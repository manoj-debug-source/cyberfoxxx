"""
Configuration settings, ICAO 9303 check digit parameters, and forensic thresholds.
"""

# ICAO 9303 Check Digit Weights (repeating 7, 3, 1)
ICAO_WEIGHTS = [7, 3, 1]

# ICAO Character Conversion Table (< is 0, 0-9 is 0-9, A-Z is 10-35)
ICAO_CHAR_VALUES = {
    "<": 0,
    **{str(i): i for i in range(10)},
    **{chr(ord("A") + i): 10 + i for i in range(26)},
}

# Image Forensics & ELA Settings
ELA_JPEG_QUALITY = 90
ELA_SCALE = 10
ELA_TAMPER_THRESHOLD = 0.28  # Mean normalized pixel difference threshold

# Noise Inconsistency Settings
NOISE_INCONSISTENCY_RATIO = 3.5  # Max acceptable ratio between photo and background noise variance

# Blacklisted editing software signatures in EXIF/Metadata
SUSPICIOUS_SOFTWARE = [
    "photoshop",
    "gimp",
    "canva",
    "paint.net",
    "pixlr",
    "snapseed",
    "lightroom",
    "affinity",
    "coreldraw",
    "facetune",
]

# Risk Score Weights for 4-Module Screening Engine
WEIGHT_FIELD_VALIDATION = 0.25      # Module 2: ICAO Checksums, Dates & Watchlist
WEIGHT_IMAGE_FORENSICS = 0.35       # Module 3: ELA, Noise Disparity, Stamp, Font
WEIGHT_FACE_VERIFICATION = 0.30     # Module 4: Live 1:1 Face Match & Anti-Spoofing
WEIGHT_OCR_CONFIDENCE = 0.10        # Module 1: OCR Field Consistency & Completeness

# Face Verification & Liveness Thresholds (Module 4)
FACE_SIMILARITY_THRESHOLD = 0.68     # Cosine similarity >= 0.68 is a confirmed match
FACE_IMPERSONATION_THRESHOLD = 0.50  # Cosine similarity < 0.50 is flagged as impersonation
ANTI_SPOOFING_TEXTURE_MIN = 45.0     # Minimum high-frequency Laplacian variance for genuine 3D human skin
ANTI_SPOOFING_TEXTURE_MAX = 850.0    # Above this indicates high-frequency moiré patterns / screen pixels

# Stamp Forensics Settings
STAMP_COLOR_RANGES = {
    "VIOLET": ((120, 40, 40), (160, 255, 255)),  # Border immigration violet stamps
    "BLUE": ((95, 50, 40), (125, 255, 255)),     # Entry blue circular stamps
    "RED": ((0, 60, 40), (15, 255, 255)),        # Departure red rectangular stamps
}
STAMP_MIN_CIRCULARITY = 0.52
STAMP_MIN_COVERAGE = 0.005  # Stamp must cover at least 0.5% of the visa area

# Simulated Sashastra Seema Bal (SSB) & Interpol Border Watchlist
BORDER_WATCHLIST = [
    {
        "passport_number": "M1983021",
        "name": "VIKRAM MALHOTRA",
        "category": "INTERPOL RED NOTICE",
        "reason": "Wanted for transnational cyber fraud & document counterfeit syndicates",
        "alert_level": "CRITICAL",
        "issuing_agency": "SSB Intelligence / Interpol Lyon",
    },
    {
        "passport_number": "K7721904",
        "name": "CARLOS SANTOS",
        "category": "LOST / STOLEN PASSPORT (SLTD)",
        "reason": "Reported stolen in Lisbon, Portugal in 2024",
        "alert_level": "CRITICAL",
        "issuing_agency": "Interpol SLTD Database",
    },
    {
        "passport_number": "P4482019",
        "name": "RAHUL DESHMUKH",
        "category": "NATIONAL SECURITY LOOKOUT",
        "reason": "Border Lookout Circular (LOC) - Active arrest warrant",
        "alert_level": "CRITICAL",
        "issuing_agency": "Ministry of Home Affairs",
    },
]

# Severity & Decision Thresholds
SEVERITY_THRESHOLDS = {
    "CRITICAL": 0.85,
    "HIGH": 0.70,
    "MEDIUM": 0.50,
    "LOW": 0.30,
}

DECISION_POLICIES = {
    "ALLOW": "CLEAR (ALLOW PASSENGER TRANSIT)",
    "VERIFY": "VERIFY PASSENGER (ROUTINE QUESTIONING)",
    "SECONDARY": "SECONDARY INSPECTION REQUIRED (SUPERVISOR ESCALATION)",
    "REJECT": "REJECT & DETAIN (CRITICAL FORGERY DETECTED)",
}
