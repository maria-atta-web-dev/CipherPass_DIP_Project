"""
Bank KYC / AML Customer Screening
=================================
Industry use: When someone opens a bank account or applies for a loan,
banks must verify identity (KYC) and check watchlists / criminal & fraud
history (AML) before approval.

This module looks up a person by CNIC and returns:
  - Registered customer data (citizen_database.json)
  - Criminal / fraud records (criminal_records.json)
  - Previous verification sessions (verification_data/history.json)
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

DATABASE_FILE = "citizen_database.json"
CRIMINAL_RECORDS_FILE = "criminal_records.json"
HISTORY_FILE = Path("verification_data") / "history.json"


def normalize_cnic(cnic: str) -> str:
    """Normalize CNIC for lookup (digits and dashes only)."""
    if not cnic:
        return ""
    return re.sub(r"\s+", "", cnic.strip())


def load_json(path: str) -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def find_citizen(cnic: str, database: dict) -> tuple:
    """Find citizen by exact or normalized CNIC."""
    cnic = normalize_cnic(cnic)
    if cnic in database:
        return cnic, database[cnic]
    for key, data in database.items():
        if normalize_cnic(key) == normalize_cnic(cnic):
            return key, data
        stored = data.get("cnic", "")
        if stored and normalize_cnic(stored) == normalize_cnic(cnic):
            return key, data
    return None, None


def find_criminal_record(cnic: str, records: dict) -> dict:
    cnic = normalize_cnic(cnic)
    if cnic in records:
        return records[cnic]
    for key, data in records.items():
        if normalize_cnic(key) == cnic:
            return data
    return None


def get_previous_verifications(cnic: str, limit: int = 20) -> list:
    """Past KYC checks for this CNIC from verification history."""
    cnic_norm = normalize_cnic(cnic)
    if not HISTORY_FILE.exists():
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        history = json.load(f)
    sessions = history.get("sessions", [])
    matched = [
        s for s in sessions
        if normalize_cnic(s.get("cnic", "")) == cnic_norm
    ]
    matched.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return matched[:limit]


def save_verification_history(cnic: str, session: dict) -> str:
    """Append one verification session to verification_data/history.json."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    history = {"sessions": []}
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = {"sessions": []}
    sessions = history.get("sessions", [])
    sessions.append(session)
    history["sessions"] = sessions[-500:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)
    return str(HISTORY_FILE)


def screening_decision(citizen: dict, criminal: dict, previous_count: int) -> dict:
    """
    Bank-style approve / review / reject recommendation.
    """
    if criminal and criminal.get("has_criminal_record"):
        risk = criminal.get("risk_level", "high")
        if risk == "high":
            return {
                "status": "REJECT",
                "color": "#ff0000",
                "message": "Account opening BLOCKED — high-risk criminal/fraud history.",
                "reason": "AML policy: convicted fraud or money laundering on file.",
            }
        return {
            "status": "MANUAL REVIEW",
            "color": "#ffaa00",
            "message": "Sent to compliance officer — medium-risk record found.",
            "reason": "Previous financial crime; requires branch manager approval.",
        }

    if not citizen:
        return {
            "status": "MANUAL REVIEW",
            "color": "#ffaa00",
            "message": "New customer — not in bank database. Full KYC required.",
            "reason": "CNIC not registered; complete identity verification.",
        }

    trust = citizen.get("trust_score", 0)
    if trust < 50:
        return {
            "status": "REJECT",
            "color": "#ff0000",
            "message": "Low trust score — application rejected.",
            "reason": f"Internal trust score {trust}/100 below bank threshold.",
        }

    if previous_count >= 3:
        recent_high = False  # caller can pass flags later
        if recent_high:
            pass
        return {
            "status": "MANUAL REVIEW",
            "color": "#ffaa00",
            "message": f"Repeat screening ({previous_count} past checks) — review activity.",
            "reason": "Multiple prior verifications; possible account takeover attempt.",
        }

    return {
        "status": "APPROVE",
        "color": "#00ff00",
        "message": "Eligible for account opening — clean AML/KYC screening.",
        "reason": "No criminal record; customer verified in bank database.",
    }


def get_customer_profile(cnic: str) -> dict:
    """
    Full customer screening report for one CNIC.
    Used by UI before or during account-opening verification.
    """
    cnic_norm = normalize_cnic(cnic)
    database = load_json(DATABASE_FILE)
    criminal_db = load_json(CRIMINAL_RECORDS_FILE)

    key, citizen = find_citizen(cnic_norm, database)
    criminal = find_criminal_record(cnic_norm, criminal_db)
    previous = get_previous_verifications(cnic_norm)
    decision = screening_decision(citizen, criminal, len(previous))

    return {
        "cnic": cnic_norm,
        "found_in_database": citizen is not None,
        "citizen": citizen,
        "citizen_key": key,
        "criminal_record": criminal or {
            "has_criminal_record": False,
            "crimes": [],
            "risk_level": "low",
            "no_data": criminal is None,
        },
        "previous_verifications": previous,
        "previous_count": len(previous),
        "decision": decision,
        "screened_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def format_profile_text(profile: dict) -> str:
    """Plain-text report for dialogs and logs."""
    lines = [
        "=" * 50,
        "BANK KYC / AML CUSTOMER SCREENING REPORT",
        "=" * 50,
        f"CNIC: {profile['cnic']}",
        f"Screened at: {profile['screened_at']}",
        "",
        "--- CUSTOMER DATABASE ---",
    ]

    if profile["found_in_database"]:
        c = profile["citizen"]
        father = c.get("father") or c.get("father_name", "N/A")
        lines.extend([
            f"Name: {c.get('name', 'N/A')}",
            f"Father: {father}",
            f"Address: {c.get('address', 'N/A')}",
            f"Phone: {c.get('phone', 'N/A')}",
            f"Trust Score: {c.get('trust_score', 'N/A')}/100",
            f"Registered: {c.get('registered_date', 'N/A')}",
        ])
    else:
        lines.append("NOT FOUND — New applicant (not in bank records)")

    lines.append("")
    lines.append("--- CRIMINAL / FRAUD RECORD (AML) ---")
    cr = profile["criminal_record"]
    if cr.get("has_criminal_record"):
        lines.append(f"STATUS: CRIMINAL RECORD FOUND — Risk: {cr.get('risk_level', '').upper()}")
        for i, crime in enumerate(cr.get("crimes", []), 1):
            lines.append(f"  {i}. {crime.get('type')} ({crime.get('date')})")
            lines.append(f"     {crime.get('description', '')}")
            lines.append(f"     Status: {crime.get('status', 'unknown')}")
    elif cr.get("no_data"):
        lines.append("No AML watchlist entry for this CNIC (clear in demo DB)")
    else:
        lines.append("CLEAR — No criminal or fraud record on file")

    lines.append("")
    lines.append(f"--- PREVIOUS VERIFICATIONS ({profile['previous_count']}) ---")
    if profile["previous_verifications"]:
        for s in profile["previous_verifications"][:5]:
            lines.append(
                f"  • {s.get('timestamp', '')[:19]} | "
                f"Score: {s.get('trust_score')}/100 | Risk: {s.get('risk_level')}"
            )
        if profile["previous_count"] > 5:
            lines.append(f"  ... and {profile['previous_count'] - 5} more")
    else:
        lines.append("  No previous KYC checks in this system")

    d = profile["decision"]
    lines.extend([
        "",
        "--- BANK DECISION ---",
        f"Recommendation: {d['status']}",
        f"{d['message']}",
        f"Reason: {d['reason']}",
        "=" * 50,
    ])
    return "\n".join(lines)
