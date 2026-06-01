"""
Enhanced Person Search & Criminal Record Lookup
================================================
Industry Use: Bank tellers use this to search customers before processing
Real-world: Before account opening, banks search by CNIC or name to find:
  - Previous banking records
  - Criminal history
  - Fraud attempts
  - Account status
"""

import json
import os
from datetime import datetime
from pathlib import Path
from customer_screening import normalize_cnic, load_json, find_citizen, find_criminal_record

DATABASE_FILE = "citizen_database.json"
CRIMINAL_RECORDS_FILE = "criminal_records.json"
HISTORY_FILE = Path("verification_data") / "history.json"


def search_by_cnic(cnic: str) -> dict:
    """
    Search customer and criminal record by CNIC.
    Returns full profile with all history.
    """
    cnic_norm = normalize_cnic(cnic)
    if not cnic_norm:
        return {"error": "Invalid CNIC format"}
    
    database = load_json(DATABASE_FILE)
    criminal_db = load_json(CRIMINAL_RECORDS_FILE)
    
    key, citizen = find_citizen(cnic_norm, database)
    criminal = find_criminal_record(cnic_norm, criminal_db)
    previous = get_verification_history(cnic_norm)
    
    return {
        "cnic": cnic_norm,
        "citizen": citizen,
        "criminal": criminal,
        "previous_attempts": previous,
        "search_result": "FOUND" if citizen or criminal else "NOT FOUND"
    }


def search_by_name(name: str) -> list:
    """
    Search all customers by name (partial match).
    Real-world: When customer forgets CNIC or name is illegible.
    """
    database = load_json(DATABASE_FILE)
    results = []
    name_lower = name.lower().strip()
    
    for key, citizen in database.items():
        citizen_name = citizen.get("name", "").lower()
        if name_lower in citizen_name or citizen_name.startswith(name_lower):
            results.append({
                "cnic": key,
                "name": citizen.get("name"),
                "father": citizen.get("father", "N/A"),
                "dob": citizen.get("dob", "N/A"),
                "trust_score": citizen.get("trust_score", 0),
                "verified": citizen.get("verified", False)
            })
    
    return results


def get_verification_history(cnic: str, limit: int = 50) -> list:
    """
    Get all previous verification attempts for this CNIC.
    Used to detect fraud: same person attempting multiple account openings.
    """
    cnic_norm = normalize_cnic(cnic)
    if not HISTORY_FILE.exists():
        return []
    
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except:
        return []
    
    sessions = history.get("sessions", [])
    matched = [
        s for s in sessions
        if normalize_cnic(s.get("cnic", "")) == cnic_norm
    ]
    matched.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return matched[:limit]


def display_criminal_record(criminal: dict) -> str:
    """
    Format criminal record for display in UI.
    Real-world: Compliance officer reads this to make rejection decision.
    """
    if not criminal or not criminal.get("has_criminal_record"):
        return "✓ NO CRIMINAL RECORD FOUND\n\nThis person is CLEAR in all watchlists."
    
    lines = []
    lines.append("⚠ CRIMINAL RECORD FOUND")
    lines.append("=" * 60)
    lines.append(f"Risk Level: {criminal.get('risk_level', 'UNKNOWN').upper()}")
    lines.append(f"Status: {criminal.get('status', 'Unknown')}")
    lines.append(f"Last Updated: {criminal.get('last_updated', 'N/A')}")
    lines.append(f"Source: {criminal.get('source', 'N/A')}")
    lines.append("")
    lines.append("CRIMES ON FILE:")
    lines.append("-" * 60)
    
    crimes = criminal.get("crimes", [])
    for i, crime in enumerate(crimes, 1):
        lines.append(f"\n{i}. {crime.get('type', 'Unknown').upper()}")
        lines.append(f"   Date: {crime.get('date', 'N/A')}")
        lines.append(f"   Status: {crime.get('status', 'unknown').upper()}")
        lines.append(f"   Description: {crime.get('description', 'N/A')}")
        if crime.get("penalty"):
            lines.append(f"   Penalty: {crime.get('penalty')}")
    
    if criminal.get("flags"):
        lines.append("\n" + "=" * 60)
        lines.append("FLAGS:")
        for flag in criminal.get("flags", []):
            lines.append(f"  🚩 {flag}")
    
    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def detect_fraud_attempts(cnic: str) -> dict:
    """
    Check for suspicious patterns indicating fraud.
    Real-world: FIA/bank fraud detection system.
    """
    cnic_norm = normalize_cnic(cnic)
    history = get_verification_history(cnic_norm)
    
    flags = []
    risk_score = 0
    
    if len(history) == 0:
        return {
            "is_suspicious": False,
            "fraud_risk": "LOW",
            "reason": "No previous attempts",
            "flags": [],
            "risk_score": 0
        }
    
    # Check 1: Multiple attempts in short time (account takeover)
    if len(history) >= 3:
        recent = [h for h in history if is_recent(h.get("timestamp", ""))]
        if len(recent) >= 3:
            flags.append("MULTIPLE_ATTEMPTS_IN_SHORT_TIME")
            risk_score += 35
    
    # Check 2: Different faces, same CNIC (identity theft)
    if len(history) >= 2:
        face_mismatch = sum(1 for h in history[:3] if not h.get("is_correct_person", False))
        if face_mismatch >= 2:
            flags.append("FACE_MISMATCH_DETECTED")
            risk_score += 40
    
    # Check 3: Rapid rejections (trying to bypass system)
    if len(history) >= 2:
        recent_rejects = [h for h in history[:5] if h.get("risk_level") in ["high", "reject"]]
        if len(recent_rejects) >= 2:
            flags.append("REPEATED_REJECTIONS")
            risk_score += 25
    
    # Check 4: Document tampering attempts
    doc_issues = sum(1 for h in history[:5] if h.get("doc_score", 100) < 60)
    if doc_issues >= 2:
        flags.append("DOCUMENT_QUALITY_ISSUES")
        risk_score += 20
    
    fraud_risk = "LOW"
    if risk_score >= 70:
        fraud_risk = "HIGH"
    elif risk_score >= 40:
        fraud_risk = "MEDIUM"
    
    return {
        "is_suspicious": fraud_risk in ["MEDIUM", "HIGH"],
        "fraud_risk": fraud_risk,
        "reason": f"{len(history)} previous attempts detected",
        "flags": flags,
        "risk_score": risk_score,
        "recent_attempts": len([h for h in history if is_recent(h.get("timestamp", ""))])
    }


def is_recent(timestamp_str: str, days: int = 30) -> bool:
    """Check if timestamp is within N days."""
    if not timestamp_str:
        return False
    try:
        attempt_date = datetime.strptime(timestamp_str[:10], "%Y-%m-%d")
        current_date = datetime.now().date()
        delta = (current_date - attempt_date.date()).days
        return delta <= days
    except:
        return False


def format_search_report(search_result: dict) -> str:
    """Format complete search report for display."""
    lines = []
    lines.append("=" * 70)
    lines.append("PERSON SEARCH & CRIMINAL RECORD REPORT")
    lines.append("=" * 70)
    
    cnic = search_result.get("cnic", "N/A")
    lines.append(f"\nCNIC: {cnic}")
    lines.append(f"Search Result: {search_result.get('search_result', 'UNKNOWN')}")
    
    # Citizen Info
    citizen = search_result.get("citizen")
    lines.append("\n--- BANK RECORDS ---")
    if citizen:
        lines.append(f"Name: {citizen.get('name', 'N/A')}")
        lines.append(f"Father: {citizen.get('father', 'N/A')}")
        lines.append(f"DOB: {citizen.get('dob', 'N/A')}")
        lines.append(f"Address: {citizen.get('address', 'N/A')}")
        lines.append(f"Phone: {citizen.get('phone', 'N/A')}")
        lines.append(f"Trust Score: {citizen.get('trust_score', 'N/A')}/100")
        lines.append(f"Verified: {citizen.get('verified', False)}")
        lines.append(f"Account Type: {citizen.get('account_type', 'N/A')}")
    else:
        lines.append("NOT FOUND IN BANK DATABASE — New applicant")
    
    # Criminal Record
    criminal = search_result.get("criminal")
    lines.append("\n--- CRIMINAL / AML RECORD ---")
    if criminal and criminal.get("has_criminal_record"):
        lines.append(display_criminal_record(criminal))
    else:
        lines.append("✓ CLEAR — No criminal or fraud record")
    
    # Previous Attempts
    previous = search_result.get("previous_attempts", [])
    lines.append(f"\n--- VERIFICATION HISTORY ({len(previous)} attempts) ---")
    if previous:
        for i, attempt in enumerate(previous[:10], 1):
            lines.append(
                f"\n  {i}. {attempt.get('timestamp', 'N/A')[:19]}"
            )
            lines.append(f"     Trust Score: {attempt.get('trust_score', '?')}/100")
            lines.append(f"     Risk Level: {attempt.get('risk_level', '?').upper()}")
            lines.append(f"     Face Match: {'✓' if attempt.get('is_correct_person') else '✗'}")
        if len(previous) > 10:
            lines.append(f"\n  ... and {len(previous) - 10} more attempts")
    else:
        lines.append("  No previous verification attempts")
    
    # Fraud Detection
    fraud_check = detect_fraud_attempts(cnic)
    lines.append("\n--- FRAUD DETECTION ---")
    lines.append(f"Fraud Risk: {fraud_check.get('fraud_risk')}")
    if fraud_check.get("is_suspicious"):
        lines.append("⚠ SUSPICIOUS ACTIVITY DETECTED")
        for flag in fraud_check.get("flags", []):
            lines.append(f"  🚩 {flag}")
    else:
        lines.append("✓ No suspicious patterns detected")
    
    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


# Export for UI integration
__all__ = [
    'search_by_cnic',
    'search_by_name',
    'get_verification_history',
    'display_criminal_record',
    'detect_fraud_attempts',
    'format_search_report'
]
