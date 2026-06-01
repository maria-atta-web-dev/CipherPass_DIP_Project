"""
================================================================================
SCORING ENGINE - Weighted Trust Score Calculation
Weighted Formula: Trust = (Face × 0.40) + (Document × 0.35) + (Signature × 0.25)
================================================================================
"""


def calculate_trust_score(face_conf, doc_conf, sig_sim):
    """
    Weighted trust score calculation
    Face: 40% (primary biometric)
    Document: 35% (identity proof)
    Signature: 25% (behavioral biometric)
    """
    weighted = (face_conf * 0.40) + (doc_conf * 0.35) + (sig_sim * 0.25)
    return round(weighted * 100)


def get_risk_level(trust_score):
    """Risk classification based on trust score"""
    if trust_score >= 70:
        return 'low', 'IDENTITY VERIFIED — SAFE TO PROCEED'
    elif trust_score >= 45:
        return 'medium', 'CAUTION — MANUAL REVIEW RECOMMENDED'
    else:
        return 'high', 'HIGH RISK — TRANSACTION BLOCKED'


def generate_flags(face_conf, doc_conf, sig_sim, face_count=1, liveness=1.0):
    """Generate specific fraud indicators"""
    flags = []
    
    if face_conf < 0.5:
        flags.append("❌ Face verification failed — Identity mismatch")
    elif face_conf < 0.7:
        flags.append("⚠️ Low face confidence — Review recommended")
    
    if face_count == 0:
        flags.append("❌ No face detected in image")
    elif face_count > 1:
        flags.append(f"⚠️ Multiple faces ({face_count}) detected")
    
    if liveness < 0.4:
        flags.append("❌ Liveness check failed — Possible photo attack")
    
    if doc_conf < 0.4:
        flags.append("❌ Document forgery detected")
    elif doc_conf < 0.6:
        flags.append("⚠️ Document tampering suspected")
    
    if sig_sim < 0.3:
        flags.append("❌ Signature mismatch — Identity inconsistency")
    elif sig_sim < 0.5:
        flags.append("⚠️ Low signature match — Verify manually")
    
    return flags


def get_full_recommendation(risk_level, flags):
    """Detailed recommendation based on risk assessment"""
    if risk_level == 'low':
        return ("✅ VERIFICATION CLEARED.\n\nAll checks passed. Proceed with transaction.")
    
    elif risk_level == 'medium':
        return ("⚠️ MANUAL REVIEW REQUIRED.\n\n"
                "Recommended actions:\n"
                "1. Request additional ID proof\n"
                "2. Perform video verification\n"
                "3. Cross-check with issuing authority\n"
                "4. Limit transaction amount until cleared")
    
    else:
        return ("🚨 IMMEDIATE ACTION REQUIRED.\n\n"
                "DO NOT PROCEED with transaction!\n\n"
                "Recommended actions:\n"
                "1. BLOCK transaction immediately\n"
                "2. Report to fraud department\n"
                "3. Flag subject in database\n"
                "4. File police report if financial loss occurred")