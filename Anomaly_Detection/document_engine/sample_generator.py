"""
Synthetic Document and Tampering Generator for SIH 2026 Testing and Demonstration.
Generates genuine passport images and simulates 6 realistic border checkpoint scenarios:
1. Genuine clean passport & matching live face (Dr. Ananya Sharma) -> CLEARED (NORMAL)
2. Text manipulation: modified expiry date causing MRZ mismatch (Tariq Al-Mansoor) -> REJECT
3. Photo replacement: spliced portrait with sensor noise & Photoshop EXIF (Marcus Vance) -> REJECT
4. Identity impersonation: genuine document with mismatched live passenger face (David Miller) -> REJECT
5. Visa stamp forgery: synthetic digital stamp & stay duration anomaly (Elena Rostova) -> SECONDARY
6. Watchlist hit: Interpol Red Notice / SSB Lookout Circular (Vikram Malhotra) -> CODE RED DETAIN
"""

import io
from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from document_engine.mrz_validator import generate_mrz_lines
from document_engine.schema import PassportData, VisaData


def create_avatar_face(
    seed_id: int = 1,
    is_female: bool = False,
    skin_tone: Tuple[int, int, int] = (235, 195, 165),
    hair_color: Tuple[int, int, int] = (40, 25, 15),
    size: Tuple[int, int] = (200, 240),
) -> Image.Image:
    """
    Creates a standardized portrait face with 3D skin texture for face verification and anti-spoofing.
    """
    w, h = size
    img = Image.new("RGB", size, color=(210, 220, 230))
    draw = ImageDraw.Draw(img)

    # Hair back
    hair_top = int(h * 0.10)
    draw.ellipse([(int(w * 0.15), hair_top), (int(w * 0.85), int(h * 0.75))], fill=hair_color)

    # Neck
    draw.rectangle([(int(w * 0.38), int(h * 0.65)), (int(w * 0.62), int(h * 0.85))], fill=skin_tone)

    # Face Oval
    face_bbox = [(int(w * 0.22), int(h * 0.20)), (int(w * 0.78), int(h * 0.78))]
    draw.ellipse(face_bbox, fill=skin_tone, outline=(skin_tone[0] - 30, skin_tone[1] - 30, skin_tone[2] - 30), width=2)

    # Hair front / style
    if is_female:
        draw.chord([(int(w * 0.18), int(h * 0.12)), (int(w * 0.82), int(h * 0.45))], 180, 360, fill=hair_color)
        draw.rectangle([(int(w * 0.15), int(h * 0.25)), (int(w * 0.28), int(h * 0.75))], fill=hair_color)
        draw.rectangle([(int(w * 0.72), int(h * 0.25)), (int(w * 0.85), int(h * 0.75))], fill=hair_color)
    else:
        draw.pieslice([(int(w * 0.20), int(h * 0.10)), (int(w * 0.80), int(h * 0.42))], 180, 360, fill=hair_color)

    # Eyebrows & Eyes
    eye_y = int(h * 0.42)
    # Left eye
    draw.line([(int(w * 0.30), eye_y - 12), (int(w * 0.44), eye_y - 10)], fill=hair_color, width=3)
    draw.ellipse([(int(w * 0.32), eye_y - 6), (int(w * 0.42), eye_y + 6)], fill=(255, 255, 255), outline=(50, 50, 50))
    pupil_x = int(w * 0.37) + (seed_id % 3 - 1)
    draw.ellipse([(pupil_x - 3, eye_y - 4), (pupil_x + 3, eye_y + 4)], fill=(40, 30, 20))

    # Right eye
    draw.line([(int(w * 0.56), eye_y - 10), (int(w * 0.70), eye_y - 12)], fill=hair_color, width=3)
    draw.ellipse([(int(w * 0.58), eye_y - 6), (int(w * 0.68), eye_y + 6)], fill=(255, 255, 255), outline=(50, 50, 50))
    pupil_xr = int(w * 0.63) + (seed_id % 3 - 1)
    draw.ellipse([(pupil_xr - 3, eye_y - 4), (pupil_xr + 3, eye_y + 4)], fill=(40, 30, 20))

    # Nose
    nose_y = int(h * 0.54)
    draw.line([(int(w * 0.50), eye_y + 4), (int(w * 0.47), nose_y)], fill=(skin_tone[0] - 40, skin_tone[1] - 40, skin_tone[2] - 40), width=2)
    draw.line([(int(w * 0.47), nose_y), (int(w * 0.53), nose_y)], fill=(skin_tone[0] - 40, skin_tone[1] - 40, skin_tone[2] - 40), width=2)

    # Mouth
    mouth_y = int(h * 0.66)
    draw.arc([(int(w * 0.40), mouth_y - 4), (int(w * 0.60), mouth_y + 8)], 0, 180, fill=(180, 70, 70), width=3)

    # Add realistic biological skin texture
    arr = np.array(img, dtype=np.float32)
    noise = np.random.normal(0, 7.5, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def _draw_passport_base(passport: PassportData, portrait_face: Image.Image) -> Image.Image:
    """
    Renders standard high-resolution passport biodata page with guilloche patterns and MRZ.
    """
    img = Image.new("RGB", (800, 500), color=(240, 245, 250))
    draw = ImageDraw.Draw(img)

    # Security guilloche-like background lines
    for y in range(0, 500, 20):
        draw.line([(0, y), (800, y + 12)], fill=(225, 235, 245), width=1)
    for x in range(0, 800, 30):
        draw.line([(x, 0), (x + 15, 500)], fill=(230, 238, 246), width=1)

    # Header
    draw.rectangle([(20, 20), (780, 70)], fill=(30, 55, 90))
    draw.text((30, 32), f"GOVERNMENT OF {passport.nationality} - PASSPORT / PASSEPORT", fill=(255, 255, 255))

    # Paste Portrait photo in left zone
    face_resized = portrait_face.resize((180, 220), Image.Resampling.BILINEAR)
    img.paste(face_resized, (50, 90))
    draw.rectangle([(50, 90), (230, 310)], outline=(80, 110, 140), width=2)

    # Text fields
    fields = [
        ("Type / Type", "P"),
        ("Country Code", passport.nationality),
        ("Passport No.", passport.passport_number),
        ("Full Name / Nom", passport.name),
        ("Nationality", passport.nationality),
        ("Date of Birth", passport.date_of_birth),
        ("Sex / Sexe", passport.gender),
        ("Date of Expiry", passport.date_of_expiry),
    ]

    x, y = 260, 90
    for label, val in fields:
        draw.text((x, y), f"{label}: ", fill=(90, 100, 110))
        draw.text((x + 180, y), str(val), fill=(20, 30, 40))
        y += 24

    # MRZ Zone (bottom)
    draw.rectangle([(20, 385), (780, 480)], fill=(255, 255, 255), outline=(180, 190, 200))
    l1 = passport.mrz_line1 or ""
    l2 = passport.mrz_line2 or ""
    draw.text((35, 400), l1, fill=(0, 0, 0))
    draw.text((35, 435), l2, fill=(0, 0, 0))

    return img


def generate_genuine_sample() -> Tuple[Image.Image, PassportData, VisaData, Image.Image]:
    """
    Scenario 1: Verified Genuine Indian Passport (Dr. Ananya Sharma) & Matching Live Camera Face.
    Expected: CLEARED (NORMAL)
    """
    passport = PassportData(
        name="ANANYA SHARMA",
        passport_number="Z8942105",
        nationality="IND",
        date_of_birth="1996-05-14",
        date_of_expiry="2032-05-13",
        gender="F",
    )
    l1, l2 = generate_mrz_lines(passport)
    passport.mrz_line1 = l1
    passport.mrz_line2 = l2

    visa = VisaData(
        visa_number="V7821904",
        visa_type="TOURIST",
        entry_validation_date="2026-09-01",
        expiry_date="2026-12-01",
        stay_duration_days=30,
    )

    portrait_face = create_avatar_face(seed_id=101, is_female=True)
    img = _draw_passport_base(passport, portrait_face)

    # Re-save as clean uniform JPEG
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    clean_img = Image.open(buf).convert("RGB")

    # Live passenger face matches document photo exactly (with slight lighting variation)
    live_face = create_avatar_face(seed_id=101, is_female=True)

    return clean_img, passport, visa, live_face


def generate_tampered_expiry_sample() -> Tuple[Image.Image, PassportData, VisaData, Image.Image]:
    """
    Scenario 2: Tampered Expiry Date (Tariq Al-Mansoor).
    Visual date altered to 2034 while MRZ says 2032. Localized ELA artifact on expiry field.
    Expected: REJECT & DETAIN (CRITICAL)
    """
    passport = PassportData(
        name="TARIQ AL-MANSOOR",
        passport_number="T9821450",
        nationality="ARE",
        date_of_birth="1988-11-20",
        date_of_expiry="2032-05-13",
        gender="M",
    )
    l1, l2 = generate_mrz_lines(passport)
    passport.mrz_line1 = l1
    passport.mrz_line2 = l2

    portrait_face = create_avatar_face(seed_id=202, is_female=False)
    img = _draw_passport_base(passport, portrait_face)

    # Tamper visual expiry date to 2034
    passport.date_of_expiry = "2034-05-13"
    draw = ImageDraw.Draw(img)
    draw.rectangle([(430, 255), (580, 280)], fill=(255, 255, 255))
    draw.text((440, 258), "2034-05-13", fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=68)
    buf.seek(0)
    tampered_img = Image.open(buf).convert("RGB")

    live_face = create_avatar_face(seed_id=202, is_female=False)
    visa = None

    return tampered_img, passport, visa, live_face


def generate_photo_replacement_sample() -> Tuple[Image.Image, PassportData, VisaData, dict, Image.Image]:
    """
    Scenario 3: Spliced Photo Replacement (Marcus Vance).
    High noise disparity on photo, Photoshop metadata fingerprint.
    Expected: REJECT & DETAIN (CRITICAL)
    """
    passport = PassportData(
        name="MARCUS VANCE",
        passport_number="GB871203",
        nationality="GBR",
        date_of_birth="1992-04-18",
        date_of_expiry="2031-08-22",
        gender="M",
    )
    l1, l2 = generate_mrz_lines(passport)
    passport.mrz_line1 = l1
    passport.mrz_line2 = l2

    orig_face = create_avatar_face(seed_id=303, is_female=False)
    img = _draw_passport_base(passport, orig_face)

    # Spliced photo: completely different face pasted with heavy sensor noise
    spliced_face = create_avatar_face(seed_id=399, is_female=False, skin_tone=(245, 215, 190), hair_color=(180, 140, 40))
    spliced_arr = np.array(spliced_face, dtype=np.float32)
    spliced_arr += np.random.normal(0, 42, spliced_arr.shape)  # Heavy sensor noise
    spliced_noisy = Image.fromarray(np.clip(spliced_arr, 0, 255).astype(np.uint8)).resize((180, 220))
    img.paste(spliced_noisy, (50, 90))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    buf.seek(0)
    spliced_img = Image.open(buf).convert("RGB")

    metadata = {
        "Software": "Adobe Photoshop 2024 (Windows)",
        "ModifyDate": "2026-09-12 19:42:10",
    }

    # Live face presented matches the spliced face (the imposter who altered the document)
    live_face = spliced_face

    return spliced_img, passport, None, metadata, live_face


def generate_face_mismatch_sample() -> Tuple[Image.Image, PassportData, VisaData, Image.Image]:
    """
    Scenario 4: Identity Impersonation / Face Mismatch (David Miller / Live Imposter).
    Document is 100% genuine, but the live individual in front of camera is an imposter.
    Expected: REJECT & DETAIN (CRITICAL)
    """
    passport = PassportData(
        name="DAVID MILLER",
        passport_number="U4491028",
        nationality="USA",
        date_of_birth="1985-07-25",
        date_of_expiry="2033-01-15",
        gender="M",
    )
    l1, l2 = generate_mrz_lines(passport)
    passport.mrz_line1 = l1
    passport.mrz_line2 = l2

    doc_face = create_avatar_face(seed_id=404, is_female=False, hair_color=(20, 20, 20))
    img = _draw_passport_base(passport, doc_face)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    clean_img = Image.open(buf).convert("RGB")

    # Live face is an imposter (different ethnicity, face shape, hair)
    imposter_face = create_avatar_face(seed_id=888, is_female=True, skin_tone=(200, 160, 130), hair_color=(120, 30, 20))

    return clean_img, passport, None, imposter_face


def generate_stamp_forgery_sample() -> Tuple[Image.Image, PassportData, VisaData, Image.Image]:
    """
    Scenario 5: Visa Stamp Forgery & Stay Duration Overstay (Elena Rostova).
    Digital stamp overlay with unnatural uniform ink saturation, plus 60 days stay requested on 14 days visa.
    Expected: SECONDARY INSPECTION (HIGH)
    """
    passport = PassportData(
        name="ELENA ROSTOVA",
        passport_number="R5541092",
        nationality="RUS",
        date_of_birth="1994-03-10",
        date_of_expiry="2030-10-18",
        gender="F",
    )
    l1, l2 = generate_mrz_lines(passport)
    passport.mrz_line1 = l1
    passport.mrz_line2 = l2

    portrait_face = create_avatar_face(seed_id=505, is_female=True)
    img = _draw_passport_base(passport, portrait_face)

    # Draw synthetic digital stamp with perfectly uniform violet ink
    draw = ImageDraw.Draw(img)
    # Circle with uniform violet fill/outline
    draw.ellipse([(600, 180), (740, 320)], outline=(140, 50, 200), width=4)
    draw.text((615, 235), "IMMIGRATION", fill=(140, 50, 200))
    draw.text((625, 255), "ENTRY PERMIT", fill=(140, 50, 200))
    draw.text((630, 275), "DELHI BORDER", fill=(140, 50, 200))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    buf.seek(0)
    stamp_img = Image.open(buf).convert("RGB")

    visa = VisaData(
        visa_number="V992144",
        visa_type="TOURIST",
        entry_validation_date="2026-10-01",
        expiry_date="2026-10-15",
        stay_duration_days=60,  # Overstay
    )
    live_face = create_avatar_face(seed_id=505, is_female=True)

    return stamp_img, passport, visa, live_face


def generate_watchlist_hit_sample() -> Tuple[Image.Image, PassportData, VisaData, Image.Image]:
    """
    Scenario 6: Stolen Passport / Interpol Red Notice / SSB Lookout Circular (Vikram Malhotra).
    Passport Number M1983021 is actively blacklisted on SSB border watchlist.
    Expected: CODE RED ESCALATION & DETAIN (CRITICAL)
    """
    passport = PassportData(
        name="VIKRAM MALHOTRA",
        passport_number="M1983021",
        nationality="IND",
        date_of_birth="1982-08-14",
        date_of_expiry="2028-12-30",
        gender="M",
    )
    l1, l2 = generate_mrz_lines(passport)
    passport.mrz_line1 = l1
    passport.mrz_line2 = l2

    portrait_face = create_avatar_face(seed_id=606, is_female=False)
    img = _draw_passport_base(passport, portrait_face)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    clean_img = Image.open(buf).convert("RGB")

    live_face = create_avatar_face(seed_id=606, is_female=False)
    visa = None

    return clean_img, passport, visa, live_face

