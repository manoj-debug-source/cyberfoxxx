"""
Module 1: OCR Extraction & ICAO 9303 MRZ Parsing Engine.
Extracts structured traveler identity data from Passports, Visas, and National IDs.
"""

import re
from typing import Dict, List, Optional, Tuple
from document_engine.schema import (
    NationalIDData,
    OCRResult,
    PassportData,
    VisaData,
)


class OCRExtractor:
    """
    Robust OCR Information Extraction engine for international border documents.
    """

    def parse_mrz(self, mrz_text: str) -> Optional[OCRResult]:
        """
        Parses Machine Readable Zone (MRZ) string containing 2 or 3 lines.
        Supports ICAO 9303 TD3 (Passports, 2x44) and TD1 (National IDs, 3x30).
        """
        raw_lines = [line.strip().upper() for line in mrz_text.splitlines() if line.strip()]
        # Filter out lines that do not look like MRZ characters
        mrz_lines = [re.sub(r"[^A-Z0-9<]", "", l) for l in raw_lines]
        mrz_lines = [l for l in mrz_lines if len(l) >= 28]

        if len(mrz_lines) >= 2 and len(mrz_lines[0]) >= 40 and len(mrz_lines[1]) >= 40:
            return self._parse_td3_passport(mrz_lines[0][:44], mrz_lines[1][:44])
        elif len(mrz_lines) >= 3 and len(mrz_lines[0]) >= 28 and len(mrz_lines[1]) >= 28:
            return self._parse_td1_national_id(mrz_lines[0][:30], mrz_lines[1][:30], mrz_lines[2][:30])

        return None

    def _parse_td3_passport(self, line1: str, line2: str) -> OCRResult:
        """
        Parses standard 2-line 44-character ICAO TD3 passport MRZ.
        Line 1: P<[NAT][SURNAME]<<[GIVENNAMES]...
        Line 2: [DOC_NO(9)][CD][NAT(3)][DOB(6)][CD][SEX(1)][EXP(6)][CD]...
        """
        # Line 1 parsing
        doc_type_code = line1[0:2].replace("<", "")
        country = line1[2:5].replace("<", "")
        name_segment = line1[5:].rstrip("<")

        if "<<" in name_segment:
            surname, given_names = name_segment.split("<<", 1)
            full_name = f"{given_names.replace('<', ' ')} {surname}".strip()
        else:
            full_name = name_segment.replace("<", " ").strip()

        # Line 2 parsing
        doc_number = line2[0:9].replace("<", "")
        mrz_doc_cd = line2[9] if len(line2) > 9 else "0"
        nationality = line2[10:13].replace("<", "") if len(line2) >= 13 else country
        dob_raw = line2[13:19] if len(line2) >= 19 else "000000"
        sex_char = line2[20] if len(line2) > 20 else "<"
        sex = "M" if sex_char == "M" else ("F" if sex_char == "F" else "X")
        expiry_raw = line2[21:27] if len(line2) >= 27 else "000000"

        # Format dates (YYMMDD -> YYYY-MM-DD heuristic)
        formatted_dob = self._format_yymmdd_to_iso(dob_raw, is_birth=True)
        formatted_expiry = self._format_yymmdd_to_iso(expiry_raw, is_birth=False)

        passport = PassportData(
            name=full_name.upper(),
            passport_number=doc_number.upper(),
            nationality=nationality.upper(),
            date_of_birth=formatted_dob,
            date_of_expiry=formatted_expiry,
            gender=sex,
            mrz_line1=line1,
            mrz_line2=line2,
        )

        full_transcript = f"PASSPORT: {full_name} | {doc_number} | {nationality} | DOB: {formatted_dob} | EXP: {formatted_expiry} | SEX: {sex}"

        return OCRResult(
            document_type="PASSPORT",
            passport=passport,
            mrz_detected=True,
            mrz_lines=[line1, line2],
            confidence=0.98,
            extracted_text=full_transcript,
        )

    def _parse_td1_national_id(self, line1: str, line2: str, line3: str) -> OCRResult:
        """
        Parses 3-line 30-character ICAO TD1 National ID card MRZ.
        """
        doc_number = line1[5:14].replace("<", "")
        dob_raw = line2[0:6]
        sex_char = line2[7] if len(line2) > 7 else "X"
        sex = "M" if sex_char == "M" else ("F" if sex_char == "F" else "X")
        formatted_dob = self._format_yymmdd_to_iso(dob_raw, is_birth=True)

        name_segment = line3.rstrip("<")
        full_name = name_segment.replace("<<", " ").replace("<", " ").strip()

        national_id = NationalIDData(
            id_number=doc_number,
            name=full_name.upper(),
            date_of_birth=formatted_dob,
            gender=sex,
        )

        return OCRResult(
            document_type="NATIONAL_ID",
            national_id=national_id,
            mrz_detected=True,
            mrz_lines=[line1, line2, line3],
            confidence=0.96,
            extracted_text=f"NATIONAL ID: {full_name} | {doc_number} | DOB: {formatted_dob} | SEX: {sex}",
        )

    def extract_from_raw_text(self, text: str, default_type: str = "PASSPORT") -> OCRResult:
        """
        Extracts fields from unstructured text transcript via specialized regex patterns.
        """
        # First attempt MRZ parse if MRZ pattern appears in text
        mrz_res = self.parse_mrz(text)
        if mrz_res:
            return mrz_res

        # Fallback to visual field regex extraction
        upper_text = text.upper()

        # Passport Number
        passport_num_match = re.search(r"\b([A-Z][0-9]{7,8}|[A-Z0-9]{8,9})\b", upper_text)
        passport_num = passport_num_match.group(1) if passport_num_match else "UNKNOWN_DOC"

        # Dates
        dates = re.findall(r"\b(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})\b", text)
        dob = dates[0] if len(dates) > 0 else "1990-01-01"
        expiry = dates[1] if len(dates) > 1 else "2030-01-01"

        # Gender
        gender_match = re.search(r"\b(GENDER|SEX)\s*[:/]?\s*([MFX])\b", upper_text)
        gender = gender_match.group(2) if gender_match else "M"

        # Nationality
        nat_match = re.search(r"\b(NATIONALITY|COUNTRY)\s*[:/]?\s*([A-Z]{3})\b", upper_text)
        nationality = nat_match.group(2) if nat_match else "IND"

        # Name
        name_match = re.search(r"\b(?:NAME|SURNAME|GIVEN NAMES?)\s*[:/]?\s*([A-Z\s]{4,30})", upper_text)
        name = name_match.group(1).strip() if name_match else "TRAVELER NAME"

        passport_data = PassportData(
            name=name,
            passport_number=passport_num,
            nationality=nationality,
            date_of_birth=dob,
            date_of_expiry=expiry,
            gender=gender if gender in ["M", "F", "X"] else "M",
        )

        return OCRResult(
            document_type=default_type,
            passport=passport_data,
            mrz_detected=False,
            mrz_lines=[],
            confidence=0.88,
            extracted_text=text[:300],
        )

    def _format_yymmdd_to_iso(self, yymmdd: str, is_birth: bool = True) -> str:
        """
        Converts 6-character YYMMDD to ISO 8601 YYYY-MM-DD.
        """
        if len(yymmdd) < 6 or not yymmdd[:6].isdigit():
            return "2000-01-01"
        yy = int(yymmdd[0:2])
        mm = yymmdd[2:4]
        dd = yymmdd[4:6]

        if is_birth:
            year = 1900 + yy if yy > 25 else 2000 + yy
        else:
            year = 2000 + yy

        return f"{year}-{mm}-{dd}"

