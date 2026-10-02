"""
SENTRY-ID -- Document Analysis Module (Module 1: OCR & Classification)
=========================================================================
SIH 26188 -- AI-Based Fake Identity & Document Screening System

Supports TWO families of documents:

1. MRZ DOCUMENTS (passports, visas, some national IDs): ICAO 9303
   Machine Readable Zone standard, with checksum-guided repair and
   resolution/layout adaptivity.

2. INDIAN ID DOCUMENTS (Aadhaar, PAN Card, Voter ID/EPIC, Driving
   Licence): none of these use MRZ. Only Aadhaar has a public
   mathematical checksum (Verhoeff algorithm). PAN/Voter ID/Driving
   Licence are validated structurally only, honestly flagged via
   checksum_verified: false.

DOCUMENT TYPE DETECTION uses fragment-based keyword scoring, not exact-
phrase matching -- real full-page OCR on a busy ID card (watermarks,
background patterns) frequently garbles one word of a multi-word phrase
even when surrounding words read fine. Detection also runs across a few
different Tesseract page-segmentation modes and combines the results,
since a keyword missed in one layout assumption often shows up in
another. This was verified necessary and fixed against a real case: a
Voter ID card's OCR read "ELECTION COMMIS: AEANDI LA" -- garbled enough
that exact-phrase matching missed it entirely and the document was
mis-routed into the passport/MRZ pipeline, producing nonsense output.

Both Voter ID (EPIC) and Aadhaar number extraction also correct for the
OCR letter/digit confusion at format boundaries (e.g. "UZO2630044" misread
as "UZ02630044") using the same positional coercion technique as MRZ.

Name extraction across all Indian ID types anchors to the "Name" label
first (tolerant of the label's colon/spacing being dropped by OCR) before
falling back to a generic longest-Title-Case-run heuristic -- anchoring
is far more reliable when the page has other incidental capitalized text
that could otherwise outscore the real name on length alone.

Supports: .jpg, .jpeg, .png, .bmp, .tiff, .webp, and .pdf, at any
resolution from a sensible minimum (~400px) up through very large scans.

SETUP (run these once):
    pip install opencv-python pytesseract numpy Pillow

    # Tesseract OCR engine itself (separate from the pytesseract package):
    #   Windows: https://github.com/UB-Mannheim/tesseract/wiki
    #   Mac:     brew install tesseract
    #   Linux:   sudo apt install tesseract-ocr
    # If Tesseract isn't on your PATH after installing, uncomment/edit:
    # pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"
    # (Better: add C:/Program Files/Tesseract-OCR to your system PATH once,
    # system-wide, so this never needs editing again.)

    # PDF support (only needed if you'll analyze PDF files):
    pip install PyMuPDF

USAGE:
    python document_analysis_combined.py path/to/document.jpg
    python document_analysis_combined.py path/to/document.pdf
    python document_analysis_combined.py path/to/multipage.pdf 1   # page 2 (0-indexed)
"""

import re
import time
import json
import statistics

import cv2
import numpy as np
import pytesseract
from pytesseract import Output

# Uncomment and edit this line if Tesseract isn't on your system PATH:
# pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"


# =========================================================================
# SECTION 1: IMAGE PREPROCESSING (PDF loading, resolution/layout adaptivity)
# =========================================================================

def load_image(path: str, page_number: int = 0) -> np.ndarray:
    """
    Load a document from disk as a BGR image array (OpenCV format).

    Supports standard image formats natively via OpenCV: JPG/JPEG, PNG,
    BMP, TIFF, WEBP, and more. PDFs are handled separately since a PDF
    isn't pixel data — it has to be rendered to an image first. Only the
    given page is used (documents like passports/IDs are typically
    single-page; pass page_number for multi-page PDFs, 0-indexed).
    """
    ext = path.lower().rsplit(".", 1)[-1] if "." in path else ""

    if ext == "pdf":
        return _load_pdf_first_page(path, page_number=page_number)

    img = cv2.imread(path)
    if img is None:
        raise ValueError(
            f"Could not read image at {path}. Check the file path, or that "
            f"the format is supported (jpg, jpeg, png, bmp, tiff, webp, pdf)."
        )
    return img


def _load_pdf_first_page(path: str, page_number: int = 0, dpi: int = 300) -> np.ndarray:
    """
    Render a PDF's page to a BGR image array for the rest of the pipeline.

    Tries PyMuPDF (fitz) first -- it's a single `pip install PyMuPDF` with
    no separate system dependency, which is the easiest path on Windows.
    Falls back to pdf2image (which requires the Poppler system binary to
    already be installed and on PATH) if PyMuPDF isn't available.
    """
    try:
        try:
            import pymupdf as fitz  # newer PyMuPDF releases prefer this import name
        except ImportError:
            import fitz  # older PyMuPDF releases (pre-rename) only expose this
        doc = fitz.open(path)
        if page_number >= len(doc):
            raise ValueError(f"PDF only has {len(doc)} page(s); page {page_number} doesn't exist.")
        page = doc[page_number]
        zoom = dpi / 72.0  # PDF default is 72 DPI; scale up for OCR quality
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        doc.close()
        if pix.n == 4:  # RGBA
            return cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    except ImportError:
        pass  # fall through to pdf2image

    try:
        from pdf2image import convert_from_path
        pages = convert_from_path(path, dpi=dpi, first_page=page_number + 1, last_page=page_number + 1)
        if not pages:
            raise ValueError(f"Could not render page {page_number} from PDF: {path}")
        pil_img = pages[0].convert("RGB")
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except ImportError:
        raise ImportError(
            "Reading PDFs requires either PyMuPDF or pdf2image to be installed.\n"
            "Easiest fix (no extra system install needed):\n"
            "    pip install PyMuPDF\n"
            "Alternative (requires the Poppler binary on your system PATH):\n"
            "    pip install pdf2image\n"
            "    Windows Poppler binaries: https://github.com/oschwartz10612/poppler-windows/releases"
        )


def check_quality(img: np.ndarray) -> dict:
    """
    Basic image quality gate, matching the 'Image Quality Check' step
    in the pipeline. Returns a dict of quality signals + a pass/fail flag.

    This runs BEFORE OCR so garbage-in doesn't get silently misread as
    valid (or worse, misread as tampered).
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Blur detection: variance of Laplacian. Low variance = blurry.
    #
    # IMPORTANT: this metric is NOT scale-invariant. The same physical
    # sharpness produces a much lower variance at high resolution (e.g. a
    # 300 DPI full-page scan, several thousand pixels wide) than at low
    # resolution (a phone photo resized down, or a small crop) -- edges
    # spread across more pixels, diluting the second-derivative response.
    # A single fixed threshold tuned on one resolution will misfire on
    # the other. Normalize to a reference width before measuring so the
    # same threshold means the same thing regardless of source DPI.
    h0, w0 = gray.shape[:2]
    reference_width = 1200
    if w0 > reference_width:
        scale = reference_width / w0
        blur_target = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    else:
        blur_target = gray
    blur_score = cv2.Laplacian(blur_target, cv2.CV_64F).var()

    # Brightness / glare check.
    #
    # IMPORTANT: real ID documents (passports, national IDs) legitimately
    # have large light/white background areas — that alone is NOT glare
    # and must not be flagged. Actual glare/overexposure means detail is
    # LOST: a camera flash reflecting off a laminated card blows highlights
    # out to flat, textureless white. The distinguishing signal is contrast
    # (std deviation), not raw brightness. A document with a light
    # background but visible text/photo has plenty of contrast; a truly
    # glared-out image does not.
    mean_brightness = float(np.mean(gray))
    std_dev = float(np.std(gray))
    overexposed_ratio = float(np.mean(gray > 240))  # fraction of near-white pixels (informational)

    # Resolution check
    h, w = gray.shape[:2]

    issues = []
    if blur_score < 100:
        issues.append("blurry")
    if mean_brightness < 40:
        issues.append("too_dark")
    # Only flag glare when brightness is very high AND contrast/detail is
    # genuinely low — i.e. the image has actually lost information (fully
    # saturated/clipped), not just a light-toned background with normal text
    # contrast. Threshold tuned conservatively: false-rejecting a scannable
    # document is worse than occasionally missing mild glare, since a
    # rejected image just asks for a rescan rather than silently failing.
    if mean_brightness > 235 and std_dev < 20:
        issues.append("glare_or_overexposed")
    if min(h, w) < 400:
        issues.append("low_resolution")

    return {
        "blur_score": round(blur_score, 2),
        "mean_brightness": round(mean_brightness, 2),
        "contrast_std": round(std_dev, 2),
        "overexposed_ratio": round(overexposed_ratio, 4),
        "width": w,
        "height": h,
        "issues": issues,
        "passed": len(issues) == 0,
    }


def deskew(img: np.ndarray) -> np.ndarray:
    """
    Correct small rotation/skew so text lines are horizontal.
    Uses the minimum-area rectangle of thresholded text pixels.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    coords = np.column_stack(np.where(thresh > 0))
    if coords.shape[0] < 10:
        return img  # not enough signal to deskew safely

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Don't rotate for tiny angles — avoids introducing noise on already-straight images
    if abs(angle) < 0.5:
        return img

    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)
    return rotated


def enhance_for_ocr(img: np.ndarray, max_dimension: int = 2500) -> np.ndarray:
    """
    Full preprocessing pipeline for OCR: grayscale, denoise, contrast
    boost, adaptive threshold. Returns a clean binary image.

    Downscales first if the image exceeds max_dimension on its longest
    side. Full-page OCR cost scales with pixel count, so an uncapped
    8000px+ scan (common from high-DPI flatbed scanners) can take far
    longer than needed -- 2500px is well beyond what general document
    text needs for reliable OCR. The MRZ-specific pipeline is unaffected
    by this cap and can still upscale further where it actually helps.
    """
    h, w = img.shape[:2]
    if max(h, w) > max_dimension:
        scale = max_dimension / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise while preserving edges/text
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # CLAHE = adaptive contrast enhancement, helps with uneven lighting/glare
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrasted = clahe.apply(denoised)

    # Adaptive threshold handles documents with uneven backgrounds better
    # than a single global threshold.
    binary = cv2.adaptiveThreshold(
        contrasted, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 15
    )
    return binary


def enhance_mrz_for_ocr(img: np.ndarray) -> np.ndarray:
    """
    Lighter preprocessing specifically for the MRZ band.

    The MRZ is printed in a high-contrast, OCR-friendly monospace style
    (real passports use the OCR-B font designed for this purpose), so
    the heavy denoise/CLAHE/adaptive-threshold combo used for general
    document text tends to distort the repeated '<' filler characters
    instead of helping. A simple grayscale + global Otsu threshold is
    both faster and more reliable here.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)  # light smoothing only
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def generate_mrz_variants(mrz_crop: np.ndarray) -> list:
    """
    Generate several differently-preprocessed versions of the MRZ crop
    for ensemble OCR. Real-world photos vary a lot in resolution, lighting
    and sharpness, and no single preprocessing recipe is best for all of
    them — running OCR across several variants and keeping whichever
    result validates best against the ICAO checksums is far more robust
    than betting everything on one fixed pipeline.

    Upscale factors are computed adaptively from the crop's actual size
    (see adaptive_upscale_factor) rather than fixed 2x/3x multipliers, so
    a tiny low-res crop gets scaled up much more aggressively than one
    that's already high-resolution.
    """
    gray = cv2.cvtColor(mrz_crop, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    variants = []

    # 1) Light blur + Otsu (good general default)
    v = cv2.GaussianBlur(gray, (3, 3), 0)
    _, v = cv2.threshold(v, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(v)

    # 2) Straight Otsu, no blur (best when the source is already sharp)
    _, v = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(v)

    # 3) Adaptive threshold (handles uneven lighting/shadow across the band)
    v = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 31, 15)
    variants.append(v)

    # 4) Adaptive-factor upscale + Otsu -- scale computed from actual crop
    #    size (see adaptive_upscale_factor) instead of a fixed multiplier,
    #    so a tiny low-res crop gets scaled up much more than a large one.
    base_factor = adaptive_upscale_factor(h)
    upscaled = cv2.resize(gray, None, fx=base_factor, fy=base_factor, interpolation=cv2.INTER_CUBIC)
    _, v = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(v)

    # 5) A second, larger adaptive-factor upscale + adaptive threshold --
    #    covers cases where variant 4's factor wasn't quite enough.
    larger_factor = min(base_factor * 1.5, 8.0)
    upscaled2 = cv2.resize(gray, None, fx=larger_factor, fy=larger_factor, interpolation=cv2.INTER_CUBIC)
    v = cv2.adaptiveThreshold(upscaled2, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 35, 15)
    variants.append(v)

    # 6) Unsharp-mask sharpening + Otsu (helps mildly blurry photos)
    blur = cv2.GaussianBlur(gray, (0, 0), 3)
    sharpened = cv2.addWeighted(gray, 1.5, blur, -0.5, 0)
    _, v = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(v)

    return variants


def generate_mrz_band_candidates(img: np.ndarray) -> list:
    """
    Generate several candidate horizontal bands where the MRZ might live,
    instead of assuming a single fixed position. Real-world documents vary:
    passports put the MRZ at the very bottom; some ID cards center it;
    landscape-oriented cards or an awkwardly cropped photo can shift it
    elsewhere. Returning several candidates lets the OCR stage actually
    test which one contains real MRZ-like content rather than guessing.

    Each candidate also gets a plain (non-cropped) full-height fallback
    at the end, in case the document is small enough that band-splitting
    doesn't help.
    """
    h, w = img.shape[:2]
    band_fractions = [
        (0.75, 1.0),   # bottom 25% -- most passports
        (0.60, 0.85),  # bottom-ish -- some ID card layouts
        (0.0, 0.25),   # top 25% -- some ID cards / upside-down scans
        (0.35, 0.65),  # middle band -- landscape cards, centered MRZ
    ]
    candidates = []
    for top_frac, bottom_frac in band_fractions:
        top, bottom = int(h * top_frac), int(h * bottom_frac)
        band = img[top:bottom, 0:w]
        if band.shape[0] >= 20:
            candidates.append(band)
    return candidates


def crop_mrz_region(img: np.ndarray) -> np.ndarray:
    """
    Fallback single-band MRZ crop (bottom 25%), kept for callers that want
    the old fast-path behavior. Prefer generate_mrz_band_candidates() +
    a scoring step for documents whose layout isn't a standard passport.
    """
    h, w = img.shape[:2]
    top = int(h * 0.75)
    return img[top:h, 0:w]


def adaptive_upscale_factor(band_height_px: int, target_line_height_px: int = 45) -> float:
    """
    Compute an upscale factor based on actual detected size rather than a
    fixed multiplier. A crop where each MRZ line is only ~20px tall needs
    much more upscaling than one where each line is already ~80px tall --
    a single hardcoded '2x' or '3x' is either wasteful or insufficient
    depending on the source. Assumes the band holds 2 MRZ lines (TD3) or
    3 (TD1); caller can adjust target_line_height_px for TD1 if known.
    """
    if band_height_px <= 0:
        return 1.0
    estimated_line_height = band_height_px / 2.5  # ~2 lines + spacing/margin
    factor = target_line_height_px / max(estimated_line_height, 1)
    return max(1.0, min(factor, 8.0))  # cap at 8x -- beyond this, upscaling just blurs further


def preprocess_pipeline(path: str, page_number: int = 0) -> dict:
    """
    Run the full preprocessing pipeline and return everything downstream
    modules need: the quality report, the deskewed original (for MRZ/photo
    region crops), and the OCR-ready binarized image.

    `page_number` only applies to PDF input (0 = first page); ignored for
    plain image files.

    Returns `mrz_band_candidates` (multiple candidate regions where the
    MRZ might be) rather than a single fixed crop -- the OCR stage picks
    the winning band via a cheap probe (see ocr_extractor.select_best_mrz_band)
    before running the full expensive ensemble on it. This keeps the
    pipeline from hard-assuming a fixed document layout.
    """
    img = load_image(path, page_number=page_number)
    quality = check_quality(img)

    deskewed = deskew(img)
    ocr_ready = enhance_for_ocr(deskewed)
    mrz_band_candidates = generate_mrz_band_candidates(deskewed)

    return {
        "quality": quality,
        "original": img,
        "deskewed": deskewed,
        "ocr_ready": ocr_ready,
        "mrz_band_candidates": mrz_band_candidates,
    }


# =========================================================================
# SECTION 2: MRZ PARSING (ICAO 9303 check-digit validation + safe repair)
# =========================================================================

_CHAR_VALUES = {c: i for i, c in enumerate("0123456789")}
_CHAR_VALUES.update({c: i + 10 for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")})
_CHAR_VALUES["<"] = 0
_WEIGHTS = [7, 3, 1]


def _char_value(c: str) -> int:
    return _CHAR_VALUES.get(c.upper(), 0)


def check_digit(data: str) -> int:
    """Compute the ICAO 9303 check digit for a given MRZ field."""
    total = 0
    for i, c in enumerate(data):
        total += _char_value(c) * _WEIGHTS[i % 3]
    return total % 10


def _verify(data: str, expected: str) -> bool:
    """Compare a computed check digit against the digit printed in the MRZ.
    A printed '<' is treated as an unused/optional field and passes."""
    if expected == "<" or expected == "":
        return True
    try:
        return check_digit(data) == int(expected)
    except ValueError:
        return False


def clean_mrz_text(raw_text: str) -> list:
    """
    Take raw OCR text output and extract candidate MRZ lines.
    MRZ lines are uppercase, use only A-Z, 0-9 and '<', and are a fixed length.
    """
    lines = raw_text.upper().splitlines()
    candidates = []
    for line in lines:
        cleaned = re.sub(r"[^A-Z0-9<]", "", line.strip())
        cleaned = strip_hallucinated_filler_noise(cleaned)
        if len(cleaned) >= 20:
            candidates.append(cleaned)
    return candidates


def strip_hallucinated_filler_noise(line: str) -> str:
    """
    Generic OCR engines (trained on natural-language text) frequently
    hallucinate a repeated letter in place of a long run of MRZ '<'
    filler characters — a run of 15-20 identical filler chars is very
    unusual in ordinary text, so the model's language priors fight it
    and substitute something like 'KKKKKKKK' instead.

    Real MRZ content never repeats the same non-'<' character more than
    a couple of times in a row, so a run of 3+ identical non-'<'
    characters is almost certainly this hallucination artifact, not
    genuine data. Replace such runs with '<' filler.
    """
    return re.sub(r"([A-Z0-9])\1{4,}", lambda m: "<" * len(m.group(0)), line)


def _pad_or_trim(s: str, length: int) -> str:
    s = s[:length]
    return s.ljust(length, "<")


# --- OCR confusion correction ---
# MRZ has fixed-format positions (digit-only vs letter-only vs either),
# so OCR misreads of visually similar characters can often be corrected
# deterministically once we know what type of character belongs where.
# This matters even on real scans (worn ink, print-scan artifacts),
# not just synthetic test renders.

_LETTER_TO_DIGIT = {"O": "0", "D": "0", "Q": "0", "I": "1", "L": "1",
                     "Z": "2", "S": "5", "B": "8", "G": "6", "T": "1"}
_DIGIT_TO_LETTER = {"0": "O", "1": "I", "5": "S", "8": "B", "2": "Z", "6": "G"}


def _coerce(chars: str, kind: str) -> str:
    """kind: 'digit' forces digits, 'alpha' forces letters/<, 'any' leaves as-is."""
    if kind == "digit":
        return "".join(_LETTER_TO_DIGIT.get(c, c) for c in chars)
    if kind == "alpha":
        return "".join(_DIGIT_TO_LETTER.get(c, c) if c not in ("<",) else c for c in chars)
    return chars


def correct_td3_line2(line2: str) -> str:
    """Apply position-aware confusable-character correction to a TD3 line 2."""
    line2 = _pad_or_trim(line2, 44)
    parts = [
        (line2[0:9], "any"),      # passport number: alnum
        (line2[9], "digit"),      # check digit
        (line2[10:13], "alpha"),  # nationality
        (line2[13:19], "digit"),  # DOB
        (line2[19], "digit"),     # check digit
        (line2[20], "alpha"),     # sex
        (line2[21:27], "digit"),  # expiry
        (line2[27], "digit"),     # check digit
        (line2[28:42], "any"),    # personal number: alnum
        (line2[42], "digit"),     # check digit
        (line2[43], "digit"),     # composite check digit
    ]
    return "".join(_coerce(chunk, kind) for chunk, kind in parts)


def parse_td3(line1: str, line2: str) -> dict:
    """Parse a 2-line, 44-char TD3 MRZ (used on passports)."""
    line1 = _pad_or_trim(line1, 44)
    line2 = _pad_or_trim(line2, 44)

    doc_type = line1[0:2].replace("<", "")
    issuing_country = line1[2:5].replace("<", "")

    names_field = line1[5:44]
    surname, _, given_names = names_field.partition("<<")
    surname = surname.replace("<", " ").strip()
    given_names = given_names.replace("<", " ").strip()

    passport_number = line2[0:9].replace("<", "")
    passport_number_check = line2[9]
    nationality = line2[10:13].replace("<", "")
    dob_raw = line2[13:19]
    dob_check = line2[19]
    sex = line2[20]
    expiry_raw = line2[21:27]
    expiry_check = line2[27]
    personal_number = line2[28:42].replace("<", "")
    personal_number_check = line2[42]
    composite_check = line2[43]

    def fmt_date(yymmdd: str) -> str:
        if len(yymmdd) != 6 or not yymmdd.isdigit():
            return None
        yy, mm, dd = yymmdd[0:2], yymmdd[2:4], yymmdd[4:6]
        # Pivot: 00-30 -> 2000s, 31-99 -> 1900s (adjust pivot as needed for your data)
        century = "20" if int(yy) <= 30 else "19"
        return f"{century}{yy}-{mm}-{dd}"

    checks = {
        "passport_number": _verify(line2[0:9], passport_number_check),
        "date_of_birth": _verify(dob_raw, dob_check),
        "expiry_date": _verify(expiry_raw, expiry_check),
        "personal_number": _verify(line2[28:42], personal_number_check) if personal_number else True,
    }

    composite_data = line2[0:10] + line2[13:20] + line2[21:43]
    checks["composite"] = _verify(composite_data, composite_check)

    return {
        "mrz_type": "TD3",
        "document_type": doc_type,
        "issuing_country": issuing_country,
        "surname": surname,
        "given_names": given_names,
        "passport_number": passport_number,
        "nationality": nationality,
        "date_of_birth": fmt_date(dob_raw),
        "sex": sex if sex in ("M", "F") else "X",
        "expiry_date": fmt_date(expiry_raw),
        "personal_number": personal_number or None,
        "check_digit_results": checks,
        "all_checks_passed": all(checks.values()),
        "raw_lines": [line1, line2],
    }


def parse_td1(line1: str, line2: str, line3: str) -> dict:
    """Parse a 3-line, 30-char TD1 MRZ (used on ID cards)."""
    line1 = _pad_or_trim(line1, 30)
    line2 = _pad_or_trim(line2, 30)
    line3 = _pad_or_trim(line3, 30)

    doc_type = line1[0:2].replace("<", "")
    issuing_country = line1[2:5].replace("<", "")
    document_number = line1[5:14].replace("<", "")
    document_number_check = line1[14]

    dob_raw = line2[0:6]
    dob_check = line2[6]
    sex = line2[7]
    expiry_raw = line2[8:14]
    expiry_check = line2[14]
    nationality = line2[15:18].replace("<", "")
    composite_check = line2[29]

    names_field = line3
    surname, _, given_names = names_field.partition("<<")
    surname = surname.replace("<", " ").strip()
    given_names = given_names.replace("<", " ").strip()

    def fmt_date(yymmdd: str) -> str:
        if len(yymmdd) != 6 or not yymmdd.isdigit():
            return None
        yy, mm, dd = yymmdd[0:2], yymmdd[2:4], yymmdd[4:6]
        century = "20" if int(yy) <= 30 else "19"
        return f"{century}{yy}-{mm}-{dd}"

    checks = {
        "document_number": _verify(line1[5:14], document_number_check),
        "date_of_birth": _verify(dob_raw, dob_check),
        "expiry_date": _verify(expiry_raw, expiry_check),
    }
    composite_data = line1[5:30] + line2[0:7] + line2[8:15] + line2[18:29]
    checks["composite"] = _verify(composite_data, composite_check)

    return {
        "mrz_type": "TD1",
        "document_type": doc_type,
        "issuing_country": issuing_country,
        "document_number": document_number,
        "surname": surname,
        "given_names": given_names,
        "nationality": nationality,
        "date_of_birth": fmt_date(dob_raw),
        "sex": sex if sex in ("M", "F") else "X",
        "expiry_date": fmt_date(expiry_raw),
        "check_digit_results": checks,
        "all_checks_passed": all(checks.values()),
        "raw_lines": [line1, line2, line3],
    }


def _score_result(result: dict) -> int:
    """Count how many ICAO check digits passed. Higher = more trustworthy."""
    if not result or result.get("mrz_type") is None:
        return -1
    return sum(1 for v in result.get("check_digit_results", {}).values() if v)


def _best_of(candidate, current_best, current_best_score):
    """Keep whichever result has the higher checksum score."""
    if candidate is None:
        return current_best, current_best_score
    score = _score_result(candidate)
    if score > current_best_score:
        return candidate, score
    return current_best, current_best_score


def repair_td3_line2(line2: str, line1: str):
    """
    Checksum-guided repair for TD3 line 2.

    OCR errors on a fixed-format field come in two flavors:
      1. Substitution ("O" read as "0") -- correct_td3_line2() already
         handles this using known digit/letter positions.
      2. Insertion/deletion -- Tesseract reads one extra or one missing
         character somewhere, which shifts every field after it. No
         positional substitution can fix this because the positions
         themselves are now wrong.

    For (2), we exploit the fact that we have a verifiable ground truth
    (the ICAO check digits) to *search* for the fix: try removing (or
    inserting) one character at every position, re-run the checksum
    validation, and keep whichever edit yields the most passing checks.
    This is only feasible because MRZ lines are short (44 chars) and the
    alphabet is small -- an exhaustive single-edit search is cheap.
    """
    best_result, best_score = None, -1

    # Try as-is, and with pure substitution-correction, first.
    for candidate_line in (line2, correct_td3_line2(line2)):
        try:
            best_result, best_score = _best_of(parse_td3(line1, candidate_line), best_result, best_score)
        except Exception:
            continue

    if best_score >= 5:  # all 5 checks already pass -- no repair needed
        return best_result, best_score

    # One character too many: try deleting each position.
    if len(line2) == 45:
        for i in range(len(line2)):
            candidate = line2[:i] + line2[i + 1:]
            for variant in (candidate, correct_td3_line2(candidate)):
                try:
                    best_result, best_score = _best_of(parse_td3(line1, variant), best_result, best_score)
                except Exception:
                    continue
            if best_score >= 5:
                return best_result, best_score

    # One character missing: try inserting the most likely candidates
    # ('<' filler is by far the most common drop, but try digits too
    # since a faint character can vanish entirely) at each position.
    if len(line2) == 43:
        for i in range(len(line2) + 1):
            for ch in ("<", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"):
                candidate = line2[:i] + ch + line2[i:]
                try:
                    best_result, best_score = _best_of(parse_td3(line1, candidate), best_result, best_score)
                except Exception:
                    continue
            if best_score >= 5:
                return best_result, best_score

    # Length is right (44) but a field still fails: likely a pure
    # substitution error inside an alphanumeric field (passport number or
    # personal number), which correct_td3_line2() can't fix because those
    # fields legitimately mix letters and digits -- there's no single
    # "expected type" to coerce toward.
    #
    # IMPORTANT SAFETY CONSTRAINT: only try substitutions from the known
    # visually-confusable set (O/0, Z/2, etc.), never an exhaustive search
    # over the full alphabet. An exhaustive search WILL eventually find
    # *some* single-character edit that satisfies the checksum on almost
    # any input -- but that's a coincidental match, not evidence the edit
    # is correct. This showed up concretely on a test document with an
    # internally-inconsistent checksum: exhaustive search "fixed" a
    # correctly-read value into a DIFFERENT, still-wrong value, and
    # reported it as checksum_verified -- false confidence, which is worse
    # than honestly reporting the checksum failure. Restricting to
    # confusable characters keeps repairs plausible rather than coincidental.
    if len(line2) == 44 and best_score < 5 and best_result is not None:
        checks = best_result.get("check_digit_results", {})
        working_line = list(line2)

        field_specs = [("passport_number", 0, 9, 9), ("personal_number", 28, 42, 42)]
        for check_key, start, end, check_pos in field_specs:
            if checks.get(check_key):
                continue  # already valid, don't touch it
            data = "".join(working_line[start:end])
            check_char = working_line[check_pos]
            fixed = None
            for i in range(len(data)):
                original = data[i]
                candidates = []
                if original in _LETTER_TO_DIGIT:
                    candidates.append(_LETTER_TO_DIGIT[original])
                if original in _DIGIT_TO_LETTER:
                    candidates.append(_DIGIT_TO_LETTER[original])
                for cand in candidates:
                    trial = data[:i] + cand + data[i + 1:]
                    if _verify(trial, check_char):
                        fixed = trial
                        break
                if fixed:
                    break
            if fixed:
                working_line[start:end] = list(fixed)

        candidate = "".join(working_line)
        if candidate != line2:
            try:
                best_result, best_score = _best_of(parse_td3(line1, candidate), best_result, best_score)
            except Exception:
                pass

    return best_result, best_score


def parse_mrz_best_effort(candidate_texts) -> dict:
    """
    Robust MRZ parsing entry point: takes either a single raw OCR text
    string or a list of raw OCR text strings (one per preprocessing/PSM
    variant -- see extract_mrz_text_multi), tries every one of them
    through cleaning, substitution-correction and insertion/deletion
    repair.

    Checksum score alone isn't a perfect arbiter: on a document whose own
    printed checksum doesn't actually validate against its own data (see
    module docstring), a single stray OCR misread can coincidentally
    satisfy that broken checksum and look MORE trustworthy than the
    correct reading. To guard against that, when multiple candidates tie
    for the best score, this breaks the tie by consensus -- preferring
    whichever passport_number value the most independent OCR attempts
    agree on, rather than an arbitrary single lucky match.

    This is the "read it even when the image isn't perfectly clear"
    entry point -- prefer this over parse_mrz_from_text for real-world
    (photographed, not scanned) documents.
    """
    if isinstance(candidate_texts, str):
        candidate_texts = [candidate_texts]

    all_results = []  # every (result, score) pair seen, for consensus tie-breaking
    attempts = 0

    for raw_text in candidate_texts:
        candidates = clean_mrz_text(raw_text)

        td3_lines = [l for l in candidates if 20 <= len(l) <= 45]
        if len(td3_lines) >= 2:
            l1, l2 = td3_lines[-2:]
            attempts += 1
            result, score = repair_td3_line2(l2, l1)
            if result is not None:
                all_results.append((result, score))

        td1_lines = [l for l in candidates if 28 <= len(l) <= 30]
        if len(td1_lines) >= 3:
            attempts += 1
            try:
                result = parse_td1(td1_lines[0], td1_lines[1], td1_lines[2])
                all_results.append((result, _score_result(result)))
            except Exception:
                pass

    if not all_results:
        return {
            "mrz_type": None,
            "error": "No valid MRZ pattern detected across any OCR attempt",
            "ocr_attempts_tried": attempts,
            "all_checks_passed": False,
        }

    best_score = max(score for _, score in all_results)
    top_results = [r for r, s in all_results if s == best_score]

    if len(top_results) == 1 or best_score < 5:
        best_result = top_results[0]
    else:
        # Tie among multiple fully-valid candidates -- consensus tie-break.
        # Count how many of the RAW (pre-tie-break) results, across every
        # OCR attempt, agree on each candidate's passport_number. The
        # value most independent attempts converged on is more likely
        # correct than one that happens to be alone with a matching
        # (possibly coincidental) checksum.
        from collections import Counter
        pn_votes = Counter(
            r.get("passport_number") for r, _ in all_results if r.get("passport_number")
        )
        top_results.sort(key=lambda r: pn_votes.get(r.get("passport_number"), 0), reverse=True)
        best_result = top_results[0]

    best_result["ocr_attempts_tried"] = attempts
    return best_result


def parse_mrz_from_text(raw_ocr_text: str) -> dict:
    """
    Main entry point: take raw OCR text (from the MRZ crop region) and
    return parsed + validated MRZ data, or an error report if no valid
    MRZ pattern is found.
    """
    candidates = clean_mrz_text(raw_ocr_text)

    # TD3: 2 lines, up to 44 chars each. Trailing '<' fillers often produce
    # no visible ink, so OCR frequently drops them and returns a shorter
    # line — accept lines from ~20 chars up and let parse_td3's padding
    # fill in the rest, rather than requiring the full 44 up front.
    td3_lines = [l for l in candidates if 20 <= len(l) <= 44]
    if len(td3_lines) >= 2:
        td3_lines = td3_lines[-2:]  # MRZ is always the last two matching lines
        try:
            raw_result = parse_td3(td3_lines[0], td3_lines[1])
            # If raw OCR text didn't pass all checks, retry with confusable-
            # character correction on line 2 (digits/letters swapped by OCR)
            # and keep whichever version validates better.
            if not raw_result.get("all_checks_passed"):
                corrected_line2 = correct_td3_line2(td3_lines[1])
                corrected_result = parse_td3(td3_lines[0], corrected_line2)
                raw_score = sum(raw_result.get("check_digit_results", {}).values())
                corrected_score = sum(corrected_result.get("check_digit_results", {}).values())
                if corrected_score > raw_score:
                    corrected_result["ocr_correction_applied"] = True
                    return corrected_result
            return raw_result
        except Exception:
            pass  # fall through to TD1 attempt / error

    # TD1: exactly 3 lines, each ~30 chars
    td1_lines = [l for l in candidates if 28 <= l.__len__() <= 30]
    if len(td1_lines) >= 3:
        try:
            return parse_td1(td1_lines[0], td1_lines[1], td1_lines[2])
        except Exception:
            pass

    return {
        "mrz_type": None,
        "error": "No valid MRZ pattern detected in OCR text",
        "candidate_lines_found": candidates,
        "all_checks_passed": False,
    }


# =========================================================================
# SECTION 3: OCR EXTRACTION (MRZ band selection, visual name cross-check,
#            fault-tolerant document type detection across all document
#            types)
# =========================================================================

def extract_raw_text(img: np.ndarray, psm: int = 6) -> str:
    """Full-text OCR pass. psm=6 assumes a uniform block of text."""
    config = f"--psm {psm}"
    return pytesseract.image_to_string(img, config=config)


def extract_raw_text_multi_psm(img: np.ndarray) -> str:
    """
    Run full-page OCR across a few different page-segmentation modes and
    concatenate the results, for document-type DETECTION specifically
    (not for final field extraction -- that still uses the single psm=6
    pass as its primary source).

    Real ID cards are visually busier than a passport bio page (security
    watermarks, background patterns, multiple scripts), so a single OCR
    pass can miss or garble the exact keyword phrase a classifier is
    looking for even when the image itself is perfectly readable. Trying
    a couple of alternate layout assumptions costs little (no upscaling,
    no ensemble of preprocessing variants -- just 2 extra quick passes)
    and meaningfully increases the odds that at least one attempt reads
    the distinguishing keywords correctly.
    """
    texts = []
    for psm in (6, 3, 11):
        try:
            texts.append(pytesseract.image_to_string(img, config=f"--psm {psm}"))
        except Exception:
            continue
    return "\n".join(texts)


def extract_mrz_text(mrz_img: np.ndarray) -> str:
    """
    OCR pass tuned for the MRZ region: restrict the character whitelist
    to what MRZ actually contains (A-Z, 0-9, <), which meaningfully
    reduces misreads on the checksum-critical characters.
    """
    config = (
        "--psm 6 "
        "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
    )
    return pytesseract.image_to_string(mrz_img, config=config)


def extract_mrz_text_multi(mrz_variants: list) -> list:
    """
    Run MRZ-tuned OCR across every preprocessed variant AND several
    Tesseract page-segmentation modes, returning every raw text result.

    This is the core of robust MRZ reading: instead of trusting one
    OCR pass to be right, generate many independent readings so that
    the checksum-guided repair step downstream has multiple chances to
    find a version that actually validates.
    """
    results = []
    psm_modes = [6, 4, 11]
    whitelist_cfg = "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"

    for img in mrz_variants:
        for psm in psm_modes:
            config = f"--psm {psm} {whitelist_cfg}"
            try:
                text = pytesseract.image_to_string(img, config=config)
                if text.strip():
                    results.append(text)
            except Exception:
                continue
    return results


def _mrz_likelihood_score(text: str) -> int:
    """
    Quick heuristic score for 'does this text look like it contains an
    MRZ' -- used to pick which region of a document to spend the full
    (expensive) OCR ensemble on, rather than assuming the MRZ is always
    in one fixed position.
    """
    score = 0
    for line in text.upper().splitlines():
        cleaned = re.sub(r"[^A-Z0-9<]", "", line.strip())
        if len(cleaned) >= 20:
            score += len(cleaned)
            score += cleaned.count("<") * 2  # filler run is a strong MRZ signature
    return score


def select_best_mrz_band(band_candidates: list) -> object:
    """
    Cheap single-pass probe (Otsu threshold, one PSM mode) across each
    candidate band to find which region of the document actually contains
    MRZ-like content, instead of assuming a fixed position. The winning
    band then gets the full expensive multi-variant ensemble -- this two-
    stage approach keeps total OCR calls bounded even though we're now
    searching several regions instead of one.
    """
    import cv2
    best_band, best_score = band_candidates[0], -1
    for band in band_candidates:
        gray = cv2.cvtColor(band, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        try:
            text = pytesseract.image_to_string(
                binary,
                config="--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
            )
        except Exception:
            continue
        score = _mrz_likelihood_score(text)
        if score > best_score:
            best_score = score
            best_band = band
    return best_band


def extract_words_with_confidence(img: np.ndarray, psm: int = 6) -> list:
    """
    Word-level OCR with per-word confidence (0-100 from Tesseract).
    Returns a list of dicts: {text, confidence, bbox}.
    """
    config = f"--psm {psm}"
    data = pytesseract.image_to_data(img, config=config, output_type=Output.DICT)

    words = []
    n = len(data["text"])
    for i in range(n):
        text = data["text"][i].strip()
        conf = int(data["conf"][i]) if data["conf"][i] != "-1" else -1
        if text and conf >= 0:
            words.append({
                "text": text,
                "confidence": conf,
                "bbox": {
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "w": data["width"][i],
                    "h": data["height"][i],
                },
            })
    return words


def detect_document_type(raw_text: str, mrz_found: bool, mrz_type: str = None) -> str:
    """
    Heuristic document classification. Checks for Indian ID documents
    first (Aadhaar, PAN, Voter ID, Driving License -- none of which use
    an MRZ), then falls back to MRZ-based / keyword-based classification
    for passports, visas, and other travel documents.

    Uses fragment-based scoring rather than exact-phrase matching: real
    OCR on a full document page is noisier than the MRZ-tuned pass (no
    restricted character whitelist, more visual clutter/watermarks to
    fight), so a multi-word phrase like "ELECTION COMMISSION OF INDIA"
    frequently comes back with one word garbled even when the others read
    fine. Requiring the individual words to appear ANYWHERE in the text
    (not as one contiguous exact phrase) is much more robust to that,
    while still being specific enough to avoid false-positives.
    """
    text_upper = raw_text.upper()

    def _word_count_present(words: list) -> int:
        """How many of these words/fragments appear anywhere in the text."""
        return sum(1 for w in words if w in text_upper)

    # --- Indian ID documents (no MRZ -- must be detected via keywords/patterns) ---
    aadhaar_signal = _word_count_present(["AADHAAR", "UNIQUE IDENTIFICATION"])
    has_12_digit_number = bool(re.search(r"\b\d{4}\s?\d{4}\s?\d{4}\b", text_upper))
    govt_india_signal = _word_count_present(["GOVERNMENT", "INDIA"])
    if aadhaar_signal >= 1 or "आधार" in raw_text or (has_12_digit_number and govt_india_signal >= 2):
        return "aadhaar"

    pan_signal = _word_count_present(["INCOME TAX", "PERMANENT ACCOUNT", "PAN CARD"])
    has_pan_format = bool(re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", text_upper))
    if pan_signal >= 1 or has_pan_format:
        return "pan_card"

    voter_signal = _word_count_present(["ELECTION", "COMMIS", "ELECTOR"])
    if voter_signal >= 1 or "EPIC" in text_upper or re.search(r"\bVOTER\b|\bELECT", text_upper):
        return "voter_id"

    dl_signal = _word_count_present(["DRIVING", "LICEN", "TRANSPORT DEPARTMENT"])
    has_vehicle_class = bool(re.search(r"\bMCWG\b|\bLMV\b|NON-TRANSPORT", text_upper))
    if dl_signal >= 2 or has_vehicle_class:
        return "driving_license"

    if mrz_type == "TD3":
        return "passport"
    if mrz_type == "TD1":
        return "national_id"

    if "VISA" in text_upper:
        return "visa"
    if "PASSPORT" in text_upper or "PASSEPORT" in text_upper:
        return "passport"
    if "DRIVING" in text_upper or "DRIVER" in text_upper or "LICENCE" in text_upper or "LICENSE" in text_upper:
        return "driving_license"
    if "IDENTITY" in text_upper or "IDENTIFICATION" in text_upper:
        return "national_id"
    if "PERMIT" in text_upper:
        return "permit"

    return "unknown"


# --- Visual-zone field extraction (regex-based cross-check against MRZ) ---

_DATE_PATTERNS = [
    r"\b(\d{2})[\/\.\-](\d{2})[\/\.\-](\d{4})\b",   # DD/MM/YYYY
    r"\b(\d{4})[\/\.\-](\d{2})[\/\.\-](\d{2})\b",   # YYYY-MM-DD
    r"\b(\d{2})\s?(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s?(\d{4})\b",
]

_PASSPORT_NO_PATTERN = r"\b[A-PR-WYa-pr-wy][0-9]{7}\b|\b[A-Z]{1,2}[0-9]{6,8}\b"


def extract_dates(raw_text: str) -> list:
    """Find all date-like strings in the visual zone text."""
    found = []
    for pattern in _DATE_PATTERNS:
        for match in re.finditer(pattern, raw_text.upper()):
            found.append(match.group(0))
    return found


def extract_passport_number_candidates(raw_text: str) -> list:
    """Find strings matching common passport-number formats."""
    return re.findall(_PASSPORT_NO_PATTERN, raw_text.upper())


def extract_visa_fields(raw_text: str) -> dict:
    """
    Best-effort visa field extraction from visual-zone OCR text.
    Visas don't have a standardized MRZ the way passports do, so this
    leans more heavily on layout keywords.
    """
    text_upper = raw_text.upper()
    result = {}

    visa_no_match = re.search(r"VISA\s*(?:NO|NUMBER|N[°O])[\.:]?\s*([A-Z0-9]{6,12})", text_upper)
    if visa_no_match:
        result["visa_number"] = visa_no_match.group(1)

    visa_type_match = re.search(r"(?:TYPE|CATEGORY)[\.:]?\s*([A-Z0-9\-]{1,4})\b", text_upper)
    if visa_type_match:
        result["visa_type"] = visa_type_match.group(1)

    duration_match = re.search(r"(?:DURATION|STAY)[\.:]?\s*(\d{1,4})\s*(DAYS?|MONTHS?|YEARS?)", text_upper)
    if duration_match:
        result["stay_duration"] = f"{duration_match.group(1)} {duration_match.group(2).lower()}"

    dates = extract_dates(raw_text)
    if dates:
        result["entry_validity_candidates"] = dates

    return result


_NAME_STOPWORDS = {
    "REPUBLIC", "INDIA", "TYPE", "COUNTRY", "CODE", "PASSPORT", "SURNAME",
    "GIVEN", "NAME", "NAMES", "NATIONALITY", "SEX", "BIRTH", "PLACE", "ISSUE",
    "DATE", "EXPIRY", "INDIAN", "OBSERVATION", "MISCELLANEOUS", "SERVICE",
    "AUTHORITY", "SIGNATURE", "HOLDER", "PAGES", "CONTAINS", "OLD",
}


def _levenshtein(a: str, b: str) -> int:
    """Standard edit distance -- pure Python, no dependency needed."""
    m, n = len(a), len(b)
    if m == 0:
        return n
    if n == 0:
        return m
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + cost)
            prev = temp
    return dp[n]


def extract_visual_name_tokens(raw_text: str) -> list:
    """Pull candidate all-caps alphabetic name-like tokens from visual-zone OCR."""
    tokens = re.findall(r"\b[A-Z]{3,}\b", raw_text.upper())
    return [t for t in tokens if t not in _NAME_STOPWORDS]


def correct_name_field_with_visual(mrz_name: str, raw_text: str) -> str:
    """
    Cross-check each word of an MRZ-derived name against visual-zone OCR
    tokens. Names have no ICAO check digit, so an inserted/dropped phantom
    character (Tesseract's most common MRZ failure mode) can't be verified
    or repaired the way passport number/DOB/expiry can. The visual zone is
    printed in ordinary text (not the filler-heavy MRZ format that tends
    to confuse OCR), so it's a useful independent second opinion here.

    Handles two failure patterns:
      1. A visual-zone token is exactly one character shorter than the
         MRZ word and within edit distance 1 -- likely a phantom inserted
         character in the MRZ reading. Use the visual version.
      2. The MRZ reading merged two separate names into one long word
         (the '<' separator between them got misread as nothing, gluing
         them together with an extra stray character). Try splitting the
         word at every position and see if both halves independently
         match separate visual-zone tokens.
    """
    if not mrz_name:
        return mrz_name
    visual_tokens = extract_visual_name_tokens(raw_text)
    corrected_words = []
    for w in mrz_name.split():
        # Pattern 1: single inserted character in an otherwise-intact word.
        best_match = None
        for vt in visual_tokens:
            if len(vt) == len(w) - 1 and _levenshtein(w, vt) <= 1:
                best_match = vt
                break
        if best_match:
            corrected_words.append(best_match)
            continue

        # Pattern 2: two words merged into one (only worth trying on
        # suspiciously long words -- a normal single name rarely exceeds
        # ~10 characters, but this varies by culture/language, so this is
        # a soft heuristic trigger, not a hard rule).
        split_result = None
        if len(w) >= 10:
            for i in range(3, len(w) - 2):
                left, right = w[:i], w[i:]
                left_vt = next((vt for vt in visual_tokens
                                 if abs(len(vt) - len(left)) <= 1 and _levenshtein(left, vt) <= 1), None)
                right_vt = next((vt for vt in visual_tokens
                                  if abs(len(vt) - len(right)) <= 1 and _levenshtein(right, vt) <= 1), None)
                if left_vt and right_vt:
                    split_result = f"{left_vt} {right_vt}"
                    break
        corrected_words.append(split_result if split_result else w)
    return " ".join(corrected_words)


# =========================================================================
# SECTION 4: INDIAN IDENTITY DOCUMENTS (Aadhaar, PAN, Voter ID, Driving
#            Licence -- none of these use MRZ)
# =========================================================================

# =============================================================================
# VERHOEFF ALGORITHM -- Aadhaar's real, verifiable checksum
# =============================================================================
# Standard tables per the published Verhoeff algorithm specification.
# Self-consistency verified: generating a check digit for "23412341234"
# and validating the resulting 12-digit number round-trips correctly.

_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def verhoeff_validate(number: str) -> bool:
    """Validate a numeric string's last digit as a Verhoeff check digit."""
    if not number.isdigit():
        return False
    c = 0
    for i, digit in enumerate(reversed(number)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(digit)]]
    return c == 0


# =============================================================================
# CONFUSABLE-CHARACTER CORRECTION for numeric Aadhaar OCR (reuse MRZ pattern)
# =============================================================================

_LETTER_TO_DIGIT = {"O": "0", "D": "0", "Q": "0", "I": "1", "L": "1",
                     "Z": "2", "S": "5", "B": "8", "G": "6", "T": "1"}
_DIGIT_TO_LETTER = {"0": "O", "1": "I", "5": "S", "8": "B", "2": "Z", "6": "G"}

_NAME_LABEL_BLOCKLIST = {
    "DATE", "BIRTH", "GOVERNMENT", "INDIA", "MALE", "FEMALE", "AADHAAR",
    "IDENTITY", "OFFLINE", "ONLINE", "VERIFICATION", "AUTHENTICATION",
    "PROOF", "CITIZENSHIP", "ELECTION", "COMMISSION", "ELECTOR", "PHOTO",
    "CARD", "TRANSPORT", "DEPARTMENT", "LICENCE", "LICENSE", "DRIVING",
}


def _extract_best_name(raw_text: str) -> str:
    """
    Shared name-extraction heuristic for Indian ID documents.

    Priority 1: anchor to a "Name" label (tolerant of the colon/space
    after it being dropped by OCR, a common failure when a field label
    and its value end up glued together) and take the Title-Case run
    immediately following it. This is far more reliable than blindly
    picking "the longest Title-Case run in the whole document" when the
    page has other incidental capitalized text (headers, other labels)
    that can outscore the real name on length alone.

    Priority 2 (fallback): if no "Name" label is found at all, look for
    any Title-Case run of 2-4 words and prefer the longest, filtering out
    common non-name label words.
    """
    anchored = re.search(
        r"NAME[:\s]{0,3}([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
        raw_text, re.IGNORECASE
    )
    if anchored:
        return anchored.group(1)

    name_candidates = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b", raw_text)
    valid_names = [c for c in name_candidates
                   if not any(w.upper() in _NAME_LABEL_BLOCKLIST for w in c.split())]
    return max(valid_names, key=len) if valid_names else None


def _coerce_digits(s: str) -> str:
    return "".join(_LETTER_TO_DIGIT.get(c, c) for c in s)


def repair_aadhaar_number(raw_candidate: str) -> str:
    """
    Try to recover a valid Aadhaar number from a noisy OCR reading using
    the same 'checksum-guided repair' philosophy as MRZ: coerce likely
    digit confusions first, and if that doesn't validate, try a single
    confusable-character substitution search (never an unconstrained
    exhaustive search -- see mrz_parser.py's docstring for why that's
    unsafe: it can "fix" a number into a different, still-wrong one that
    coincidentally validates).
    """
    digits_only = re.sub(r"\D", "", raw_candidate)
    if len(digits_only) != 12:
        return None

    if verhoeff_validate(digits_only):
        return digits_only

    coerced = _coerce_digits(raw_candidate)
    coerced_digits = re.sub(r"\D", "", coerced)
    if len(coerced_digits) == 12 and verhoeff_validate(coerced_digits):
        return coerced_digits

    return None  # honestly report failure rather than guess


# =============================================================================
# AADHAAR EXTRACTION
# =============================================================================

def extract_aadhaar_fields(raw_text: str) -> dict:
    """
    Extract and validate Aadhaar card fields. The 12-digit number is the
    only field here with a real mathematical checksum (Verhoeff) -- name,
    DOB, gender, and address are best-effort text extraction with no
    verification available, same limitation as MRZ names.
    """
    text_upper = raw_text.upper()
    result = {"document_type": "aadhaar", "fields": [], "checksum_verified": False}

    # Name: look for a Title-Case run of 2-4 words (e.g. "Mohammed Naeem
    # Naushad"). Real scans carry a lot of OCR noise around this, so filter
    # out common non-name label words and prefer the longest plausible
    # match rather than just the first one found.
    best_name = _extract_best_name(raw_text)
    if best_name:
        result["fields"].append({
            "field_name": "name", "value": best_name,
            "confidence": 0.7, "source": "ocr", "checksum_verified": False,
        })

    # Aadhaar numbers are printed as "XXXX XXXX XXXX" (space-separated
    # groups of 4). Real cards often have security watermarks/patterns
    # overlapping the number, which can make OCR misread the space as a
    # stray character (colon, period, etc.) instead of dropping it --
    # tolerate up to 2 non-digit characters between groups rather than
    # requiring clean whitespace.
    number_candidates = re.findall(r"\b\d{4}\D{0,2}\d{4}\D{0,2}\d{4}\b", raw_text)
    verified_number = None
    for cand in number_candidates:
        fixed = repair_aadhaar_number(cand)
        if fixed:
            verified_number = fixed
            break

    if verified_number:
        formatted = f"{verified_number[0:4]} {verified_number[4:8]} {verified_number[8:12]}"
        result["fields"].append({
            "field_name": "aadhaar_number", "value": formatted,
            "confidence": 0.99, "source": "ocr", "checksum_verified": True,
        })
        result["checksum_verified"] = True
    elif number_candidates:
        # Found a 12-digit-shaped string but it didn't pass Verhoeff --
        # report it anyway at low confidence rather than silently dropping it.
        result["fields"].append({
            "field_name": "aadhaar_number", "value": number_candidates[0],
            "confidence": 0.4, "source": "ocr", "checksum_verified": False,
        })

    dob_match = re.search(r"(?:DOB|Date of Birth)[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})", raw_text, re.IGNORECASE)
    if dob_match:
        result["fields"].append({
            "field_name": "date_of_birth", "value": dob_match.group(1),
            "confidence": 0.8, "source": "ocr", "checksum_verified": False,
        })
    else:
        yob_match = re.search(r"(?:YOB|Year of Birth)[:\s]*(\d{4})", raw_text, re.IGNORECASE)
        if yob_match:
            result["fields"].append({
                "field_name": "year_of_birth", "value": yob_match.group(1),
                "confidence": 0.8, "source": "ocr", "checksum_verified": False,
            })

    gender_match = re.search(r"\b(MALE|FEMALE|TRANSGENDER)\b", text_upper)
    if gender_match:
        result["fields"].append({
            "field_name": "gender", "value": gender_match.group(1).title(),
            "confidence": 0.85, "source": "ocr", "checksum_verified": False,
        })

    return result


# =============================================================================
# PAN CARD EXTRACTION
# =============================================================================

_PAN_HOLDER_TYPES = {
    "P": "Individual", "C": "Company", "H": "Hindu Undivided Family (HUF)",
    "A": "Association of Persons (AOP)", "B": "Body of Individuals (BOI)",
    "G": "Government", "J": "Artificial Judicial Person",
    "L": "Local Authority", "F": "Firm/LLP", "T": "Trust",
}


def extract_pan_fields(raw_text: str) -> dict:
    """
    Extract PAN card fields. PAN format is AAAAA9999A (5 letters, 4 digits,
    1 letter) with semantic structure: the 4th letter encodes holder type.
    No public mathematical checksum is published for PAN (unlike Aadhaar),
    so this validates STRUCTURE (does it match the format, is the holder-
    type letter valid) rather than a true checksum -- checksum_verified
    is always False here, which is the honest answer, not a limitation
    of this code specifically.
    """
    text_upper = raw_text.upper()
    result = {"document_type": "pan_card", "fields": [], "checksum_verified": False}

    pan_match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text_upper)
    if pan_match:
        pan = pan_match.group(1)
        holder_type_letter = pan[3]
        structurally_valid = holder_type_letter in _PAN_HOLDER_TYPES
        result["fields"].append({
            "field_name": "pan_number", "value": pan,
            "confidence": 0.9 if structurally_valid else 0.5,
            "source": "ocr", "checksum_verified": False,
            "structurally_valid": structurally_valid,
        })
        if structurally_valid:
            result["fields"].append({
                "field_name": "holder_type", "value": _PAN_HOLDER_TYPES[holder_type_letter],
                "confidence": 0.9, "source": "derived", "checksum_verified": False,
            })

    dob_match = re.search(r"(\d{2}[/-]\d{2}[/-]\d{4})", raw_text)
    if dob_match:
        result["fields"].append({
            "field_name": "date_of_birth", "value": dob_match.group(1),
            "confidence": 0.75, "source": "ocr", "checksum_verified": False,
        })

    return result


# =============================================================================
# VOTER ID (EPIC) EXTRACTION
# =============================================================================

def extract_voter_id_fields(raw_text: str) -> dict:
    """
    Extract Voter ID / EPIC (Elector's Photo Identity Card) fields.
    EPIC format is typically 3 letters + 7 digits (10 chars total), but
    older cards and some states vary this -- no public checksum exists,
    so this is structural pattern matching only.

    OCR commonly confuses the letter/digit boundary here the same way it
    does in MRZ (O/0 look identical) -- e.g. "UZO2630044" misread as
    "UZ02630044". Search loosely for any 10-char alnum blob, then coerce
    the first 3 characters toward letters and the remaining 7 toward
    digits before validating the expected shape, rather than requiring a
    clean strict match on the first attempt.
    """
    text_upper = raw_text.upper()
    result = {"document_type": "voter_id", "fields": [], "checksum_verified": False}

    best_name = _extract_best_name(raw_text)
    if best_name:
        result["fields"].append({
            "field_name": "name", "value": best_name,
            "confidence": 0.65, "source": "ocr", "checksum_verified": False,
        })

    epic_match = re.search(r"\b([A-Z]{3}[0-9]{7})\b", text_upper)
    epic_value = epic_match.group(1) if epic_match else None

    if not epic_value:
        for loose_match in re.finditer(r"\b([A-Z0-9]{10})\b", text_upper):
            candidate = loose_match.group(1)
            letters_part = "".join(_DIGIT_TO_LETTER.get(c, c) for c in candidate[0:3])
            digits_part = "".join(_LETTER_TO_DIGIT.get(c, c) for c in candidate[3:10])
            fixed = letters_part + digits_part
            if re.fullmatch(r"[A-Z]{3}[0-9]{7}", fixed):
                epic_value = fixed
                break

    if epic_value:
        result["fields"].append({
            "field_name": "epic_number", "value": epic_value,
            "confidence": 0.8 if epic_match else 0.65,
            "source": "ocr", "checksum_verified": False,
        })

    age_match = re.search(r"(?:AGE)[:\s]*(\d{1,3})\b", raw_text, re.IGNORECASE)
    if age_match:
        result["fields"].append({
            "field_name": "age", "value": age_match.group(1),
            "confidence": 0.7, "source": "ocr", "checksum_verified": False,
        })

    gender_match = re.search(r"\b(MALE|FEMALE|TRANSGENDER)\b", text_upper)
    if gender_match:
        result["fields"].append({
            "field_name": "gender", "value": gender_match.group(1).title(),
            "confidence": 0.8, "source": "ocr", "checksum_verified": False,
        })

    return result


# =============================================================================
# DRIVING LICENSE EXTRACTION
# =============================================================================

def extract_driving_license_fields(raw_text: str) -> dict:
    """
    Extract Driving License fields. DL number format varies significantly
    by issuing state in India (typically 2-letter state code + 2-digit RTO
    code + year + serial number, e.g. "KA0120230012345" or with separators
    "KA-01 2023 0012345") -- no universal checksum exists across states,
    so this is pattern-based extraction, deliberately generous on format
    to accommodate state variation rather than one strict regex.
    """
    text_upper = re.sub(r"\s+", " ", raw_text.upper())
    result = {"document_type": "driving_license", "fields": [], "checksum_verified": False}

    # Generous pattern: 2 letters, optional separator, 2 digits, optional
    # separator, then 9-13 more digits (covers most state formats)
    dl_match = re.search(r"\b([A-Z]{2}[-\s]?[0-9]{2}[-\s]?[0-9]{9,13})\b", text_upper)
    if dl_match:
        cleaned = re.sub(r"[-\s]", "", dl_match.group(1))
        result["fields"].append({
            "field_name": "license_number", "value": cleaned,
            "confidence": 0.7, "source": "ocr", "checksum_verified": False,
        })

    dates = re.findall(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", raw_text)
    if dates:
        result["fields"].append({
            "field_name": "date_of_birth", "value": dates[0],
            "confidence": 0.7, "source": "ocr", "checksum_verified": False,
        })
        if len(dates) > 1:
            result["fields"].append({
                "field_name": "validity_date_candidates", "value": dates[1:],
                "confidence": 0.6, "source": "ocr", "checksum_verified": False,
            })

    vehicle_classes = re.findall(r"\b(LMV|MCWG|MCWOG|HMV|HGMV|HPMV|TRANS)\b", text_upper)
    if vehicle_classes:
        result["fields"].append({
            "field_name": "vehicle_class", "value": list(set(vehicle_classes)),
            "confidence": 0.75, "source": "ocr", "checksum_verified": False,
        })

    return result


# =============================================================================
# DISPATCH
# =============================================================================

_EXTRACTORS = {
    "aadhaar": extract_aadhaar_fields,
    "pan_card": extract_pan_fields,
    "voter_id": extract_voter_id_fields,
    "driving_license": extract_driving_license_fields,
}


def extract_indian_id_fields(document_type: str, raw_text: str) -> dict:
    """Dispatch to the right extractor for a detected Indian ID document type."""
    extractor = _EXTRACTORS.get(document_type)
    if extractor is None:
        return None
    return extractor(raw_text)


# =========================================================================
# SECTION 5: MAIN ORCHESTRATOR
# =========================================================================

def _build_extracted_fields(mrz_result: dict, source: str = "mrz") -> list:
    """
    Convert parsed MRZ data into the extracted_fields list format:
    [{field_name, value, confidence, source, checksum_verified}, ...]

    MRZ fields get high confidence when their individual check digit
    passed, lower confidence when it failed. Fields with NO check digit
    at all (names, nationality, sex, issuing country) can't be verified
    this way -- but names specifically are long free-text fields where
    Tesseract's phantom-character insertions show up most, so they get a
    distinctly lower confidence than the short, low-risk fields like
    nationality/sex. `checksum_verified: false` makes this explicit for
    downstream modules, rather than burying it in a confidence number.
    """
    if mrz_result.get("mrz_type") is None:
        return []

    checks = mrz_result.get("check_digit_results", {})
    fields = []

    def add(name, value, check_key=None, unverified_confidence=0.95):
        if value is None or value == "":
            return
        if check_key and check_key in checks:
            confidence = 0.99 if checks[check_key] else 0.55
            verified = True
        else:
            confidence = unverified_confidence
            verified = False
        fields.append({
            "field_name": name,
            "value": value,
            "confidence": confidence,
            "source": source,
            "checksum_verified": verified,
        })

    # Names: no ICAO check digit exists for these on ANY MRZ reader, and
    # they're the field type most likely to carry an uncaught OCR artifact
    # (long free text, vs. short 1-3 char fields below). Flag accordingly.
    add("surname", mrz_result.get("surname"), unverified_confidence=0.75)
    add("given_names", mrz_result.get("given_names"), unverified_confidence=0.75)

    # Short, low-entropy fields -- much less prone to insertion errors in
    # practice, and both real test documents came back correct on these.
    add("nationality", mrz_result.get("nationality"))
    add("sex", mrz_result.get("sex"))
    add("issuing_country", mrz_result.get("issuing_country"))

    if mrz_result["mrz_type"] == "TD3":
        add("passport_number", mrz_result.get("passport_number"), "passport_number")
        add("date_of_birth", mrz_result.get("date_of_birth"), "date_of_birth")
        add("expiry_date", mrz_result.get("expiry_date"), "expiry_date")
        add("personal_number", mrz_result.get("personal_number"), "personal_number")
    elif mrz_result["mrz_type"] == "TD1":
        add("document_number", mrz_result.get("document_number"), "document_number")
        add("date_of_birth", mrz_result.get("date_of_birth"), "date_of_birth")
        add("expiry_date", mrz_result.get("expiry_date"), "expiry_date")

    return fields


def _cross_check_visual_zone(extracted_fields: list, raw_text: str) -> dict:
    """
    Compare MRZ-derived fields against what visual-zone OCR independently
    found (dates, passport-number-shaped strings, name tokens). This is
    the 'two independent sources' consistency check the spec calls for —
    it's cheap to compute here and very useful to the validation module.

    Name tokens are surfaced raw (not auto-merged into a "corrected" name)
    because names have no checksum to arbitrate between the two readings
    when they disagree -- better to hand both to a human/downstream rule
    than to silently guess.
    """
    visual_dates = extract_dates(raw_text)
    visual_passport_candidates = extract_passport_number_candidates(raw_text)
    visual_name_tokens = extract_visual_name_tokens(raw_text)

    mrz_field_map = {f["field_name"]: f["value"] for f in extracted_fields}
    findings = []

    if "passport_number" in mrz_field_map:
        mrz_num = mrz_field_map["passport_number"]
        if visual_passport_candidates and mrz_num not in visual_passport_candidates:
            findings.append({
                "type": "passport_number_visual_mrz_mismatch",
                "mrz_value": mrz_num,
                "visual_candidates": visual_passport_candidates,
            })

    return {
        "visual_dates_found": visual_dates,
        "visual_passport_number_candidates": visual_passport_candidates,
        "visual_name_tokens": visual_name_tokens,
        "consistency_findings": findings,
    }


def analyze_document(image_path: str, document_type_hint: str = None, page_number: int = 0) -> dict:
    """
    Run the full document analysis pipeline on a single document image
    or PDF page.

    `page_number` only applies to PDF input (0 = first page).

    Returns a dict matching the intended /api/v1/ocr response contract:
    {
        status, document_type, quality, extracted_fields, mrz,
        visual_zone_crosscheck, visa_fields, processing_time_ms
    }
    """
    start = time.time()

    pre = preprocess_pipeline(image_path, page_number=page_number)
    quality = pre["quality"]

    if not quality["passed"]:
        # Fail-safe behavior per the spec: don't run OCR on unusable
        # images, ask for a rescan instead of guessing.
        return {
            "status": "rescan_required",
            "quality": quality,
            "processing_time_ms": round((time.time() - start) * 1000, 1),
        }

    raw_text = extract_raw_text(pre["ocr_ready"])

    # Detect document type using a multi-PSM combined text pass rather than
    # the single raw_text reading -- ID cards are visually busier than a
    # passport bio page (watermarks, background patterns), so a single OCR
    # attempt can miss the exact keyword phrase a classifier looks for even
    # on an otherwise-readable image. This lets us skip the expensive MRZ
    # search entirely for document types that never have one (Aadhaar, PAN,
    # Voter ID, Driving License are not MRZ documents -- only passports/
    # visas/national IDs use the ICAO MRZ format).
    detection_text = extract_raw_text_multi_psm(pre["ocr_ready"])
    early_doc_type = detect_document_type(detection_text, mrz_found=False, mrz_type=None)

    if early_doc_type in ("aadhaar", "pan_card", "voter_id", "driving_license"):
        # Use the combined multi-PSM text for field extraction too -- more
        # independent readings only helps regex-based matching find the
        # right fields, same reasoning as for detection above.
        indian_id_result = extract_indian_id_fields(early_doc_type, detection_text)
        extracted_fields = [
            {
                "field_name": f["field_name"], "value": f["value"],
                "confidence": f["confidence"], "source": f["source"],
                "checksum_verified": f["checksum_verified"],
            }
            for f in indian_id_result["fields"]
        ]
        words = extract_words_with_confidence(pre["ocr_ready"])
        avg_word_conf = round(statistics.mean([w["confidence"] for w in words]) / 100, 3) if words else 0.0
        return {
            "status": "success",
            "document_type": early_doc_type,
            "quality": quality,
            "ocr_summary": {"average_word_confidence": avg_word_conf, "word_count": len(words)},
            "extracted_fields": extracted_fields,
            "document_checksum_verified": indian_id_result["checksum_verified"],
            "raw_ocr_text": raw_text,
            "processing_time_ms": round((time.time() - start) * 1000, 1),
        }

    # Otherwise, proceed with the MRZ pipeline (passport / visa / national ID).
    # Pick which region of the document actually contains the MRZ (rather
    # than assuming a fixed position), then run the full OCR ensemble only
    # on that winning band -- keeps total OCR calls bounded while still
    # adapting to different document layouts.
    best_band = select_best_mrz_band(pre["mrz_band_candidates"])
    mrz_variants = generate_mrz_variants(best_band)
    mrz_raw_texts = extract_mrz_text_multi(mrz_variants)

    mrz_result = parse_mrz_best_effort(mrz_raw_texts)

    # Names have no ICAO check digit, so the checksum-guided repair above
    # can't verify/fix them. Cross-check against the visual zone (ordinary
    # printed text, not the filler-heavy MRZ format) to catch phantom
    # inserted characters -- the most common Tesseract failure mode here.
    if mrz_result.get("surname"):
        mrz_result["surname"] = correct_name_field_with_visual(mrz_result["surname"], raw_text)
    if mrz_result.get("given_names"):
        mrz_result["given_names"] = correct_name_field_with_visual(mrz_result["given_names"], raw_text)

    doc_type = document_type_hint or detect_document_type(
        raw_text, mrz_found=mrz_result.get("mrz_type") is not None,
        mrz_type=mrz_result.get("mrz_type")
    )

    extracted_fields = _build_extracted_fields(mrz_result, source="mrz")
    crosscheck = _cross_check_visual_zone(extracted_fields, raw_text)

    visa_fields = extract_visa_fields(raw_text) if doc_type == "visa" else {}

    # Word-level confidence summary, useful for the officer dashboard's
    # "OCR ✓/⚠" status without showing every single word.
    words = extract_words_with_confidence(pre["ocr_ready"])
    avg_word_conf = round(statistics.mean([w["confidence"] for w in words]) / 100, 3) if words else 0.0

    result = {
        "status": "success",
        "document_type": doc_type,
        "quality": quality,
        "ocr_summary": {
            "average_word_confidence": avg_word_conf,
            "word_count": len(words),
        },
        "extracted_fields": extracted_fields,
        "mrz": {
            "mrz_type": mrz_result.get("mrz_type"),
            "all_checks_passed": mrz_result.get("all_checks_passed", False),
            "check_digit_results": mrz_result.get("check_digit_results", {}),
            "raw_lines": mrz_result.get("raw_lines", []),
            "error": mrz_result.get("error"),
        },
        "visual_zone_crosscheck": crosscheck,
        "visa_fields": visa_fields,
        "raw_ocr_text": raw_text,
        "processing_time_ms": round((time.time() - start) * 1000, 1),
    }
    return result


def print_clean_summary(result: dict) -> None:
    """
    Human-readable terminal summary -- just the fields that matter,
    with a plain OK/mismatch next to each checksum-protected one.
    The full result dict (with raw_ocr_text, visual_name_tokens, etc.)
    is still what gets returned to code that imports analyze_document()
    directly, e.g. a teammate's FastAPI endpoint -- this function only
    changes what gets printed when you run this file from the terminal.
    """
    print("=" * 50)
    if result["status"] != "success":
        print(f"STATUS: {result['status'].upper()}")
        if result["status"] == "rescan_required":
            print("Reason: image quality too low to trust OCR on.")
            print(f"Issues found: {', '.join(result['quality']['issues'])}")
        print("=" * 50)
        return

    print(f"DOCUMENT TYPE: {result['document_type']}")
    print("=" * 50)

    # These fields have no check digit in the MRZ standard at all (ICAO
    # 9303 only protects passport/document number, DOB, and expiry) --
    # for these, "no checksum exists" is a fact about the field type,
    # not a problem with the reading. Label them differently from a
    # field that HAS a checksum and actually failed it.
    _no_checksum_fields = {
        "surname", "given_names", "nationality", "sex", "issuing_country",
        "name", "father_or_husband_name", "gender", "state",
        "vehicle_class", "holder_type",
    }

    for field in result["extracted_fields"]:
        field_key = field["field_name"]
        name = field_key.replace("_", " ").title()
        value = field["value"]
        if field.get("checksum_verified"):
            mark = "OK"
        elif field_key in _no_checksum_fields:
            mark = "no checksum for this field"
        else:
            mark = "checksum FAILED"
        print(f"{name:20s} {value}   [{mark}]")

    print("=" * 50)
    mrz = result.get("mrz", {})
    if mrz.get("mrz_type"):
        status = "ALL CHECKS PASSED" if mrz.get("all_checks_passed") else "SOME CHECKS FAILED"
        print(f"MRZ: {status}")

    findings = result.get("visual_zone_crosscheck", {}).get("consistency_findings", [])
    if findings:
        print(f"\nWARNING: {len(findings)} inconsistency(ies) between MRZ and visual zone:")
        for f in findings:
            print(f"  - {f}")

    print(f"\n(processed in {result['processing_time_ms']} ms)")
    print("=" * 50)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python document_analysis_combined.py <path_to_document> [pdf_page_number] [--json]")
        print("Supported formats: .jpg, .jpeg, .png, .bmp, .tiff, .webp, .pdf")
        print("Add --json at the end to see the full raw output instead of the summary.")
        sys.exit(1)

    want_full_json = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--json"]
    page_num = int(args[1]) if len(args) > 1 else 0

    output = analyze_document(args[0], page_number=page_num)

    if want_full_json:
        print(json.dumps(output, indent=2, default=str))
    else:
        print_clean_summary(output)
