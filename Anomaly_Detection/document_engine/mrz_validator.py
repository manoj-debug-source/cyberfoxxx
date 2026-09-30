"""
ICAO 9303 Machine Readable Zone (MRZ) Checksum & Temporal Logical Validator.
Implements official 7-3-1 check digit algorithms for travel document integrity.
"""

from datetime import datetime, timezone
import re
from typing import List, Optional, Tuple

from document_engine.config import BORDER_WATCHLIST, ICAO_CHAR_VALUES, ICAO_WEIGHTS
from document_engine.schema import EvidenceItem, PassportData, VisaData, WatchlistHit


def calculate_icao_check_digit(data: str) -> int:
    """
    Computes standard ICAO 9303 check digit using weights 7, 3, 1 repeating modulo 10.
    """
    total = 0
    clean_data = data.upper()
    for i, char in enumerate(clean_data):
        val = ICAO_CHAR_VALUES.get(char, 0)
        weight = ICAO_WEIGHTS[i % 3]
        total += val * weight
    return total % 10


def verify_icao_check_digit(data: str, expected_check_digit: str) -> bool:
    """
    Verifies if a field's expected check digit matches the calculated 7-3-1 check digit.
    """
    try:
        expected = int(expected_check_digit)
        return calculate_icao_check_digit(data) == expected
    except ValueError:
        return False


def parse_date_yymmdd(date_str: str) -> Optional[datetime]:
    """
    Parses date in either YYYY-MM-DD or YYMMDD format.
    """
    clean = re.sub(r"[^\d]", "", date_str)
    if len(clean) == 8:
        try:
            return datetime.strptime(clean, "%Y%m%d")
        except ValueError:
            return None
    elif len(clean) == 6:
        try:
            return datetime.strptime(clean, "%y%m%d")
        except ValueError:
            return None
    return None


def format_to_yymmdd(date_str: str) -> str:
    """
    Formats date string to 6-digit YYMMDD string for MRZ comparison.
    """
    dt = parse_date_yymmdd(date_str)
    return dt.strftime("%y%m%d") if dt else "000000"


def generate_mrz_lines(passport: PassportData) -> Tuple[str, str]:
    """
    Generates standard ICAO 9303 Type 3 (Passport) two 44-character MRZ lines.
    """
    # Line 1: P<NATNAME<<SURNAME<<<<<<<<<<<<<<<<<<<<<<<<<<
    nat = (passport.nationality.upper() + "<<<")[:3]
    name_parts = passport.name.upper().split()
    surname = name_parts[-1] if len(name_parts) > 1 else name_parts[0]
    given_names = "<".join(name_parts[:-1]) if len(name_parts) > 1 else ""
    full_mrz_name = f"{surname}<<{given_names}"
    line1 = f"P<{nat}{full_mrz_name}"
    line1 = (line1 + "<" * 44)[:44]

    # Line 2: DocNumber(9) + CD(1) + Nat(3) + DOB(6) + CD(1) + Sex(1) + Expiry(6) + CD(1) + Optional(14) + CD(1) + CompositeCD(1)
    doc_num = (passport.passport_number.upper().replace(" ", "") + "<" * 9)[:9]
    doc_cd = str(calculate_icao_check_digit(doc_num))

    dob_str = format_to_yymmdd(passport.date_of_birth)
    dob_cd = str(calculate_icao_check_digit(dob_str))

    sex = passport.gender.upper() if passport.gender in ["M", "F", "X"] else "<"

    exp_str = format_to_yymmdd(passport.date_of_expiry)
    exp_cd = str(calculate_icao_check_digit(exp_str))

    optional = "<" * 14
    opt_cd = "<"

    # Composite check digit data string: doc_num+doc_cd + dob+dob_cd + exp+exp_cd + optional+opt_cd
    composite_data = f"{doc_num}{doc_cd}{dob_str}{dob_cd}{exp_str}{exp_cd}{optional}{'0' if opt_cd == '<' else opt_cd}"
    composite_cd = str(calculate_icao_check_digit(composite_data))

    line2 = f"{doc_num}{doc_cd}{nat}{dob_str}{dob_cd}{sex}{exp_str}{exp_cd}{optional}{opt_cd}{composite_cd}"
    line2 = (line2 + "<" * 44)[:44]

    return line1, line2


class DocumentValidator:
    """
    Comprehensive document integrity, MRZ checksum, temporal validation, and border watchlist engine.
    """

    def __init__(self):
        self.last_watchlist_hit: Optional[WatchlistHit] = None

    def validate(
        self,
        passport: Optional[PassportData] = None,
        visa: Optional[VisaData] = None,
    ) -> Tuple[bool, float, List[EvidenceItem], List[str]]:
        """
        Runs validation across MRZ checksums, dates, syntax, and border watchlists.
        Returns:
            - is_failed: bool
            - anomaly_score: float [0.0 - 1.0]
            - evidence: List[EvidenceItem]
            - fraud_types: List[str]
        """
        self.last_watchlist_hit = None
        evidence: List[EvidenceItem] = []
        fraud_types: List[str] = []
        total_score = 0.0

        if passport:
            p_failed, p_score, p_evidence, p_types = self._validate_passport(passport)
            total_score += p_score
            evidence.extend(p_evidence)
            fraud_types.extend(p_types)

        if visa:
            v_failed, v_score, v_evidence, v_types = self._validate_visa(visa, passport)
            total_score += v_score
            evidence.extend(v_evidence)
            fraud_types.extend(v_types)

        final_score = min(1.0, total_score)
        is_failed = len(evidence) > 0

        return is_failed, final_score, evidence, fraud_types

    def _validate_passport(
        self, p: PassportData
    ) -> Tuple[bool, float, List[EvidenceItem], List[str]]:
        evidence = []
        fraud_types = []
        score = 0.0

        # 1. Validate MRZ if provided
        if p.mrz_line2 and len(p.mrz_line2.strip()) >= 44:
            mrz = p.mrz_line2.strip()

            # Extract fields from MRZ Line 2
            mrz_doc_num = mrz[0:9]
            mrz_doc_cd = mrz[9]
            mrz_dob = mrz[13:19]
            mrz_dob_cd = mrz[19]
            mrz_exp = mrz[21:27]
            mrz_exp_cd = mrz[27]

            # Check Document Number Check Digit
            if not verify_icao_check_digit(mrz_doc_num, mrz_doc_cd):
                calc = calculate_icao_check_digit(mrz_doc_num)
                evidence.append(
                    EvidenceItem(
                        layer="DOCUMENT_VALIDATION",
                        anomaly="MRZ Passport Number Check Digit Mismatch",
                        detail=f"Document number checksum failed. (MRZ check digit: '{mrz_doc_cd}', calculated: '{calc}'). Indicates forged document number.",
                        severity="CRITICAL",
                    )
                )
                fraud_types.append("MRZ Passport Number Forgery")
                score += 0.40

            # Check Date of Birth Check Digit
            if not verify_icao_check_digit(mrz_dob, mrz_dob_cd):
                calc = calculate_icao_check_digit(mrz_dob)
                evidence.append(
                    EvidenceItem(
                        layer="DOCUMENT_VALIDATION",
                        anomaly="MRZ Date of Birth Check Digit Mismatch",
                        detail=f"Date of birth checksum failed. (MRZ check digit: '{mrz_dob_cd}', calculated: '{calc}'). Indicates tampered birth date.",
                        severity="CRITICAL",
                    )
                )
                fraud_types.append("Altered Date of Birth")
                score += 0.35

            # Check Expiry Date Check Digit
            if not verify_icao_check_digit(mrz_exp, mrz_exp_cd):
                calc = calculate_icao_check_digit(mrz_exp)
                evidence.append(
                    EvidenceItem(
                        layer="DOCUMENT_VALIDATION",
                        anomaly="MRZ Expiry Date Check Digit Mismatch",
                        detail=f"Expiry date checksum failed. (MRZ check digit: '{mrz_exp_cd}', calculated: '{calc}'). Indicates tampered expiry date.",
                        severity="CRITICAL",
                    )
                )
                fraud_types.append("Altered Expiry Date")
                score += 0.35

            # Cross-check Visual OCR fields with MRZ values
            vis_doc = p.passport_number.replace(" ", "").upper()
            clean_mrz_doc = mrz_doc_num.replace("<", "").upper()
            if clean_mrz_doc and not (vis_doc.startswith(clean_mrz_doc) or clean_mrz_doc.startswith(vis_doc)):
                evidence.append(
                    EvidenceItem(
                        layer="DOCUMENT_VALIDATION",
                        anomaly="Visual vs. MRZ Document Number Discrepancy",
                        detail=f"Visual passport number '{p.passport_number}' does not match MRZ document number '{clean_mrz_doc}'.",
                        severity="CRITICAL",
                    )
                )
                fraud_types.append("Document Discrepancy / Inconsistent Identity")
                score += 0.40

            # Cross-check Visual Expiry with MRZ Expiry
            vis_exp = format_to_yymmdd(p.date_of_expiry)
            if mrz_exp and vis_exp != mrz_exp:
                evidence.append(
                    EvidenceItem(
                        layer="DOCUMENT_VALIDATION",
                        anomaly="Visual vs. MRZ Expiry Date Discrepancy",
                        detail=f"Visual expiry date '{p.date_of_expiry}' (YYMMDD: '{vis_exp}') does not match MRZ expiry '{mrz_exp}'. Indicates visual alteration of document expiration date.",
                        severity="CRITICAL",
                    )
                )
                fraud_types.append("Altered Expiry Date")
                score += 0.40

            # Cross-check Visual DOB with MRZ DOB
            vis_dob = format_to_yymmdd(p.date_of_birth)
            if mrz_dob and vis_dob != mrz_dob:
                evidence.append(
                    EvidenceItem(
                        layer="DOCUMENT_VALIDATION",
                        anomaly="Visual vs. MRZ Date of Birth Discrepancy",
                        detail=f"Visual date of birth '{p.date_of_birth}' (YYMMDD: '{vis_dob}') does not match MRZ date of birth '{mrz_dob}'. Indicates visual alteration of birth date.",
                        severity="CRITICAL",
                    )
                )
                fraud_types.append("Altered Date of Birth")
                score += 0.40

        # 2. Temporal Validation
        now = datetime.now()
        dt_expiry = parse_date_yymmdd(p.date_of_expiry)
        dt_dob = parse_date_yymmdd(p.date_of_birth)

        if dt_expiry and dt_expiry < now:
            evidence.append(
                EvidenceItem(
                    layer="DOCUMENT_VALIDATION",
                    anomaly="Expired Travel Document",
                    detail=f"Passport expired on {dt_expiry.strftime('%Y-%m-%d')}. Document invalid for international border crossing.",
                    severity="HIGH",
                )
            )
            fraud_types.append("Expired Travel Document")
            score += 0.30

        if dt_dob:
            age = (now - dt_dob).days / 365.25
            if age < 0 or age > 120:
                evidence.append(
                    EvidenceItem(
                        layer="DOCUMENT_VALIDATION",
                        anomaly="Impossible Date of Birth",
                        detail=f"Calculated passenger age is {age:.1f} years (DOB: {p.date_of_birth}), which violates biological plausibility standards.",
                        severity="HIGH",
                    )
                )
                fraud_types.append("Illogical Identity Profile")
                score += 0.30

        # 4. Check Border Watchlist (SSB / Interpol)
        doc_clean = p.passport_number.replace(" ", "").upper()
        name_clean = p.name.strip().upper()
        for entry in BORDER_WATCHLIST:
            watch_doc = entry["passport_number"].replace(" ", "").upper()
            watch_name = entry["name"].strip().upper()
            if doc_clean == watch_doc or name_clean == watch_name:
                hit = WatchlistHit(
                    passport_number=p.passport_number,
                    name=p.name,
                    category=entry["category"],
                    reason=entry["reason"],
                    alert_level=entry["alert_level"],
                    issuing_agency=entry["issuing_agency"],
                )
                self.last_watchlist_hit = hit
                evidence.append(
                    EvidenceItem(
                        layer="WATCHLIST",
                        anomaly=f"Watchlist Hit: {entry['category']}",
                        detail=(
                            f"MATCH FOUND on Border Watchlist: Document '{p.passport_number}' / '{p.name}'. "
                            f"Issuing Agency: {entry['issuing_agency']}. Reason: {entry['reason']}."
                        ),
                        severity="CRITICAL",
                    )
                )
                fraud_types.append(f"SSB Watchlist Alert ({entry['category']})")
                score += 0.95
                break

        return len(evidence) > 0, score, evidence, fraud_types

    def _validate_visa(
        self, v: VisaData, p: Optional[PassportData] = None
    ) -> Tuple[bool, float, List[EvidenceItem], List[str]]:
        evidence = []
        fraud_types = []
        score = 0.0
        now = datetime.now()

        # Check visa expiry
        if v.expiry_date:
            dt_exp = parse_date_yymmdd(v.expiry_date)
            if dt_exp and dt_exp < now:
                evidence.append(
                    EvidenceItem(
                        layer="DOCUMENT_VALIDATION",
                        anomaly="Expired Visa Authorization",
                        detail=f"Visa authorization expired on {dt_exp.strftime('%Y-%m-%d')}.",
                        severity="HIGH",
                    )
                )
                fraud_types.append("Expired Visa")
                score += 0.30

        # Check stay duration consistency
        if v.entry_validation_date and v.expiry_date and v.stay_duration_days:
            dt_start = parse_date_yymmdd(v.entry_validation_date)
            dt_end = parse_date_yymmdd(v.expiry_date)
            if dt_start and dt_end:
                total_validity_days = (dt_end - dt_start).days
                if v.stay_duration_days > total_validity_days:
                    evidence.append(
                        EvidenceItem(
                            layer="DOCUMENT_VALIDATION",
                            anomaly="Stay Duration Exceeds Visa Validity",
                            detail=f"Requested stay duration ({v.stay_duration_days} days) exceeds total visa validity window ({total_validity_days} days).",
                            severity="MEDIUM",
                        )
                    )
                    fraud_types.append("Visa Validity Anomaly")
                    score += 0.25

        return len(evidence) > 0, score, evidence, fraud_types
