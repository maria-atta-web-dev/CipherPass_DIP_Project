"""
Pakistan Banking KYC helpers
============================
CNIC format (NADRA), SBP/AML context for demos and UI.
"""

import re

# Pakistan CNIC: 12345-1234567-1 (13 digits + dashes)
CNIC_PATTERN = re.compile(r"^\d{5}-\d{7}-\d$")


def validate_pakistan_cnic(cnic: str) -> tuple:
    """
    Returns (is_valid, message).
    """
    cnic = (cnic or "").strip()
    if not cnic:
        return False, "CNIC is required"
    if CNIC_PATTERN.match(cnic):
        return True, "Valid Pakistan CNIC format (NADRA)"
    digits = re.sub(r"\D", "", cnic)
    if len(digits) == 13:
        formatted = f"{digits[:5]}-{digits[5:12]}-{digits[12]}"
        return True, f"Use format: {formatted}"
    return False, "Invalid CNIC — use 12345-1234567-1 (5-7-1 digits)"


SBP_CONTEXT = (
    "State Bank of Pakistan (SBP) requires banks to perform Customer Due Diligence (CDD) "
    "and screen customers against fraud/AML lists before account opening (BPRD circulars)."
)

PAKISTAN_BANKS_USING_KYC = [
    "HBL — Habib Bank Limited",
    "UBL — United Bank Limited",
    "Meezan Bank — Islamic banking onboarding",
    "Bank Alfalah — digital account opening",
    "JazzCash / Easypaisa — mobile wallet KYC (CNIC + selfie)",
    "NADRA — national ID verification backbone",
]

FIA_CRIME_TYPES = [
    "Identity fraud (fake CNIC)",
    "Document forgery",
    "Cheque / signature fraud",
    "Money laundering",
    "Cyber financial fraud",
]
