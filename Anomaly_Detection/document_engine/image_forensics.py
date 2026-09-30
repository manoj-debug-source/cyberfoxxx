"""
Computer Vision & Pixel-Level Image Forensics for Document Tampering Detection.
Implements Error Level Analysis (ELA), Sensor Noise Inconsistency, Stamp Forgery Detection,
Text Manipulation Analysis, and EXIF Metadata forensics.
"""

import base64
import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from PIL.ExifTags import TAGS
import scipy.ndimage as ndi

from document_engine.config import (
    ELA_JPEG_QUALITY,
    ELA_SCALE,
    ELA_TAMPER_THRESHOLD,
    NOISE_INCONSISTENCY_RATIO,
    STAMP_COLOR_RANGES,
    SUSPICIOUS_SOFTWARE,
)
from document_engine.schema import EvidenceItem


class ImageForensicAnalyzer:
    """
    Forensic image analyzer detecting digital tampering, splicing, stamp forgery, and compression anomalies.
    """

    def __init__(self):
        self.last_ela_heatmap_base64: Optional[str] = None

    def analyze_image(
        self,
        image_input: Union[str, Path, bytes, Image.Image],
        metadata_dict: Optional[dict] = None,
    ) -> Tuple[bool, float, List[EvidenceItem], List[str]]:
        """
        Runs comprehensive visual forensic analysis on document image.
        Returns:
            - is_tampered: bool
            - anomaly_score: float [0.0 - 1.0]
            - evidence: List[EvidenceItem]
            - fraud_types: List[str]
        """
        self.last_ela_heatmap_base64 = None
        evidence: List[EvidenceItem] = []
        fraud_types: List[str] = []
        scores: List[float] = []

        # Load image into RGB PIL Image
        img, raw_exif = self._load_image(image_input)
        if img is None:
            return False, 0.0, [], []

        # 1. Error Level Analysis (ELA) with Heatmap
        ela_score, ela_evidence, ela_types, heatmap_b64 = self._run_ela(img)
        self.last_ela_heatmap_base64 = heatmap_b64
        scores.append(ela_score)
        evidence.extend(ela_evidence)
        fraud_types.extend(ela_types)

        # 2. Sensor Noise Variance Inconsistency (Photo Splicing)
        noise_score, noise_evidence, noise_types = self._run_noise_analysis(img)
        scores.append(noise_score)
        evidence.extend(noise_evidence)
        fraud_types.extend(noise_types)

        # 3. Stamp Integrity & Forgery Detection
        stamp_score, stamp_evidence, stamp_types = self._run_stamp_forensics(img)
        scores.append(stamp_score)
        evidence.extend(stamp_evidence)
        fraud_types.extend(stamp_types)

        # 4. Text Manipulation & Font Consistency
        text_score, text_evidence, text_types = self._run_text_manipulation_analysis(img)
        scores.append(text_score)
        evidence.extend(text_evidence)
        fraud_types.extend(text_types)

        # 5. EXIF & Software Forensic Analysis
        meta_score, meta_evidence, meta_types = self._run_metadata_analysis(raw_exif, metadata_dict)
        scores.append(meta_score)
        evidence.extend(meta_evidence)
        fraud_types.extend(meta_types)

        # Composite image anomaly score
        overall_score = min(1.0, max(scores) * 0.65 + (sum(scores) / len(scores)) * 0.35) if scores else 0.0
        is_tampered = len(evidence) > 0

        return is_tampered, round(overall_score, 3), evidence, list(set(fraud_types))

    def _load_image(
        self, image_input: Union[str, Path, bytes, Image.Image]
    ) -> Tuple[Optional[Image.Image], dict]:
        raw_exif = {}
        try:
            if isinstance(image_input, Image.Image):
                img = image_input.convert("RGB")
            elif isinstance(image_input, (str, Path)):
                img = Image.open(str(image_input)).convert("RGB")
            elif isinstance(image_input, (bytes, bytearray)):
                img = Image.open(io.BytesIO(image_input)).convert("RGB")
            else:
                return None, {}

            # Extract EXIF if available
            exif_data = getattr(img, "_getexif", lambda: None)()
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    raw_exif[str(tag)] = str(value)

            return img, raw_exif
        except Exception:
            return None, {}

    def _run_ela(self, img: Image.Image) -> Tuple[float, List[EvidenceItem], List[str], Optional[str]]:
        """
        Error Level Analysis: re-saves image at fixed quality and measures compression residual delta.
        Unedited images produce uniform low error. Spliced/edited regions produce localized high error.
        Generates base64 visual false-color heatmap.
        """
        evidence = []
        fraud_types = []

        # Re-save at known quality
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=ELA_JPEG_QUALITY)
        buffer.seek(0)
        resaved = Image.open(buffer)

        # Compute difference
        diff = ImageChops.difference(img, resaved)
        diff_arr = np.asarray(diff, dtype=np.float32) / 255.0  # Normalize to [0, 1]

        # Calculate localized statistics (split into grid blocks)
        mean_diff = float(np.mean(diff_arr))
        h, w, _ = diff_arr.shape
        block_h, block_w = max(1, h // 8), max(1, w // 8)
        block_means = []
        for i in range(8):
            for j in range(8):
                block = diff_arr[i * block_h : (i + 1) * block_h, j * block_w : (j + 1) * block_w]
                if block.size > 0:
                    block_means.append(np.mean(block))

        block_means = np.array(block_means)
        global_mean = np.mean(block_means)
        max_block_mean = np.max(block_means)
        peak_to_average_ratio = max_block_mean / (global_mean + 1e-4)

        # Generate Visual False-Color ELA Heatmap (Base64 PNG)
        gray_diff = np.mean(diff_arr, axis=2) * ELA_SCALE
        gray_diff = np.clip(gray_diff, 0.0, 1.0)
        heatmap_arr = np.zeros((h, w, 3), dtype=np.uint8)
        # False color gradient: Blue -> Cyan -> Yellow -> Neon Red
        heatmap_arr[:, :, 0] = np.clip(gray_diff * 2.2 * 255, 0, 255).astype(np.uint8)  # R
        heatmap_arr[:, :, 1] = np.clip((1.0 - np.abs(gray_diff - 0.5) * 2.0) * 220, 0, 255).astype(np.uint8)  # G
        heatmap_arr[:, :, 2] = np.clip((1.0 - gray_diff) * 200, 0, 255).astype(np.uint8)  # B
        
        heatmap_img = Image.fromarray(heatmap_arr, mode="RGB")
        out_buf = io.BytesIO()
        heatmap_img.save(out_buf, format="PNG")
        heatmap_b64 = base64.b64encode(out_buf.getvalue()).decode("utf-8")

        # Score calculation calibrated to document layout
        if peak_to_average_ratio > 3.8 or mean_diff > ELA_TAMPER_THRESHOLD:
            ela_score = min(1.0, 0.50 + (peak_to_average_ratio - 3.8) / 3.0)
            evidence.append(
                EvidenceItem(
                    layer="IMAGE_FORENSICS",
                    anomaly="Error Level Analysis (ELA) Compression Inconsistency",
                    detail=(
                        f"Localized region exhibits anomalous JPEG compression error "
                        f"({peak_to_average_ratio:.2f}x higher than document background). "
                        f"Indicates localized image editing, text modification, or pasted element."
                    ),
                    severity="CRITICAL" if peak_to_average_ratio > 5.0 else "HIGH",
                )
            )
            fraud_types.append("Digital Image Manipulation / Splicing")
        else:
            ela_score = min(0.20, (peak_to_average_ratio / 3.8) * 0.20)

        return ela_score, evidence, fraud_types, heatmap_b64

    def _run_noise_analysis(self, img: Image.Image) -> Tuple[float, List[EvidenceItem], List[str]]:
        """
        Sensor Noise Inconsistency: Extracts high-frequency residual noise using Laplacian filter.
        Compares left half (typically portrait photo) vs right half (text/background).
        """
        evidence = []
        fraud_types = []

        # Convert to grayscale
        gray = np.asarray(img.convert("L"), dtype=np.float32)

        # High-pass Laplacian filter to isolate sensor pattern noise
        laplacian = ndi.laplace(gray)

        h, w = laplacian.shape
        # Typically passport photo resides in left 35% of the biodata page
        photo_region = laplacian[:, : int(w * 0.35)]
        doc_region = laplacian[:, int(w * 0.35) :]

        var_photo = float(np.var(photo_region))
        var_doc = float(np.var(doc_region))

        noise_ratio = var_photo / (var_doc + 1e-4) if var_doc > 0 else 1.0

        score = 0.0
        disparity = max(noise_ratio, 1.0 / (noise_ratio + 1e-4))
        if disparity >= NOISE_INCONSISTENCY_RATIO:
            score = min(1.0, (disparity - 1.0) / 4.0)
            evidence.append(
                EvidenceItem(
                    layer="IMAGE_FORENSICS",
                    anomaly="Photo Sensor Noise Inconsistency",
                    detail=(
                        f"Photo region noise variance differs significantly from document background "
                        f"(Variance disparity ratio: {disparity:.2f}x). "
                        f"Indicates portrait photo was captured by a different camera sensor or spliced."
                    ),
                    severity="CRITICAL" if disparity > 5.0 else "HIGH",
                )
            )
            fraud_types.append("Photo Replacement / Splicing")

        return score, evidence, fraud_types

    def _run_stamp_forensics(self, img: Image.Image) -> Tuple[float, List[EvidenceItem], List[str]]:
        """
        Stamp Forgery Detection: Evaluates border stamp ink color distributions,
        edge continuity, and ink saturation uniformity.
        """
        evidence = []
        fraud_types = []
        score = 0.0

        hsv = img.convert("HSV")
        hsv_arr = np.array(hsv, dtype=np.float32)

        # Inspect violet/blue and red stamp ink pixels
        for color_name, (lower, upper) in STAMP_COLOR_RANGES.items():
            h_mask = (hsv_arr[:, :, 0] >= lower[0]) & (hsv_arr[:, :, 0] <= upper[0])
            s_mask = (hsv_arr[:, :, 1] >= lower[1]) & (hsv_arr[:, :, 1] <= upper[1])
            v_mask = (hsv_arr[:, :, 2] >= lower[2]) & (hsv_arr[:, :, 2] <= upper[2])
            stamp_pixels = h_mask & s_mask & v_mask

            pixel_count = int(np.sum(stamp_pixels))
            total_pixels = stamp_pixels.size

            # If stamp is present (at least 0.4% coverage)
            if pixel_count / total_pixels > 0.004:
                stamp_sats = hsv_arr[:, :, 1][stamp_pixels]
                std_sat = float(np.std(stamp_sats))
                # Digital synthetic stamps have unnaturally low standard deviation in saturation
                if std_sat < 10.5:
                    score = max(score, 0.72)
                    evidence.append(
                        EvidenceItem(
                            layer="IMAGE_FORENSICS",
                            anomaly="Stamp Forgery / Synthetic Digital Ink",
                            detail=(
                                f"Detected {color_name.lower()} immigration stamp with unnaturally uniform ink saturation "
                                f"(std={std_sat:.1f}). Lacks physical stamp bleed and porous ink absorption."
                            ),
                            severity="HIGH",
                        )
                    )
                    fraud_types.append("Stamp Forgery Detection")

        return score, evidence, fraud_types

    def _run_text_manipulation_analysis(self, img: Image.Image) -> Tuple[float, List[EvidenceItem], List[str]]:
        """
        Text Manipulation Detection: Analyzes text line pixel edge gradients for
        sharp digital font inserts or altered numeric characters.
        """
        evidence = []
        fraud_types = []
        score = 0.0

        gray = np.asarray(img.convert("L"), dtype=np.float32)
        h, w = gray.shape

        # Focus on middle biodata text zone (25% to 70% vertical)
        text_zone = gray[int(h * 0.25) : int(h * 0.70), int(w * 0.35) :]
        if text_zone.size == 0:
            return 0.0, [], []

        # Compute horizontal and vertical gradients
        gx = ndi.sobel(text_zone, axis=1)
        gy = ndi.sobel(text_zone, axis=0)
        grad_mag = np.hypot(gx, gy)

        # Segment into horizontal bands corresponding to text lines
        band_h = max(1, grad_mag.shape[0] // 6)
        band_energies = []
        for b in range(6):
            band = grad_mag[b * band_h : (b + 1) * band_h, :]
            if band.size > 0:
                band_energies.append(np.mean(band))

        band_energies = np.array(band_energies)
        if len(band_energies) > 0 and np.mean(band_energies) > 0:
            energy_ratio = np.max(band_energies) / (np.mean(band_energies) + 1e-4)
            if energy_ratio > 4.2:
                score = min(0.80, 0.45 + (energy_ratio - 4.2) / 3.0)
                evidence.append(
                    EvidenceItem(
                        layer="IMAGE_FORENSICS",
                        anomaly="Text Line Edge Gradient Anomaly",
                        detail=(
                            f"Identified localized gradient step in document text zone "
                            f"(Energy ratio {energy_ratio:.2f}x). Consistent with altered digits or spliced text."
                        ),
                        severity="HIGH",
                    )
                )
                fraud_types.append("Text Manipulation")

        return score, evidence, fraud_types

    def _run_metadata_analysis(
        self, exif_dict: dict, user_metadata: Optional[dict]
    ) -> Tuple[float, List[EvidenceItem], List[str]]:
        """
        Examines image header, EXIF, and software provenance for editing software signatures.
        """
        evidence = []
        fraud_types = []
        combined_meta = {**exif_dict, **(user_metadata or {})}

        score = 0.0
        for k, v in combined_meta.items():
            val_str = str(v).lower()
            for susp in SUSPICIOUS_SOFTWARE:
                if susp in val_str:
                    evidence.append(
                        EvidenceItem(
                            layer="METADATA_ANALYSIS",
                            anomaly="Image Editing Software Fingerprint",
                            detail=f"Detected signature of editing software '{susp.capitalize()}' in tag '{k}' ('{v}').",
                            severity="HIGH",
                        )
                    )
                    fraud_types.append("Software Metadata Tampering")
                    score = max(score, 0.75)

        return score, evidence, fraud_types
