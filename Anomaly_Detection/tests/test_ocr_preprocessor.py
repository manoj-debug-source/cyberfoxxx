"""
Unit tests for DocumentPreprocessor (Module 1 Data Preprocessing) and OCRExtractor.
"""

import numpy as np
from PIL import Image
from document_engine.ocr_preprocessor import DocumentPreprocessor
from document_engine.ocr_extractor import OCRExtractor


def test_preprocessor_load_and_otsu():
    preprocessor = DocumentPreprocessor()
    # Create test synthetic image
    img = Image.new("RGB", (400, 300), color=(200, 200, 200))
    res = preprocessor.preprocess_for_ocr(img)

    assert "binary_otsu" in res
    assert "enhanced_gray" in res
    assert "otsu_threshold" in res
    assert 0 <= res["otsu_threshold"] <= 255


def test_preprocessor_roi_extraction():
    preprocessor = DocumentPreprocessor()
    img = Image.new("RGB", (800, 500), color=(255, 255, 255))

    mrz_img, mrz_box = preprocessor.extract_mrz_region(img)
    assert mrz_img.size[0] == 800
    assert mrz_box[1] > 300  # Top of MRZ is in bottom quadrant

    photo_img, photo_box = preprocessor.extract_photo_region(img)
    assert photo_box[0] < 100  # Left side
    assert photo_img.size[0] > 0 and photo_img.size[1] > 0


def test_ocr_extractor_mrz_parsing():
    extractor = OCRExtractor()
    line1 = "P<INDSHARMA<<ANANYA<<<<<<<<<<<<<<<<<<<<<<<<<"
    line2 = "Z8942105<8IND9605140F3205130<<<<<<<<<<<<<<<0"
    mrz_text = f"{line1}\n{line2}"

    res = extractor.parse_mrz(mrz_text)
    assert res is not None
    assert res.document_type == "PASSPORT"
    assert res.passport is not None
    assert res.passport.name == "ANANYA SHARMA"
    assert res.passport.passport_number == "Z8942105"
    assert res.passport.nationality == "IND"
    assert res.passport.gender == "F"
    assert res.passport.date_of_birth == "1996-05-14"
    assert res.passport.date_of_expiry == "2032-05-13"
    assert res.mrz_detected is True

