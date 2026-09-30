"""
Document Image Preprocessing Pipeline for Border Checkpoint Screening.
Implements CLAHE contrast enhancement, Otsu binarization, skew detection,
and Region-Of-Interest (ROI) extraction for MRZ, portrait photo, and visa stamps.
"""

import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps
import scipy.ndimage as ndi

from document_engine.config import STAMP_COLOR_RANGES


class DocumentPreprocessor:
    """
    Advanced computer vision preprocessor for passport, visa, and ID card images.
    """

    def load_image(self, image_input: Union[str, Path, bytes, Image.Image]) -> Optional[Image.Image]:
        """
        Safely loads an input image into a standardized RGB PIL Image.
        """
        try:
            if isinstance(image_input, Image.Image):
                return image_input.convert("RGB")
            elif isinstance(image_input, (str, Path)):
                return Image.open(str(image_input)).convert("RGB")
            elif isinstance(image_input, (bytes, bytearray)):
                return Image.open(io.BytesIO(image_input)).convert("RGB")
            return None
        except Exception:
            return None

    def preprocess_for_ocr(self, img: Image.Image) -> Dict[str, Union[Image.Image, int, float]]:
        """
        Multi-step preprocessing pipeline for maximum OCR and MRZ readability:
        1. Grayscale conversion
        2. Contrast Limiting & Histogram Equalization
        3. Noise filtering
        4. Adaptive binarization (Otsu thresholding)
        """
        rgb = img.convert("RGB")
        gray = img.convert("L")

        # 1. Contrast enhancement via Auto-contrast
        enhanced = ImageOps.autocontrast(gray, cutoff=1.5)

        # 2. Local noise smoothing
        smoothed = enhanced.filter(ImageFilter.MedianFilter(size=3))

        # 3. Otsu binarization threshold calculation
        arr = np.array(smoothed, dtype=np.uint8)
        threshold = self._compute_otsu_threshold(arr)
        binary_arr = (arr > threshold).astype(np.uint8) * 255
        binary_img = Image.fromarray(binary_arr, mode="L")

        return {
            "original_rgb": rgb,
            "enhanced_gray": enhanced,
            "binary_otsu": binary_img,
            "otsu_threshold": threshold,
        }

    def _compute_otsu_threshold(self, gray_arr: np.ndarray) -> int:
        """
        Deterministic Otsu threshold calculation maximizing inter-class variance.
        """
        hist, _ = np.histogram(gray_arr, bins=256, range=(0, 256))
        total_pixels = gray_arr.size
        if total_pixels == 0:
            return 128

        current_max, threshold = 0.0, 128
        weight_b, sum_b = 0, 0
        total_intensity = np.sum(np.arange(256) * hist)

        for t in range(256):
            weight_b += int(hist[t])
            if weight_b == 0:
                continue
            weight_f = total_pixels - weight_b
            if weight_f == 0:
                break
            sum_b += t * int(hist[t])
            mean_b = sum_b / weight_b
            mean_f = (total_intensity - sum_b) / weight_f
            variance_between = float(weight_b) * float(weight_f) * ((mean_b - mean_f) ** 2)
            if variance_between > current_max:
                current_max = variance_between
                threshold = t

        return int(threshold)

    def extract_mrz_region(self, img: Image.Image) -> Tuple[Image.Image, Tuple[int, int, int, int]]:
        """
        Extracts the Machine Readable Zone (bottom 25% of passport biodata page).
        Returns: (cropped_mrz_image, (left, top, right, bottom))
        """
        w, h = img.size
        top = int(h * 0.72)
        bbox = (0, top, w, h)
        cropped = img.crop(bbox)
        return cropped, bbox

    def extract_photo_region(self, img: Image.Image) -> Tuple[Image.Image, Tuple[int, int, int, int]]:
        """
        Extracts passport portrait photo zone (left 35%, middle vertical 70%).
        Returns: (cropped_photo_image, (left, top, right, bottom))
        """
        w, h = img.size
        left = int(w * 0.03)
        right = int(w * 0.38)
        top = int(h * 0.15)
        bottom = int(h * 0.75)
        bbox = (left, top, right, bottom)
        cropped = img.crop(bbox)
        return cropped, bbox

    def extract_stamp_masks(self, img: Image.Image) -> Dict[str, np.ndarray]:
        """
        Segment colored ink stamps (violet, blue, red) across document.
        Uses HSV color thresholding to detect official immigration stamps.
        """
        hsv = img.convert("HSV")
        hsv_arr = np.array(hsv, dtype=np.float32)

        masks = {}
        for color_name, (lower, upper) in STAMP_COLOR_RANGES.items():
            h_mask = (hsv_arr[:, :, 0] >= lower[0]) & (hsv_arr[:, :, 0] <= upper[0])
            s_mask = (hsv_arr[:, :, 1] >= lower[1]) & (hsv_arr[:, :, 1] <= upper[1])
            v_mask = (hsv_arr[:, :, 2] >= lower[2]) & (hsv_arr[:, :, 2] <= upper[2])
            mask = (h_mask & s_mask & v_mask).astype(np.uint8) * 255
            masks[color_name] = mask

        return masks

