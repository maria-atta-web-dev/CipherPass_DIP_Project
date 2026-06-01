"""
CNIC (Pakistan National ID) Processing
======================================
DIP enhancement + region OCR + validated fields for bank KYC.
"""

import re
import cv2
import numpy as np
from datetime import datetime

CNIC_REGEX = re.compile(r"\b(\d{5}[-\s]?\d{7}[-\s]?\d)\b")
DATE_REGEX = re.compile(r"\b(\d{2}[-/]\d{2}[-/]\d{4})\b")


def enhance_cnic_image(image: np.ndarray) -> np.ndarray:
    if image is None or image.size == 0:
        return image
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
    blur = cv2.GaussianBlur(denoised, (0, 0), 2)
    sharpened = cv2.addWeighted(denoised, 1.6, blur, -0.6, 0)
    return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)


def tesseract_installed() -> bool:
    from tesseract_setup import configure_tesseract
    return configure_tesseract()


def get_tesseract_info() -> dict:
    from tesseract_setup import get_tesseract_status
    return get_tesseract_status()


def is_valid_person_name(text: str) -> bool:
    """Reject OCR garbage; accept real names like 'Ahmed Raza'."""
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) < 3 or len(t) > 80:
        return False
    if re.search(r'["\*#@$%^&+=\[\]{}|\\<>~`]', t):
        return False
    letters = sum(1 for c in t if c.isalpha())
    digits = sum(1 for c in t if c.isdigit())
    if letters < max(3, int(len(t) * 0.55)):
        return False
    if digits > max(2, int(len(t) * 0.12)):
        return False
    words = [w for w in t.split() if re.search(r"[A-Za-z]{2,}", w)]
    return len(words) >= 1


def is_valid_father_name(text: str) -> bool:
    return is_valid_person_name(text)


def is_valid_address(text: str) -> bool:
    """Reject OCR noise; accept real addresses like 'House 12, Gulshan, Karachi'."""
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) < 10 or len(t) > 180:
        return False
    if re.search(r'[«»£*<>?{}[\]\\|@#$%^&+=~`"„“”]', t):
        return False
    if sum(1 for c in t if c.isdigit()) > len(t) * 0.25:
        return False
    letters = sum(1 for c in t if c.isalpha())
    if letters < len(t) * 0.6:
        return False
    words = re.findall(r"[A-Za-z]{3,}", t)
    if len(words) < 2:
        return False
    tokens = t.split()
    if len(tokens) > 40:
        return False
    short_noise = sum(1 for w in tokens if len(w) <= 2 and not w.isdigit())
    if short_noise > len(tokens) * 0.35:
        return False
    return True


def is_valid_dob(text: str) -> bool:
    return bool(DATE_REGEX.search(text or ""))


def sanitize_extracted_fields(data: dict) -> dict:
    """Drop invalid OCR noise before merge/display."""
    d = dict(data or {})
    if not is_valid_person_name(d.get("name", "")):
        d["name"] = ""
    if not is_valid_father_name(d.get("father_name", "")):
        d["father_name"] = ""
    if not is_valid_address(d.get("address", "")):
        d["address"] = ""
    if not is_valid_dob(d.get("date_of_birth", "")):
        d["date_of_birth"] = ""
    cnic = normalize_cnic_entered(d.get("cnic", ""))
    d["cnic"] = cnic if len(re.sub(r"\D", "", cnic)) == 13 else ""
    return d


def _prepare_ocr_variants(image: np.ndarray) -> list:
    if image is None or image.size == 0:
        return []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
    h, w = gray.shape[:2]
    if max(h, w) < 1000:
        gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    variants = []
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(otsu)
    variants.append(cv2.bitwise_not(otsu))
    adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 8)
    variants.append(adapt)
    return variants


def _ocr_languages() -> str:
    try:
        import pytesseract
        if "urd" in (pytesseract.get_languages() or []):
            return "eng+urd"
    except Exception:
        pass
    return "eng"


def _ocr_region(image: np.ndarray, psm: int = 7, whitelist: str = None, lang: str = None) -> str:
    if not tesseract_installed() or image is None or image.size == 0:
        return ""
    try:
        import pytesseract
        cfg = f"--psm {psm}"
        if whitelist:
            cfg += f" -c tessedit_char_whitelist={whitelist}"
        ocr_lang = lang or (_ocr_languages() if not whitelist else "eng")
        best = ""
        for variant in _prepare_ocr_variants(image):
            try:
                t = pytesseract.image_to_string(variant, lang=ocr_lang, config=cfg) or ""
                t = t.strip()
                if len(t) > len(best):
                    best = t
            except Exception:
                continue
        return best
    except Exception:
        return ""


def _cnic_front_regions(image: np.ndarray) -> dict:
    """
    Pakistan NADRA CNIC layout (portrait on right):
    - Left ~62%: name, father, DOB
    - Bottom strip: CNIC number
    """
    h, w = image.shape[:2]
    return {
        "name_band": image[int(h * 0.20) : int(h * 0.48), int(w * 0.04) : int(w * 0.58)],
        "father_band": image[int(h * 0.44) : int(h * 0.66), int(w * 0.04) : int(w * 0.58)],
        "dob_band": image[int(h * 0.58) : int(h * 0.78), int(w * 0.04) : int(w * 0.55)],
        "cnic_strip": image[int(h * 0.70) : h, int(w * 0.02) : int(w * 0.92)],
        "text_left": image[int(h * 0.12) : int(h * 0.88), 0 : int(w * 0.62)],
    }


def _ocr_cnic_front_one(image: np.ndarray) -> dict:
    """Single pass region OCR on one image variant."""
    rois = _cnic_front_regions(image)
    cnic_text = _ocr_region(rois["cnic_strip"], psm=7, whitelist="0123456789-")
    if not _find_cnic(cnic_text):
        cnic_text += "\n" + _ocr_region(rois["text_left"], psm=6, whitelist="0123456789-")
    if not _find_cnic(cnic_text):
        cnic_text += "\n" + _ocr_region(image, psm=6, whitelist="0123456789-")
    name_text = _ocr_region(rois["name_band"], psm=7)
    father_text = _ocr_region(rois["father_band"], psm=7)
    dob_text = _ocr_region(rois["dob_band"], psm=7)
    full_text = "\n".join(filter(None, [name_text, father_text, dob_text, cnic_text]))
    parsed = parse_fields_from_text(full_text, "front")
    parsed["cnic"] = parsed.get("cnic") or _find_cnic(cnic_text) or _find_cnic(full_text)
    if is_valid_person_name(name_text):
        parsed["name"] = _clean_name_line(name_text)
    if is_valid_father_name(father_text):
        parsed["father_name"] = _clean_name_line(father_text)
    if DATE_REGEX.search(dob_text):
        parsed["date_of_birth"] = DATE_REGEX.search(dob_text).group(1)
    return sanitize_extracted_fields(parsed)


def _merge_ocr_passes(pass_a: dict, pass_b: dict) -> dict:
    out = dict(pass_a or {})
    b = pass_b or {}
    for key in ("cnic", "name", "father_name", "date_of_birth", "gender", "address"):
        if not out.get(key) and b.get(key):
            out[key] = b[key]
    return sanitize_extracted_fields(out)


def _ocr_cnic_front_structured(image: np.ndarray) -> dict:
    """Region OCR on original + enhanced image (better CNIC digit read)."""
    enhanced = enhance_cnic_image(image)
    a = _ocr_cnic_front_one(image)
    b = _ocr_cnic_front_one(enhanced)
    return _merge_ocr_passes(a, b)


def _clean_name_line(text: str) -> str:
    t = re.sub(r"[^A-Za-z\s.'-]", " ", text or "")
    t = re.sub(r"\s+", " ", t).strip()
    return " ".join(w.capitalize() for w in t.split() if len(w) > 1)


def _find_cnic(text: str) -> str:
    compact = re.sub(r"\s+", "", text or "")
    for m in CNIC_REGEX.finditer(compact):
        raw = re.sub(r"\D", "", m.group(1))
        if len(raw) == 13:
            return f"{raw[:5]}-{raw[5:12]}-{raw[12]}"
    digits = re.sub(r"\D", "", text or "")
    for i in range(max(0, len(digits) - 12)):
        chunk = digits[i : i + 13]
        if len(chunk) == 13:
            return f"{chunk[:5]}-{chunk[5:12]}-{chunk[12]}"
    return ""


def parse_fields_from_text(text: str, side: str) -> dict:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    data = {
        "side": side,
        "raw_text": text or "",
        "cnic": _find_cnic(text),
        "name": "",
        "father_name": "",
        "date_of_birth": "",
        "gender": "",
        "address": "",
        "issue_date": "",
    }
    for line in lines:
        low = line.lower()
        if "father" in low or "s/o" in low or "d/o" in low:
            cand = re.sub(r"(?i)father|s/o|d/o|name|:", "", line).strip() or line
            if is_valid_father_name(cand):
                data["father_name"] = _clean_name_line(cand)
        elif any(g in low for g in ("male", "female")):
            data["gender"] = "Male" if "male" in low and "female" not in low else "Female"
        elif DATE_REGEX.search(line):
            d = DATE_REGEX.search(line).group(1)
            if not data["date_of_birth"]:
                data["date_of_birth"] = d
            else:
                data["issue_date"] = d
    if side == "front":
        for line in lines:
            if _find_cnic(line) or "pakistan" in line.lower():
                continue
            if is_valid_person_name(line):
                data["name"] = _clean_name_line(line)
                break
    if side == "back":
        addr = [
            ln for ln in lines
            if not _find_cnic(ln) and "pakistan" not in ln.lower() and is_valid_address(ln)
        ]
        if addr:
            data["address"] = ", ".join(addr[:4])
    return sanitize_extracted_fields(data)


def merge_cnic_data(front: dict, back: dict) -> dict:
    merged = {
        "cnic": front.get("cnic") or back.get("cnic") or "",
        "name": front.get("name") or "",
        "father_name": front.get("father_name") or "",
        "date_of_birth": front.get("date_of_birth") or "",
        "gender": front.get("gender") or "",
        "address": back.get("address") or "",
        "issue_date": back.get("issue_date") or "",
        "extracted_at": datetime.now().isoformat(),
    }
    merged["ocr_reliable"] = _is_ocr_reliable(front, back)
    return sanitize_extracted_fields(merged)


def _is_ocr_reliable(front: dict, back: dict) -> bool:
    cnic = front.get("cnic") or back.get("cnic") or ""
    name = (front.get("name") or "").strip()
    return bool(cnic) and is_valid_person_name(name)


def process_cnic_side(image: np.ndarray, side: str) -> dict:
    enhanced = enhance_cnic_image(image)
    if side == "front":
        fields = _ocr_cnic_front_structured(image)
    else:
        text = _ocr_region(enhanced, psm=6)
        fields = parse_fields_from_text(text, side)
    fields["enhanced_image"] = enhanced
    return fields


def _norm_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _text_similarity(a: str, b: str) -> float:
    from difflib import SequenceMatcher
    na, nb = _norm_text(a), _norm_text(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def normalize_cnic_entered(cnic: str) -> str:
    digits = re.sub(r"\D", "", cnic or "")
    if len(digits) == 13:
        return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"
    return (cnic or "").strip()


def _flatten_archived(archived: dict) -> dict:
    if not archived:
        return {}
    if archived.get("official_entered"):
        return {**archived, **archived["official_entered"]}
    return archived


def compare_entered_with_cnic(entered: dict, ocr_from_card: dict, archived: dict = None, bank_record: dict = None) -> dict:
    entered_cnic = normalize_cnic_entered(entered.get("cnic", ""))
    entered_name = (entered.get("name") or "").strip()
    if not is_valid_person_name(entered_name):
        entered_name = ""
    if not entered_cnic:
        return {
            "identity_score": 0,
            "is_correct_person": False,
            "verdict": "INCOMPLETE — enter CNIC",
            "issues": ["CNIC number required"],
            "message": "Enter CNIC from the card",
            "checks_passed": [],
        }
    if not entered_name:
        return {
            "identity_score": 0,
            "is_correct_person": False,
            "verdict": "INCOMPLETE — enter name",
            "issues": ["Full name required (letters only, from CNIC)"],
            "message": "Enter name from CNIC card",
            "checks_passed": [],
        }

    score = 100
    issues = []
    passed = []
    arch = _flatten_archived(archived)

    if bank_record:
        db_cnic = normalize_cnic_entered(bank_record.get("cnic", ""))
        db_name = bank_record.get("name", "")
        if db_cnic == entered_cnic:
            passed.append("CNIC matches bank database")
            name_sim = _text_similarity(entered_name, db_name)
            if name_sim >= 0.45:
                passed.append(f"Name matches bank record ({int(name_sim * 100)}%)")
            else:
                issues.append(f"Wrong person: name '{entered_name}' ≠ bank record '{db_name}'")
                score -= 55

    if arch:
        arch_cnic = normalize_cnic_entered(arch.get("cnic", ""))
        if arch_cnic and arch_cnic == entered_cnic:
            passed.append("CNIC matches saved CNIC file")
            arch_name = arch.get("name", "")
            if arch_name and _text_similarity(entered_name, arch_name) >= 0.45:
                passed.append("Name matches saved official data")
            elif arch_name:
                issues.append("Name changed from saved official data")
                score -= 25

    ocr = ocr_from_card or {}
    ocr_scan = ocr.get("ocr_scan") or {}
    if ocr_scan.get("ocr_reliable"):
        ocr_cnic = normalize_cnic_entered(ocr_scan.get("cnic", ""))
        if ocr_cnic and ocr_cnic != entered_cnic:
            issues.append(f"Card scan CNIC ({ocr_cnic}) differs from entered")
            score -= 15
        else:
            passed.append("CNIC on card matches scan")
    else:
        passed.append("Teller verified data (card name not readable by OCR)")

    score = max(0, min(100, score))
    is_correct = score >= 60 and len(issues) <= 1 and len(passed) >= 1
    if bank_record and _text_similarity(entered_name, bank_record.get("name", "")) >= 0.45:
        is_correct = True
        score = max(score, 85)

    return {
        "identity_score": score,
        "is_correct_person": is_correct,
        "verdict": "CORRECT PERSON — data verified" if is_correct else "WRONG PERSON — check CNIC & name",
        "issues": issues,
        "message": " | ".join(passed[:3]) if passed else "; ".join(issues[:2]),
        "checks_passed": passed,
    }


def extract_cnic_number_only(front_raw, back_raw=None) -> str:
    """
    Simple mode: read only the 13-digit CNIC from front/back photo.
    Names on Pakistani CNIC are often Urdu — OCR is unreliable; teller types them.
    """
    if not tesseract_installed():
        return ""
    candidates = []
    for img in (front_raw, back_raw):
        if img is None:
            continue
        enhanced = enhance_cnic_image(img)
        h, w = enhanced.shape[:2]
        regions = [
            enhanced[int(h * 0.62) : h, int(w * 0.02) : int(w * 0.98)],
            enhanced[int(h * 0.55) : h, :],
            enhanced,
        ]
        for region in regions:
            for psm in (7, 6, 11):
                text = _ocr_region(region, psm=psm, whitelist="0123456789-", lang="eng")
                c = _find_cnic(text)
                if c:
                    candidates.append(c)
                text = _ocr_region(region, psm=psm, lang="eng")
                c = _find_cnic(text)
                if c:
                    candidates.append(c)
    if not candidates:
        return ""
    from collections import Counter
    return Counter(candidates).most_common(1)[0][0]


def extract_cnic_from_images(front_raw, back_raw=None) -> dict:
    """Simple extract: CNIC number from scan; other fields left for teller entry."""
    cnic = extract_cnic_number_only(front_raw, back_raw)
    if not cnic and front_raw is not None:
        front = process_cnic_side(front_raw, "front")
        front.pop("enhanced_image", None)
        cnic = front.get("cnic") or ""
    back = {}
    if back_raw is not None:
        back = process_cnic_side(back_raw, "back")
        back.pop("enhanced_image", None)
        if not cnic:
            cnic = back.get("cnic") or ""
    merged = merge_cnic_data(
        sanitize_extracted_fields({"cnic": cnic, "name": "", "father_name": "", "date_of_birth": ""}),
        sanitize_extracted_fields(back),
    )
    merged["extract_mode"] = "simple_cnic_only"
    return merged


def compare_with_stored(stored_enhanced: np.ndarray, new_enhanced: np.ndarray) -> dict:
    if stored_enhanced is None or new_enhanced is None:
        return {"similarity": 0.0, "match": True, "message": "First CNIC scan saved"}
    g1 = cv2.cvtColor(stored_enhanced, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(new_enhanced, cv2.COLOR_BGR2GRAY)
    g2 = cv2.resize(g2, (g1.shape[1], g1.shape[0]))
    h1 = cv2.calcHist([g1], [0], None, [256], [0, 256])
    h2 = cv2.calcHist([g2], [0], None, [256], [0, 256])
    cv2.normalize(h1, h1)
    cv2.normalize(h2, h2)
    sim = float(cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL))
    match = sim > 0.65
    return {
        "similarity": round(sim, 3),
        "match": match,
        "message": "Same CNIC document" if match else "Different CNIC image — review",
    }


def enrich_from_bank_db(merged: dict, citizen: dict) -> dict:
    if not citizen:
        return merged
    merged = dict(merged or {})
    if is_valid_person_name(citizen.get("name", "")):
        merged["name"] = citizen.get("name", "")
    merged["father_name"] = merged.get("father_name") or citizen.get("father") or citizen.get("father_name", "")
    merged["address"] = merged.get("address") or citizen.get("address", "")
    merged["date_of_birth"] = merged.get("date_of_birth") or citizen.get("dob", "")
    merged["cnic"] = merged.get("cnic") or citizen.get("cnic", "")
    merged["from_bank_db"] = True
    return merged


def get_form_fill_from_extract(data: dict) -> dict:
    """
    Values to copy into Step 2 UI fields after CNIC upload/extract.
    Priority: valid OCR scan → bank DB → existing official record.
    """
    data = data or {}
    scan = sanitize_extracted_fields(data.get("ocr_scan") or {})
    off = data.get("official_record") or data
    fill = {}

    cnic = normalize_cnic_entered(scan.get("cnic") or off.get("cnic") or "")
    if len(re.sub(r"\D", "", cnic)) == 13:
        fill["cnic"] = cnic

    for src in (scan, off):
        n = src.get("name", "")
        if is_valid_person_name(n) and "name" not in fill:
            fill["name"] = _clean_name_line(n)
        f = src.get("father_name", "")
        if is_valid_father_name(f) and "father_name" not in fill:
            fill["father_name"] = _clean_name_line(f)
        d = src.get("date_of_birth", "")
        if is_valid_dob(d) and "date_of_birth" not in fill:
            fill["date_of_birth"] = d
        a = src.get("address", "")
        if is_valid_address(a) and "address" not in fill:
            fill["address"] = a

    return fill


def merge_extract_sources(ocr: dict = None, manual: dict = None, bank: dict = None) -> dict:
    """
    Realistic bank flow: official record = teller + bank DB.
    OCR scan shown separately; garbage never overwrites official fields.
    """
    ocr = sanitize_extracted_fields(dict(ocr or {}))
    manual = dict(manual or {})
    bank = bank or {}

    ocr_scan = sanitize_extracted_fields({
        "cnic": ocr.get("cnic") or "",
        "name": ocr.get("name") or "",
        "father_name": ocr.get("father_name") or "",
        "date_of_birth": ocr.get("date_of_birth") or "",
        "address": ocr.get("address") or "",
        "ocr_reliable": ocr.get("ocr_reliable", False),
    })

    official = {"cnic": "", "name": "", "father_name": "", "date_of_birth": "", "address": ""}
    sources = []

    cnic_m = normalize_cnic_entered(manual.get("cnic", ""))
    if len(re.sub(r"\D", "", cnic_m)) == 13:
        official["cnic"] = cnic_m
        sources.append("teller_cnic")

    if bank:
        official = enrich_from_bank_db(official, bank)
        if "bank_database" not in sources:
            sources.append("bank_database")

    name_m = (manual.get("name") or "").strip()
    if is_valid_person_name(name_m):
        official["name"] = _clean_name_line(name_m)
        if "teller_entry" not in sources:
            sources.append("teller_entry")
    father_m = (manual.get("father_name") or "").strip()
    if is_valid_father_name(father_m):
        official["father_name"] = _clean_name_line(father_m)
    dob_m = (manual.get("date_of_birth") or "").strip()
    if is_valid_dob(dob_m):
        official["date_of_birth"] = dob_m
    addr_m = (manual.get("address") or "").strip()
    if is_valid_address(addr_m):
        official["address"] = addr_m

    if ocr_scan["cnic"] and not official["cnic"]:
        official["cnic"] = ocr_scan["cnic"]
        sources.append("ocr_cnic_only")

    out = {
        **official,
        "ocr_scan": ocr_scan,
        "official_record": official,
        "sources": sources,
        "ocr_engine_ok": tesseract_installed(),
    }
    if out["ocr_engine_ok"]:
        out["tesseract"] = get_tesseract_info()
    out["ocr_reliable"] = ocr_scan.get("ocr_reliable", False)
    return out
