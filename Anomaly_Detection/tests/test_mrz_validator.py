"""
Unit tests for ICAO 9303 MRZ checksum calculation and temporal logic validation.
"""

from document_engine.mrz_validator import (
    calculate_icao_check_digit,
    generate_mrz_lines,
    verify_icao_check_digit,
    DocumentValidator,
)
from document_engine.schema import PassportData, VisaData


def test_icao_check_digit_calculation():
    # Official ICAO test vector: "L898902C<" -> check digit is 3
    assert calculate_icao_check_digit("L898902C<") == 3
    # "740812" -> check digit is 2
    assert calculate_icao_check_digit("740812") == 2
    # "120415" -> check digit is 9
    assert calculate_icao_check_digit("120415") == 9


def test_genuine_passport_mrz_passes():
    p = PassportData(
        name="ANANYA SHARMA",
        passport_number="Z8942105",
        nationality="IND",
        date_of_birth="1996-05-14",
        date_of_expiry="2032-05-13",
        gender="F",
    )
    l1, l2 = generate_mrz_lines(p)
    p.mrz_line1 = l1
    p.mrz_line2 = l2

    validator = DocumentValidator()
    is_failed, score, evidence, fraud_types = validator.validate(passport=p)

    assert is_failed is False
    assert score == 0.0
    assert len(evidence) == 0


def test_tampered_passport_number_mrz_fails():
    p = PassportData(
        name="ANANYA SHARMA",
        passport_number="Z8942105",
        nationality="IND",
        date_of_birth="1996-05-14",
        date_of_expiry="2032-05-13",
        gender="F",
    )
    l1, l2 = generate_mrz_lines(p)
    # Alter the first digit of the passport number in MRZ Line 2 without updating check digit
    tampered_l2 = "A" + l2[1:]
    p.mrz_line2 = tampered_l2

    validator = DocumentValidator()
    is_failed, score, evidence, fraud_types = validator.validate(passport=p)

    assert is_failed is True
    assert score > 0.30
    assert any("MRZ Passport Number Check Digit Mismatch" in e.anomaly for e in evidence)


def test_tampered_birth_date_mrz_fails():
    p = PassportData(
        name="ANANYA SHARMA",
        passport_number="Z8942105",
        nationality="IND",
        date_of_birth="1996-05-14",
        date_of_expiry="2032-05-13",
        gender="F",
    )
    l1, l2 = generate_mrz_lines(p)
    # Alter birth year in MRZ from 96 to 02 (chars 13-19) without updating check digit
    tampered_l2 = l2[:13] + "020514" + l2[19:]
    p.mrz_line2 = tampered_l2

    validator = DocumentValidator()
    is_failed, score, evidence, fraud_types = validator.validate(passport=p)

    assert is_failed is True
    assert any("MRZ Date of Birth Check Digit Mismatch" in e.anomaly for e in evidence)


def test_expired_travel_document():
    p = PassportData(
        name="JOHN DOE",
        passport_number="A1234567",
        nationality="USA",
        date_of_birth="1980-01-01",
        date_of_expiry="2018-01-01",  # Expired
        gender="M",
    )
    validator = DocumentValidator()
    is_failed, score, evidence, fraud_types = validator.validate(passport=p)

    assert is_failed is True
    assert any("Expired Travel Document" in e.anomaly for e in evidence)


def test_visa_stay_duration_anomaly():
    v = VisaData(
        visa_number="V100200",
        visa_type="TOURIST",
        entry_validation_date="2026-10-01",
        expiry_date="2026-10-15",  # 14-day validity window
        stay_duration_days=60,  # Requesting 60 days stay!
    )
    validator = DocumentValidator()
    is_failed, score, evidence, fraud_types = validator.validate(visa=v)

    assert is_failed is True
    assert any("Stay Duration Exceeds Visa Validity" in e.anomaly for e in evidence)
