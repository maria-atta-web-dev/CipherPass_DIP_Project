"""
CNIC Image Archive — permanent storage per customer for future fraud checks.
"""

import json
import re
import cv2
from pathlib import Path
from datetime import datetime
from customer_screening import normalize_cnic

ARCHIVE_DIR = Path("verification_data") / "cnic_archive"


def _folder(cnic: str) -> Path:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    safe = normalize_cnic(cnic).replace("-", "_")
    p = ARCHIVE_DIR / safe
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_cnic_archive(cnic: str, front_raw, front_enh, back_raw, back_enh, extracted: dict, face_img=None, doc_img=None) -> str:
    """Save front/back raw + enhanced + face/doc images + JSON metadata."""
    folder = _folder(cnic)
    paths = {}
    if front_raw is not None:
        p = folder / "front_raw.jpg"
        cv2.imwrite(str(p), front_raw)
        paths["front_raw"] = str(p)
    if front_enh is not None:
        p = folder / "front_enhanced.jpg"
        cv2.imwrite(str(p), front_enh)
        paths["front_enhanced"] = str(p)
    if back_raw is not None:
        p = folder / "back_raw.jpg"
        cv2.imwrite(str(p), back_raw)
        paths["back_raw"] = str(p)
    if back_enh is not None:
        p = folder / "back_enhanced.jpg"
        cv2.imwrite(str(p), back_enh)
        paths["back_enhanced"] = str(p)
    if face_img is not None:
        p = folder / "face.jpg"
        cv2.imwrite(str(p), face_img)
        paths["face"] = str(p)
    if doc_img is not None:
        p = folder / "doc.jpg"
        cv2.imwrite(str(p), doc_img)
        paths["doc"] = str(p)

    meta = {
        "cnic": normalize_cnic(cnic),
        "saved_at": datetime.now().isoformat(),
        "image_paths": paths,
        "extracted_data": {k: v for k, v in extracted.items() if k != "enhanced_image"},
        "verification_count": 1,
    }
    meta_file = folder / "archive.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            old = json.load(f)
        meta["verification_count"] = old.get("verification_count", 0) + 1
        meta["first_saved_at"] = old.get("first_saved_at", old.get("saved_at"))
    else:
        meta["first_saved_at"] = meta["saved_at"]

    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return str(folder)


def save_cnic_dip_image(cnic: str, step_name: str, image) -> str:
    """Save a selected DIP/filter image to the CNIC archive and update archive metadata."""
    folder = _folder(cnic)
    safe_name = re.sub(r"[^a-z0-9]+", "_", step_name.lower()).strip("_")
    if not safe_name:
        safe_name = "dip_step"
    p = folder / f"dip_{safe_name}.jpg"
    cv2.imwrite(str(p), image)

    meta_file = folder / "archive.json"
    meta = {
        "cnic": normalize_cnic(cnic),
        "saved_at": datetime.now().isoformat(),
        "image_paths": {},
        "dip_images": {},
    }
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {
                "cnic": normalize_cnic(cnic),
                "saved_at": datetime.now().isoformat(),
                "image_paths": {},
                "dip_images": {},
            }
    meta.setdefault("image_paths", {})
    meta.setdefault("dip_images", {})
    meta["image_paths"][f"dip_{safe_name}"] = str(p)
    meta["dip_images"][step_name] = str(p)
    meta["last_dip_saved"] = datetime.now().isoformat()
    meta["dip_saved_count"] = meta.get("dip_saved_count", 0) + 1

    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return str(p)


def load_cnic_archive(cnic: str) -> dict:
    """Load archive metadata and images if exist."""
    folder = _folder(cnic)
    meta_file = folder / "archive.json"
    if not meta_file.exists():
        return None
    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)
    images = {}
    for key, path in meta.get("image_paths", {}).items():
        if Path(path).exists():
            images[key] = cv2.imread(path)
    meta["images"] = images
    return meta


def has_archive(cnic: str) -> bool:
    return (_folder(cnic) / "archive.json").exists()
