"""
CipherPass — Encrypted Identity Clearance & Intelligence Platform
=================================================================
Biometric identity verification, criminal intelligence, and AML compliance.
"""

import os
import re
import sys
import json
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QGroupBox, QMessageBox,
    QFileDialog, QDialog, QProgressBar, QFrame, QSizePolicy, QScrollArea,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QFont

from face_module import run_face_verification
from document_module import analyze_document
from scoring import calculate_trust_score, get_risk_level, generate_flags
from utils import log_message, numpy_to_pixmap
from customer_screening import get_customer_profile, normalize_cnic, save_verification_history
from pakistan_kyc import validate_pakistan_cnic
from dip_showcase_dialog import DipShowcaseDialog
from cnic_processor import enhance_cnic_image, normalize_cnic_entered, is_valid_person_name
from cnic_archive import save_cnic_archive, save_cnic_dip_image
from ui_styles import (
    APP_STYLESHEET, HEADER_STYLE, BTN_PRIMARY, BTN_DANGER,
    BTN_SUCCESS, BTN_WARNING, BTN_VERIFY
)
from pdf_export import generate_pdf_report

DATABASE_FILE = "citizen_database.json"
APP_NAME = "CipherPass"
APP_TAGLINE = "Encrypted Identity  ·  Criminal Intelligence  ·  AML Screening  ·  Fraud Prevention"


def load_database():
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "42101-1234567-1": {
            "name": "Ahmed Raza", "father": "Muhammad Raza", "cnic": "42101-1234567-1",
            "address": "Karachi", "dob": "15/08/1990", "trust_score": 98,
        },
        "12345-6789012-3": {
            "name": "Hassan Ali", "father": "Muhammad Ali",
            "cnic": "12345-6789012-3", "address": "Karachi", "dob": "01/01/1985", "trust_score": 25,
        },
    }


OFFICIAL_DATABASE = load_database()


def bank_record_for_cnic(cnic):
    key = normalize_cnic(cnic)
    if not key:
        return None
    for k, v in OFFICIAL_DATABASE.items():
        if normalize_cnic(k) == key:
            return v
    return None


class FaceDetector:
    @staticmethod
    def detect(img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
        out = img.copy()
        for (x, y, w, h) in faces:
            cv2.rectangle(out, (x, y), (x + w, y + h), (0, 255, 0), 2)
        return out, len(faces)


class WebcamThread(QThread):
    change_pixmap = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self._run = True
        self.cap = None

    def run(self):
        self.cap = cv2.VideoCapture(0)
        while self._run and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                out, _ = FaceDetector.detect(frame)
                self.change_pixmap.emit(out)
            self.msleep(33)

    def stop(self):
        self._run = False
        if self.cap:
            self.cap.release()
        self.wait()


class WebcamDialog(QDialog):
    frame_captured = pyqtSignal(np.ndarray)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Live Face Capture")
        self.resize(700, 520)
        self.setStyleSheet("""
            QDialog { background-color: #0f1728; }
            QLabel { color: #e2e8f0; font-size: 13px; }
            QPushButton {
                background-color: #1e3a5f; color: white; border-radius: 8px;
                padding: 10px 20px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #2563a8; }
        """)
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        info = QLabel("Position your face in the frame.  Green box = face detected.")
        info.setStyleSheet("color:#38b2ac; font-size:13px; padding:6px;")
        lay.addWidget(info)
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 400)
        self.video_label.setStyleSheet("background:#0a1628; border-radius:8px;")
        lay.addWidget(self.video_label)
        row = QHBoxLayout()
        cap_btn = QPushButton("📸  Capture Photo")
        cap_btn.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #276749,stop:1 #38a169);
            color:white; font-weight:bold; border-radius:8px; padding:11px 24px; font-size:14px;
        """)
        cap_btn.clicked.connect(self._capture)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        row.addWidget(cap_btn)
        row.addWidget(close_btn)
        lay.addLayout(row)
        self.thread = WebcamThread()
        self.thread.change_pixmap.connect(self._update)
        self.thread.start()
        self.current_frame = None

    def _update(self, frame):
        self.current_frame = frame.copy()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        self.video_label.setPixmap(
            QPixmap.fromImage(QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)).scaled(
                self.video_label.size(), Qt.KeepAspectRatio
            )
        )

    def _capture(self):
        if self.current_frame is not None:
            self.frame_captured.emit(self.current_frame.copy())
            self.accept()

    def closeEvent(self, event):
        try:
            self.thread.stop()
        except Exception:
            pass
        event.accept()


class ComplianceReviewDialog(QDialog):
    """Compliance officer reviews a flagged customer and records a decision."""

    def __init__(self, parent=None, customer_name="", criminal_record=None, trust_score=0):
        super().__init__(parent)
        self.setWindowTitle("⚠  Compliance Review — Flagged Customer")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        self.result_data = {}
        self.setStyleSheet("""
            QDialog { background-color: #0f1728; }
            QLabel  { color: #e2e8f0; font-size: 13px; }
            QLineEdit {
                background-color: #1a2235; border: 1px solid #2d4a6e;
                border-radius: 8px; padding: 9px 13px;
                color: #e2e8f0; font-size: 13px;
            }
            QLineEdit:focus { border: 2px solid #38b2ac; }
            QTextEdit {
                background-color: #0d1421; border: 1px solid #2d4a6e;
                border-radius: 8px; color: #e2e8f0; font-size: 13px;
                padding: 8px;
            }
            QComboBox {
                background-color: #1a2235; border: 1px solid #2d4a6e;
                border-radius: 8px; padding: 8px 12px;
                color: #e2e8f0; font-size: 13px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a2235; color: #e2e8f0;
                selection-background-color: #2563a8;
            }
            QPushButton {
                background-color: #1e3a5f; color: white; border-radius: 8px;
                padding: 10px 18px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2563a8; }
        """)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        # --- Header banner ---
        banner = QFrame()
        banner.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #3d0000, stop:1 #5c1a1a);
            border-radius: 10px; border: 1px solid #c53030;
            padding: 12px;
        """)
        bl = QVBoxLayout(banner)
        bl.setSpacing(4)
        title_lbl = QLabel("⚠  FLAGGED CUSTOMER — COMPLIANCE REVIEW REQUIRED")
        title_lbl.setStyleSheet("color:#ff6b6b; font-size:15px; font-weight:bold;")
        sub_lbl = QLabel(
            f"Customer: <b>{customer_name}</b>   |   "
            f"Trust Score: <b>{trust_score}/100</b>"
        )
        sub_lbl.setStyleSheet("color:#fca5a5; font-size:13px;")
        sub_lbl.setTextFormat(Qt.RichText)
        bl.addWidget(title_lbl)
        bl.addWidget(sub_lbl)
        lay.addWidget(banner)

        # --- Criminal record details ---
        cr_lbl = QLabel("Criminal Record on File:")
        cr_lbl.setStyleSheet("color:#f6ad55; font-weight:bold; font-size:13px; margin-top:6px;")
        lay.addWidget(cr_lbl)

        cr_box = QFrame()
        cr_box.setStyleSheet("""
            background-color: #1a0a00;
            border: 1px solid #c05621;
            border-radius: 10px;
            padding: 12px;
        """)
        cr_lay = QVBoxLayout(cr_box)
        cr_lay.setSpacing(6)

        if criminal_record and criminal_record.get("has_criminal_record"):
            cr = criminal_record
            risk_color = "#ff4d4f" if cr.get("risk_level") == "high" else "#f6ad55"
            meta_lbl = QLabel(
                f"<b style='color:{risk_color};'>Risk Level: {cr.get('risk_level','').upper()}</b>"
                f"&nbsp;&nbsp;&nbsp;Status: <span style='color:#fca5a5;'>{cr.get('status','')}</span>"
                f"&nbsp;&nbsp;&nbsp;Last Updated: {cr.get('last_updated','N/A')}"
            )
            meta_lbl.setTextFormat(Qt.RichText)
            meta_lbl.setStyleSheet("color:#e2e8f0; font-size:13px;")
            cr_lay.addWidget(meta_lbl)

            for i, crime in enumerate(cr.get("crimes", []), 1):
                status_color = "#ff4d4f" if crime.get("status") == "convicted" else "#f6ad55"
                crime_frame = QFrame()
                crime_frame.setStyleSheet("""
                    background-color: #200e00;
                    border: 1px solid #7b341e;
                    border-radius: 8px;
                    padding: 10px;
                """)
                cf_lay = QVBoxLayout(crime_frame)
                cf_lay.setSpacing(3)
                c_title = QLabel(
                    f"<b style='color:#fc8181;'>#{i}  {crime.get('type','Unknown')}</b>"
                    f"  <span style='color:#a0aec0;'>({crime.get('date','N/A')})</span>"
                )
                c_title.setTextFormat(Qt.RichText)
                cf_lay.addWidget(c_title)
                c_desc = QLabel(crime.get("description", ""))
                c_desc.setWordWrap(True)
                c_desc.setStyleSheet("color:#e2d4c0; font-size:12px;")
                cf_lay.addWidget(c_desc)
                c_stat = QLabel(
                    f"Status: <b style='color:{status_color};'>{crime.get('status','').upper()}</b>"
                    f"  |  Penalty: <span style='color:#fca5a5;'>{crime.get('penalty','N/A')}</span>"
                )
                c_stat.setTextFormat(Qt.RichText)
                c_stat.setStyleSheet("font-size:12px;")
                cf_lay.addWidget(c_stat)
                crime_frame.setLayout(cf_lay)
                cr_lay.addWidget(crime_frame)
        else:
            no_cr = QLabel("No detailed criminal record data available.")
            no_cr.setStyleSheet("color:#a0aec0; font-size:13px;")
            cr_lay.addWidget(no_cr)

        cr_box.setLayout(cr_lay)
        lay.addWidget(cr_box)

        # --- Decision section ---
        dec_lbl = QLabel("Compliance Officer Decision:")
        dec_lbl.setStyleSheet("color:#63b3ed; font-weight:bold; font-size:13px; margin-top:8px;")
        lay.addWidget(dec_lbl)

        action_lay = QHBoxLayout()
        act_label = QLabel("Action:")
        act_label.setStyleSheet("color:#e2e8f0; min-width:90px;")
        action_lay.addWidget(act_label)
        from PyQt5.QtWidgets import QComboBox
        self.action_combo = QComboBox()
        self.action_combo.addItems([
            "REJECT — Block account opening",
            "ESCALATE — Send to branch manager",
            "INVESTIGATE — Request more documents",
            "REPORT_FIA — Report to Federal Investigation Agency",
            "HOLD — Pending further review",
        ])
        action_lay.addWidget(self.action_combo)
        lay.addLayout(action_lay)

        name_lay = QHBoxLayout()
        name_label = QLabel("Officer Name:")
        name_label.setStyleSheet("color:#e2e8f0; min-width:90px;")
        name_lay.addWidget(name_label)
        self.officer_name = QLineEdit()
        self.officer_name.setPlaceholderText("Enter officer's full name")
        name_lay.addWidget(self.officer_name)
        lay.addLayout(name_lay)

        notes_lbl = QLabel("Review Notes:")
        notes_lbl.setStyleSheet("color:#e2e8f0; font-size:13px;")
        lay.addWidget(notes_lbl)
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Enter compliance review comments, observations, or additional findings...")
        self.notes.setMinimumHeight(90)
        lay.addWidget(self.notes)

        btn_lay = QHBoxLayout()
        save_btn = QPushButton("📋  Submit Compliance Report")
        save_btn.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #c53030, stop:1 #e53e3e);
            color: white; font-weight: bold; font-size: 14px;
            border-radius: 8px; padding: 11px 22px;
        """)
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            background-color: #1a2235; color: #a0aec0;
            border: 1px solid #2d4a6e; border-radius: 8px; padding: 11px 18px;
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_lay.addWidget(save_btn)
        btn_lay.addWidget(cancel_btn)
        lay.addLayout(btn_lay)

    def _save(self):
        if not self.officer_name.text().strip():
            QMessageBox.warning(self, "Required", "Please enter the officer's name.")
            return
        action = self.action_combo.currentText()
        self.result_data = {
            "action": action.split(" — ")[0],
            "action_full": action,
            "officer_name": self.officer_name.text().strip(),
            "notes": self.notes.toPlainText().strip(),
            "timestamp": datetime.now().isoformat(),
        }
        self.accept()


class CnicDataDialog(QDialog):
    """Enter data from the physical identity card."""

    def __init__(self, parent=None, cnic=""):
        super().__init__(parent)
        self.setWindowTitle("Enter Identity Card Data")
        self.setMinimumWidth(440)
        self.result_data = {}
        self.setStyleSheet("""
            QDialog { background-color: #0f1728; }
            QLabel  { color: #e2e8f0; font-size: 13px; }
            QLineEdit {
                background-color: #1a2235; border: 1px solid #2d4a6e;
                border-radius: 8px; padding: 10px 14px;
                color: #e2e8f0; font-size: 13px;
            }
            QLineEdit:focus { border: 2px solid #38b2ac; }
            QPushButton {
                background-color: #1e3a5f; color: white; border-radius: 8px;
                padding: 11px 20px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #2563a8; }
        """)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Enter details from the identity card:")
        title.setStyleSheet("color:#38b2ac; font-weight:bold; font-size:14px; margin-bottom:6px;")
        lay.addWidget(title)

        self.cnic = QLineEdit(normalize_cnic_entered(cnic) if cnic else "")
        self.cnic.setPlaceholderText("CNIC Number  (e.g. 12345-1234567-1)")
        self.name = QLineEdit()
        self.name.setPlaceholderText("Full Name")
        self.father = QLineEdit()
        self.father.setPlaceholderText("Father's Name")
        self.dob = QLineEdit()
        self.dob.setPlaceholderText("Date of Birth  (DD/MM/YYYY)")
        self.address = QLineEdit()
        self.address.setPlaceholderText("Address (from back of card)")

        for label, w in [
            ("CNIC Number", self.cnic),
            ("Full Name", self.name),
            ("Father's Name", self.father),
            ("Date of Birth", self.dob),
            ("Address", self.address),
        ]:
            lbl = QLabel(label)
            lbl.setStyleSheet("color:#a0aec0; font-size:12px; margin-top:4px;")
            lay.addWidget(lbl)
            lay.addWidget(w)

        ok = QPushButton("✔  Confirm Data")
        ok.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #276749,stop:1 #38a169);
            color:white; font-weight:bold; border-radius:8px; padding:11px;
            font-size:13px; margin-top:8px;
        """)
        ok.clicked.connect(self._ok)
        lay.addWidget(ok)

    def _ok(self):
        cnic = normalize_cnic_entered(self.cnic.text().strip())
        name = self.name.text().strip()
        if len(re.sub(r"\D", "", cnic)) != 13:
            QMessageBox.warning(self, "Invalid CNIC", "Please enter a valid 13-digit CNIC (e.g. 12345-1234567-1).")
            return
        if not is_valid_person_name(name):
            QMessageBox.warning(self, "Invalid Name", "Please enter a valid full name (letters only).")
            return
        self.result_data = {
            "cnic": cnic,
            "name": name,
            "father_name": self.father.text().strip(),
            "date_of_birth": self.dob.text().strip(),
            "address": self.address.text().strip(),
        }
        self.accept()


class VerificationWorker(QThread):
    progress = pyqtSignal(int)
    result = pyqtSignal(dict)
    step = pyqtSignal(str)

    def __init__(self, cnic, face_img, doc_img, manual_data):
        super().__init__()
        self.cnic = cnic
        self.face_img = face_img
        self.doc_img = doc_img
        self.manual_data = manual_data or {}

    def run(self):
        results = {}
        self.step.emit("Identity input received — starting verification pipeline...")
        self.progress.emit(15)

        self.step.emit("Biometric processing: grayscale conversion, edge detection, face analysis...")
        face_score, liveness = 0.0, 0.0
        if self.face_img is not None:
            gray = cv2.cvtColor(self.face_img, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            cv2.Canny(blur, 50, 150)
            fr = run_face_verification(self.face_img)
            face_score = fr.get("confidence", 0.8)
            liveness = fr.get("liveness_score", 0.75)
            _, n = FaceDetector.detect(self.face_img)
            self.step.emit(f"  Faces detected: {n}  |  Biometric score: {int(face_score * 100)}%  |  Liveness: {int(liveness * 100)}%")
        else:
            self.step.emit("  No face image provided.")
        self.progress.emit(40)

        self.step.emit("Document verification: authenticity analysis in progress...")
        doc_score = 0.0
        if self.doc_img is not None:
            doc = analyze_document(self.doc_img)
            doc_score = doc.get("authenticity_score", 0.85)
            self.step.emit(f"  Document authenticity score: {int(doc_score * 100)}%")
        self.progress.emit(55)

        self.step.emit("Criminal & AML database screening...")
        profile = get_customer_profile(self.cnic)
        results["criminal_record"] = profile["criminal_record"]
        results["profile"] = profile
        if profile["found_in_database"]:
            self.step.emit(f"  Customer on record: {profile['citizen'].get('name', '')}")
        else:
            self.step.emit("  New customer — not in existing records.")
        if profile["criminal_record"].get("has_criminal_record"):
            self.step.emit("  ⚠  CRIMINAL RECORD FOUND — flagging for compliance review")
        else:
            self.step.emit("  ✔  Criminal record: CLEAR")
        self.progress.emit(70)

        self.step.emit("Calculating trust score and risk assessment...")
        trust = calculate_trust_score(face_score, doc_score, 0.75)
        if profile["criminal_record"].get("has_criminal_record"):
            trust = max(0, trust - 40)
        if profile["decision"]["status"] == "REJECT":
            trust = max(0, trust - 25)
        bank = bank_record_for_cnic(self.cnic)
        entered_name = self.manual_data.get("name", "")
        is_correct = True
        if bank and entered_name:
            from difflib import SequenceMatcher
            sim = SequenceMatcher(
                None, entered_name.lower(), bank.get("name", "").lower()
            ).ratio()
            is_correct = sim >= 0.45
            if not is_correct:
                trust = max(0, trust - 35)
                self.step.emit("  Name does not match existing bank record — score penalty applied.")
            else:
                self.step.emit("  Name matches bank record.")
        results["trust_score"] = trust
        results["face_score"] = int(face_score * 100)
        results["doc_score"] = int(doc_score * 100)
        results["sig_score"] = 0
        results["is_correct_person"] = is_correct
        results["is_verified"] = profile["found_in_database"]
        results["risk_level"], results["risk_message"] = get_risk_level(trust)
        results["flags"] = generate_flags(face_score, doc_score, 0.75)
        risk_color_tag = "HIGH" if trust < 40 else ("MEDIUM" if trust < 70 else "LOW")
        self.step.emit(f"  Trust Score: {trust}/100  |  Risk: {risk_color_tag}")
        self.progress.emit(100)
        self.result.emit(results)


class KYCApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — {APP_TAGLINE}")
        self.setGeometry(60, 60, 1380, 900)
        self.face_img = None
        self.cnic_front_raw = None
        self.cnic_back_raw = None
        self.cnic_front_enh = None
        self.doc_img = None
        self.last_results = None
        self.last_manual = None
        self.last_compliance = None
        self._build_ui()
        self._update_dashboard()

    def _load_dashboard_stats(self):
        """Read verification history files and compute today's live stats."""
        today = datetime.now().strftime("%Y-%m-%d")
        total = flagged = cleared = high_risk = compliance_actions = 0
        hist_dir = Path("verification_data")
        if hist_dir.exists():
            for f in hist_dir.glob("*.json"):
                if f.name == "compliance_decisions.json":
                    try:
                        data = json.loads(f.read_text(encoding="utf-8"))
                        for d in data.get("decisions", []):
                            if d.get("timestamp", "").startswith(today):
                                compliance_actions += 1
                    except Exception:
                        pass
                    continue
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    for session in data.get("sessions", []):
                        if session.get("timestamp", "").startswith(today):
                            total += 1
                            cr = session.get("criminal_record", {})
                            if cr.get("has_criminal_record"):
                                flagged += 1
                            trust = session.get("trust_score", 0) or 0
                            if trust >= 70:
                                cleared += 1
                            if session.get("risk_level", "") == "high":
                                high_risk += 1
                except Exception:
                    pass
        rate = int((cleared / total * 100)) if total > 0 else 0
        return {
            "total": total,
            "flagged": flagged,
            "cleared": cleared,
            "high_risk": high_risk,
            "clearance_rate": rate,
            "compliance_actions": compliance_actions,
        }

    def _update_dashboard(self):
        """Refresh all stat counter labels from live data."""
        s = self._load_dashboard_stats()
        self.stat_total.setText(str(s["total"]))
        self.stat_cleared.setText(str(s["cleared"]))
        self.stat_flagged.setText(str(s["flagged"]))
        self.stat_highrisk.setText(str(s["high_risk"]))
        self.stat_rate.setText(f"{s['clearance_rate']}%")
        self.stat_actions.setText(str(s["compliance_actions"]))

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(10)
        root.setContentsMargins(12, 12, 12, 12)

        # ── Header ──
        header = QFrame()
        header.setStyleSheet(HEADER_STYLE)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 8, 10, 8)

        left_hdr = QVBoxLayout()
        name_row = QHBoxLayout()
        lock_lbl = QLabel("🔐")
        lock_lbl.setStyleSheet("font-size:36px; padding-right:4px;")
        cipher_lbl = QLabel("Cipher")
        cipher_lbl.setStyleSheet(
            "color:#e2e8f0; font-size:32px; font-weight:bold; letter-spacing:1px;"
        )
        pass_lbl = QLabel("Pass")
        pass_lbl.setStyleSheet(
            "color:#805ad5; font-size:32px; font-weight:900; letter-spacing:3px;"
        )
        name_row.addWidget(lock_lbl)
        name_row.addWidget(cipher_lbl)
        name_row.addWidget(pass_lbl)
        name_row.addStretch()
        left_hdr.addLayout(name_row)
        app_tag_lbl = QLabel(APP_TAGLINE)
        app_tag_lbl.setStyleSheet(
            "color:#718096; font-size:11px; letter-spacing:1px; padding-left:52px;"
        )
        left_hdr.addWidget(app_tag_lbl)
        hl.addLayout(left_hdr)
        hl.addStretch()

        right_hdr = QVBoxLayout()
        right_hdr.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # version tag
        ver_lbl = QLabel("v2.0  ENTERPRISE EDITION")
        ver_lbl.setStyleSheet(
            "color:#b794f4; font-size:9px; letter-spacing:2px; font-weight:bold;"
            " padding-bottom:4px;"
        )
        ver_lbl.setAlignment(Qt.AlignRight)
        right_hdr.addWidget(ver_lbl)

        badges = [
            ("🔐  Encrypted Biometrics",  "#1a0d2e", "#b794f4"),
            ("🕵  Criminal Intelligence", "#1c3a26", "#68d391"),
            ("⚖  AML / FIA Shield",      "#2d1b4e", "#d6bcfa"),
        ]
        badge_row = QHBoxLayout()
        badge_row.setSpacing(6)
        for text, bg, fg in badges:
            b = QLabel(text)
            b.setStyleSheet(
                f"background-color:{bg}; color:{fg}; border-radius:12px;"
                f" padding:5px 14px; font-size:11px; font-weight:bold;"
            )
            badge_row.addWidget(b)
        right_hdr.addLayout(badge_row)
        hl.addLayout(right_hdr)
        root.addWidget(header)

        # ── Live Dashboard Stats Bar ──
        dash = QFrame()
        dash.setStyleSheet(
            "background-color:#111827; border:1px solid #1e3a5f;"
            " border-radius:10px; padding:2px;"
        )
        dash_lay = QHBoxLayout(dash)
        dash_lay.setSpacing(0)
        dash_lay.setContentsMargins(8, 6, 8, 6)

        stat_defs = [
            ("📊", "Today's Verifications", "0",  "#63b3ed", "stat_total"),
            ("✅", "Cleared",               "0",  "#48bb78", "stat_cleared"),
            ("⚠",  "Flagged Cases",         "0",  "#fc8181", "stat_flagged"),
            ("🔴", "High Risk",             "0",  "#f6ad55", "stat_highrisk"),
            ("📈", "Clearance Rate",        "0%", "#38b2ac", "stat_rate"),
            ("📋", "Compliance Actions",    "0",  "#b794f4", "stat_actions"),
        ]
        for i, (icon, label, val, color, attr) in enumerate(stat_defs):
            if i > 0:
                sep = QFrame()
                sep.setFrameShape(QFrame.VLine)
                sep.setStyleSheet("color:#1e3a5f; background:#1e3a5f; max-width:1px;")
                dash_lay.addWidget(sep)
            card = QWidget()
            cl = QVBoxLayout(card)
            cl.setSpacing(1)
            cl.setContentsMargins(14, 4, 14, 4)
            icon_lbl = QLabel(f"{icon}  {label}")
            icon_lbl.setStyleSheet("color:#4a5568; font-size:10px; font-weight:bold;")
            count_lbl = QLabel(val)
            count_lbl.setStyleSheet(f"color:{color}; font-size:20px; font-weight:900;")
            count_lbl.setAlignment(Qt.AlignCenter)
            cl.addWidget(icon_lbl)
            cl.addWidget(count_lbl)
            setattr(self, attr, count_lbl)
            dash_lay.addWidget(card)

        refresh_btn = QPushButton("↻")
        refresh_btn.setToolTip("Refresh stats")
        refresh_btn.setFixedSize(32, 32)
        refresh_btn.setStyleSheet(
            "background:#1e3a5f; color:#38b2ac; border-radius:6px;"
            " font-size:16px; font-weight:bold;"
        )
        refresh_btn.clicked.connect(self._update_dashboard)
        dash_lay.addStretch()
        dash_lay.addWidget(refresh_btn)
        root.addWidget(dash)

        # ── Main content row ──
        row = QHBoxLayout()
        row.setSpacing(10)

        # ── LEFT PANEL ──
        left = QScrollArea()
        left.setWidgetResizable(True)
        left.setMinimumWidth(440)
        left_w = QWidget()
        left_lay = QVBoxLayout(left_w)
        left_lay.setSpacing(10)

        # Step 1 — Upload ID Card
        g1 = QGroupBox("Step 1 — Upload Identity Card (CNIC)")
        g1l = QVBoxLayout(g1)
        r = QHBoxLayout()
        b1 = QPushButton("📄  Upload Front Side")
        b1.clicked.connect(self._upload_front)
        b2 = QPushButton("📄  Upload Back Side")
        b2.clicked.connect(self._upload_back)
        r.addWidget(b1)
        r.addWidget(b2)
        g1l.addLayout(r)
        self.prev_front = QLabel("Front")
        self.prev_back = QLabel("Back")
        for p in (self.prev_front, self.prev_back):
            p.setMinimumSize(130, 95)
            p.setAlignment(Qt.AlignCenter)
            p.setStyleSheet(
                "background:#0d1421; border:1px dashed #2d4a6e;"
                " border-radius:8px; color:#4a5568; font-size:12px;"
            )
        pr = QHBoxLayout()
        pr.addWidget(self.prev_front)
        pr.addWidget(self.prev_back)
        g1l.addLayout(pr)
        dip_b = QPushButton("🔬  Show Image Processing Steps")
        dip_b.clicked.connect(self._show_dip)
        g1l.addWidget(dip_b)
        left_lay.addWidget(g1)

        # Step 2 — Customer Data
        g2 = QGroupBox("Step 2 — Customer Information")
        g2l = QVBoxLayout(g2)
        self.cnic_in = self._field(g2l, "CNIC Number", "42101-1234567-1")
        self.name_in = self._field(g2l, "Full Name", "Enter full name")
        self.father_in = self._field(g2l, "Father's Name", "Enter father's name")
        self.dob_in = self._field(g2l, "Date of Birth", "DD/MM/YYYY")
        self.addr_in = self._field(g2l, "Address", "Enter address")

        btn_row1 = QHBoxLayout()
        enter_b = QPushButton("✏  Enter from Card")
        enter_b.setStyleSheet(BTN_SUCCESS)
        enter_b.clicked.connect(self._enter_cnic_dialog)
        load_b = QPushButton("🗃  Load Demo Record")
        load_b.setStyleSheet(BTN_WARNING)
        load_b.clicked.connect(self._load_bank)
        btn_row1.addWidget(enter_b)
        btn_row1.addWidget(load_b)
        g2l.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        lookup_b = QPushButton("🔎  Lookup Customer Profile")
        lookup_b.setStyleSheet(BTN_PRIMARY)
        lookup_b.clicked.connect(self._lookup_profile)
        save_b = QPushButton("💾  Save Customer Data")
        save_b.clicked.connect(self._save)
        btn_row2.addWidget(lookup_b)
        btn_row2.addWidget(save_b)
        g2l.addLayout(btn_row2)

        self.hint = QLabel(
            "Demo CNICs:  42101-1234567-1 (clean record)  |  12345-6789012-3 (flagged)"
        )
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet(
            "color:#4a8fa8; font-size:11px; padding:6px 0; font-style:italic;"
        )
        g2l.addWidget(self.hint)
        left_lay.addWidget(g2)

        # Step 3 — Face Capture
        g3 = QGroupBox("Step 3 — Biometric Face Capture")
        g3l = QVBoxLayout(g3)
        fb = QPushButton("📷  Open Camera")
        fb.clicked.connect(self._capture_face)
        g3l.addWidget(fb)
        self.face_prev = QLabel("No face captured")
        self.face_prev.setMinimumSize(160, 160)
        self.face_prev.setAlignment(Qt.AlignCenter)
        self.face_prev.setStyleSheet(
            "background:#0d1421; border:1px dashed #2d4a6e;"
            " border-radius:10px; color:#4a5568; font-size:12px;"
        )
        g3l.addWidget(self.face_prev)
        left_lay.addWidget(g3)

        self.verify_b = QPushButton("🔐   START VERIFICATION")
        self.verify_b.setStyleSheet(BTN_VERIFY)
        self.verify_b.clicked.connect(self._verify)
        left_lay.addWidget(self.verify_b)
        left_lay.addStretch()
        left.setWidget(left_w)
        row.addWidget(left, 1)

        # ── RIGHT PANEL ──
        right = QScrollArea()
        right.setWidgetResizable(True)
        rw = QWidget()
        rl = QVBoxLayout(rw)
        rl.setSpacing(10)

        # Score card
        score_card = QFrame()
        score_card.setStyleSheet(
            "background-color:#111827; border:1px solid #1e3a5f;"
            " border-radius:12px; padding:16px;"
        )
        sc_lay = QVBoxLayout(score_card)
        score_title = QLabel("Trust Score")
        score_title.setStyleSheet("color:#90cdf4; font-size:13px; font-weight:bold;")
        self.score_lbl = QLabel("—")
        self.score_lbl.setStyleSheet("font-size:52px; font-weight:bold; color:#48bb78;")
        self.risk_lbl = QLabel("Awaiting verification...")
        self.risk_lbl.setStyleSheet("color:#a0aec0; font-size:13px;")
        sc_lay.addWidget(score_title)
        sc_lay.addWidget(self.score_lbl)
        sc_lay.addWidget(self.risk_lbl)
        rl.addWidget(score_card)

        # Status cards row
        status_row = QHBoxLayout()

        person_card = QFrame()
        person_card.setStyleSheet(
            "background-color:#111827; border:1px solid #1e3a5f;"
            " border-radius:10px; padding:12px;"
        )
        pc_lay = QVBoxLayout(person_card)
        person_title = QLabel("Identity Match")
        person_title.setStyleSheet("color:#90cdf4; font-size:11px; font-weight:bold;")
        self.person_lbl = QLabel("—")
        self.person_lbl.setStyleSheet("color:#a0aec0; font-size:13px; font-weight:bold;")
        pc_lay.addWidget(person_title)
        pc_lay.addWidget(self.person_lbl)

        crim_card = QFrame()
        crim_card.setStyleSheet(
            "background-color:#111827; border:1px solid #1e3a5f;"
            " border-radius:10px; padding:12px;"
        )
        cc_lay = QVBoxLayout(crim_card)
        crim_title = QLabel("Criminal Record")
        crim_title.setStyleSheet("color:#90cdf4; font-size:11px; font-weight:bold;")
        self.crim_lbl = QLabel("—")
        self.crim_lbl.setStyleSheet("color:#a0aec0; font-size:13px; font-weight:bold;")
        cc_lay.addWidget(crim_title)
        cc_lay.addWidget(self.crim_lbl)

        dup_card = QFrame()
        dup_card.setStyleSheet(
            "background-color:#111827; border:1px solid #1e3a5f;"
            " border-radius:10px; padding:12px;"
        )
        dc_lay = QVBoxLayout(dup_card)
        dup_title = QLabel("Previous Verifications")
        dup_title.setStyleSheet("color:#90cdf4; font-size:11px; font-weight:bold;")
        self.prev_verif_lbl = QLabel("—")
        self.prev_verif_lbl.setStyleSheet("color:#a0aec0; font-size:13px; font-weight:bold;")
        dc_lay.addWidget(dup_title)
        dc_lay.addWidget(self.prev_verif_lbl)

        status_row.addWidget(person_card)
        status_row.addWidget(crim_card)
        status_row.addWidget(dup_card)
        rl.addLayout(status_row)

        # Export PDF button (hidden until verification done)
        self.export_btn = QPushButton("📄  Export PDF Compliance Report")
        self.export_btn.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #553c9a, stop:1 #6b46c1);
            color:white; font-weight:bold; font-size:13px;
            border-radius:8px; padding:11px; border:1px solid #7c3aed;
        """)
        self.export_btn.clicked.connect(self._export_pdf)
        self.export_btn.setVisible(False)
        rl.addWidget(self.export_btn)

        self.dip_btn = QPushButton("🔬  DIP Showcase — View Image Processing Steps")
        self.dip_btn.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #1a4b6e, stop:1 #2b6cb0);
            color:white; font-weight:bold; font-size:13px;
            border-radius:8px; padding:11px; border:1px solid #3182ce;
        """)
        self.dip_btn.clicked.connect(self._show_dip_showcase)
        self.dip_btn.setVisible(False)
        rl.addWidget(self.dip_btn)

        # Recent Verifications
        recent_title_row = QHBoxLayout()
        recent_title = QLabel("Recent Verifications")
        recent_title.setStyleSheet(
            "color:#90cdf4; font-size:13px; font-weight:bold; padding-top:6px;"
        )
        recent_title_row.addWidget(recent_title)
        recent_title_row.addStretch()
        rl.addLayout(recent_title_row)

        self.recent_list = QTextEdit()
        self.recent_list.setReadOnly(True)
        self.recent_list.setMaximumHeight(160)
        self.recent_list.setStyleSheet(
            "background-color:#0d1421; border:1px solid #1e3a5f;"
            " border-radius:8px; color:#e2e8f0; font-size:12px; padding:6px;"
        )
        rl.addWidget(self.recent_list)
        self._refresh_recent_verifications()

        # Activity log
        log_title = QLabel("Activity Log")
        log_title.setStyleSheet(
            "color:#90cdf4; font-size:13px; font-weight:bold; padding-top:6px;"
        )
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(200)
        rl.addWidget(log_title)
        rl.addWidget(self.log)
        right.setWidget(rw)
        row.addWidget(right, 1)
        root.addLayout(row)

        self.prog = QProgressBar()
        self.prog.setVisible(False)
        self.prog.setMaximumHeight(18)
        root.addWidget(self.prog)
        self.setStyleSheet(APP_STYLESHEET)

    def _field(self, layout, label, ph):
        lbl = QLabel(label)
        lbl.setStyleSheet("color:#a0aec0; font-size:12px; margin-top:4px;")
        layout.addWidget(lbl)
        w = QLineEdit()
        w.setPlaceholderText(ph)
        layout.addWidget(w)
        return w

    def _read_img(self, path):
        img = cv2.imread(path)
        if img is None:
            img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        try:
            from PIL import Image, ExifTags
            pil = Image.open(path)
            exif = pil._getexif()
            orientation = None
            if exif is not None:
                for k, v in ExifTags.TAGS.items():
                    if v == 'Orientation':
                        orientation = exif.get(k)
                        break
            if orientation is not None and img is not None:
                if orientation == 3:
                    img = cv2.rotate(img, cv2.ROTATE_180)
                elif orientation == 6:
                    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                elif orientation == 8:
                    img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        except Exception:
            pass
        return img

    def _upload_front(self):
        path, _ = QFileDialog.getOpenFileName(self, "Upload CNIC Front", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return
        self.cnic_front_raw = self._read_img(path)
        if self.cnic_front_raw is None:
            QMessageBox.warning(self, "Error", "Cannot read the selected image.")
            return
        self.cnic_front_enh = enhance_cnic_image(self.cnic_front_raw)
        self.doc_img = self.cnic_front_enh
        self.prev_front.setPixmap(numpy_to_pixmap(self.cnic_front_enh, 130, 95))
        log_message(self.log, "CNIC front uploaded and enhanced successfully.", "success")
        self._enter_cnic_dialog()

    def _upload_back(self):
        path, _ = QFileDialog.getOpenFileName(self, "Upload CNIC Back", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.cnic_back_raw = self._read_img(path)
            if self.cnic_back_raw is not None:
                self.prev_back.setPixmap(
                    numpy_to_pixmap(enhance_cnic_image(self.cnic_back_raw), 130, 95)
                )
                log_message(self.log, "CNIC back uploaded.", "success")

    def _enter_cnic_dialog(self):
        dlg = CnicDataDialog(self, self.cnic_in.text())
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.result_data
            self.cnic_in.setText(d["cnic"])
            self.name_in.setText(d["name"])
            self.father_in.setText(d.get("father_name", ""))
            self.dob_in.setText(d.get("date_of_birth", ""))
            self.addr_in.setText(d.get("address", ""))
            log_message(self.log, f"Customer data entered: {d['name']}", "success")

    def _load_bank(self):
        cnic = self.cnic_in.text().strip()
        if not cnic:
            QMessageBox.warning(self, "CNIC Required", "Please enter a CNIC number first.")
            return
        p = get_customer_profile(cnic)
        if not p["found_in_database"]:
            QMessageBox.information(self, "Not Found", "CNIC not found in demo database.")
            return
        c = p["citizen"]
        self.cnic_in.setText(normalize_cnic_entered(c.get("cnic", cnic)))
        self.name_in.setText(c.get("name", ""))
        self.father_in.setText(c.get("father") or c.get("father_name", ""))
        self.dob_in.setText(c.get("dob", ""))
        self.addr_in.setText(c.get("address", ""))
        self.hint.setText(f"Loaded: {c.get('name')}  |  AML Status: {p['decision']['status']}")
        log_message(self.log, f"Loaded record from database: {c.get('name')}", "success")

    def _lookup_profile(self):
        cnic = self.cnic_in.text().strip()
        if not cnic:
            QMessageBox.warning(self, "CNIC Required", "Please enter a CNIC number first.")
            return
        profile = get_customer_profile(cnic)
        profile_text = [
            f"CNIC: {profile['cnic']}",
            f"Bank Record: {'FOUND' if profile['found_in_database'] else 'NOT FOUND'}",
            f"Criminal Record: {'⚠ FLAGGED' if profile['criminal_record'].get('has_criminal_record') else '✔ CLEAR'}",
            f"Decision: {profile['decision']['status']}",
            f"Reason: {profile['decision']['reason']}",
            f"Previous Checks: {profile['previous_count']}",
        ]
        if profile['found_in_database']:
            citizen = profile['citizen']
            profile_text.insert(1, f"Name: {citizen.get('name', 'N/A')}")
            profile_text.insert(2, f"Father: {citizen.get('father') or citizen.get('father_name', 'N/A')}")
        if profile['criminal_record'].get('has_criminal_record'):
            profile_text.append("")
            profile_text.append("Crimes on Record:")
            for crime in profile['criminal_record'].get('crimes', []):
                profile_text.append(f"  ▸ {crime.get('type')} ({crime.get('date')})")
                profile_text.append(f"    {crime.get('description', '')}")
        QMessageBox.information(self, "Customer Profile", "\n".join(profile_text))
        log_message(self.log, f"Profile lookup complete: {profile['decision']['status']}", "success")

    def _save(self):
        if self.cnic_front_raw is None:
            QMessageBox.warning(self, "Upload Required", "Please upload the CNIC front image first.")
            return
        manual = {
            "cnic": normalize_cnic_entered(self.cnic_in.text()),
            "name": self.name_in.text().strip(),
            "father_name": self.father_in.text().strip(),
            "date_of_birth": self.dob_in.text().strip(),
            "address": self.addr_in.text().strip(),
        }
        ok, msg = validate_pakistan_cnic(manual["cnic"])
        if not ok:
            QMessageBox.warning(self, "Invalid CNIC", msg)
            return
        if not is_valid_person_name(manual["name"]):
            QMessageBox.warning(self, "Invalid Name", "Please enter a valid full name.")
            return
        self.cnic_front_enh = enhance_cnic_image(self.cnic_front_raw)
        folder = save_cnic_archive(
            manual["cnic"], self.cnic_front_raw, self.cnic_front_enh,
            self.cnic_back_raw, None, manual,
            face_img=self.face_img,
            doc_img=self.doc_img,
        )
        OFFICIAL_DATABASE[manual["cnic"]] = {
            **manual,
            "father": manual["father_name"],
            "dob": manual["date_of_birth"],
            "trust_score": 85,
        }
        with open(DATABASE_FILE, "w", encoding="utf-8") as f:
            json.dump(OFFICIAL_DATABASE, f, indent=2)
        QMessageBox.information(self, "Saved Successfully", f"Customer record saved to:\n{folder}")
        log_message(self.log, f"Customer saved: {manual['name']}", "success")

    def _capture_face(self):
        d = WebcamDialog(self)
        d.frame_captured.connect(self._on_face)
        d.exec_()

    def _archive_verification(self, manual: dict, results: dict):
        archive_folder = save_cnic_archive(
            manual["cnic"], self.cnic_front_raw, self.cnic_front_enh,
            self.cnic_back_raw, None, manual,
            face_img=self.face_img,
            doc_img=self.doc_img,
        )
        session = {
            "timestamp": datetime.now().isoformat(),
            "cnic": normalize_cnic(manual["cnic"]),
            "manual_data": manual,
            "trust_score": results.get("trust_score"),
            "risk_level": results.get("risk_level"),
            "is_correct_person": results.get("is_correct_person"),
            "is_verified": results.get("is_verified"),
            "criminal_record": results.get("criminal_record"),
            "flags": results.get("flags"),
            "archive_folder": archive_folder,
        }
        save_verification_history(manual["cnic"], session)
        log_message(self.log, f"Verification archived: {archive_folder}", "success")

    def _save_compliance_decision(self, manual: dict, compliance_decision: dict, results: dict):
        compliance_file = Path("verification_data") / "compliance_decisions.json"
        Path("verification_data").mkdir(parents=True, exist_ok=True)
        decisions = {"decisions": []}
        if compliance_file.exists():
            with open(compliance_file, "r", encoding="utf-8") as f:
                try:
                    decisions = json.load(f)
                except json.JSONDecodeError:
                    decisions = {"decisions": []}
        decision_record = {
            "timestamp": compliance_decision["timestamp"],
            "cnic": normalize_cnic(manual["cnic"]),
            "customer_name": manual.get("name"),
            "action": compliance_decision["action"],
            "officer_name": compliance_decision["officer_name"],
            "notes": compliance_decision["notes"],
            "trust_score": results.get("trust_score"),
            "criminal_record": results.get("criminal_record"),
        }
        decisions["decisions"].append(decision_record)
        with open(compliance_file, "w", encoding="utf-8") as f:
            json.dump(decisions, f, indent=2)
        log_message(self.log, "Compliance decision archived to records.", "success")

    def _refresh_recent_verifications(self):
        """Load last 6 verifications from history and display them in the recent panel."""
        all_sessions = []
        hist_dir = Path("verification_data")
        if hist_dir.exists():
            for f in hist_dir.glob("*.json"):
                if f.name == "compliance_decisions.json":
                    continue
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    for s in data.get("sessions", []):
                        all_sessions.append(s)
                except Exception:
                    pass
        all_sessions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        recent = all_sessions[:6]
        if not recent:
            self.recent_list.setHtml(
                "<div style='color:#4a5568; padding:10px; font-size:12px;'>"
                "No verifications on record yet.</div>"
            )
            return
        html = ""
        for s in recent:
            ts = s.get("timestamp", "")[:16].replace("T", " ")
            name = s.get("manual_data", {}).get("name", "Unknown")
            cnic = s.get("cnic", "")
            trust = s.get("trust_score", 0) or 0
            risk = s.get("risk_level", "unknown")
            has_cr = s.get("criminal_record", {}).get("has_criminal_record", False)
            t_color = "#48bb78" if trust >= 70 else ("#f6ad55" if trust >= 40 else "#fc8181")
            cr_badge = (
                "<span style='background:#5c0000;color:#fc8181;border-radius:3px;"
                "padding:1px 5px;font-size:10px;'>⚠ FLAGGED</span>"
                if has_cr else
                "<span style='background:#0d2a1a;color:#48bb78;border-radius:3px;"
                "padding:1px 5px;font-size:10px;'>✔ CLEAR</span>"
            )
            html += (
                f"<div style='padding:5px 8px; border-bottom:1px solid #1e3a5f;'>"
                f"<span style='color:#90cdf4;font-size:11px;'>{ts}</span>"
                f"&nbsp;&nbsp;<b style='color:#e2e8f0;'>{name}</b>"
                f"&nbsp;<span style='color:#4a5568;font-size:10px;'>{cnic}</span><br>"
                f"<span style='color:{t_color};font-weight:bold;font-size:11px;'>"
                f"Trust: {trust}/100</span>&nbsp;&nbsp;{cr_badge}"
                f"</div>"
            )
        self.recent_list.setHtml(
            f"<div style='background:#0d1421; font-family: Segoe UI, Arial;'>{html}</div>"
        )

    def _show_dip_showcase(self):
        """Open the DIP Showcase dialog for the last processed image."""
        img = None
        label = "Input Image"
        if self.face_img is not None:
            img = self.face_img
            label = "Live Face Capture"
        elif self.cnic_front_enh is not None:
            img = self.cnic_front_enh
            label = "CNIC Front (Enhanced)"
        elif self.doc_img is not None:
            img = self.doc_img
            label = "Document Image"

        if img is None:
            QMessageBox.information(
                self, "No Image",
                "Capture a face or upload a CNIC first, then run verification to see DIP steps."
            )
            return

        dlg = DipShowcaseDialog(
            self,
            image=img,
            image_label=label,
            cnic=self.cnic_in.text().strip(),
            save_callback=self._save_selected_dip_step,
        )
        dlg.exec_()

    def _save_selected_dip_step(self, cnic: str, label: str, image) -> str:
        """Save a selected DIP step image into the CNIC archive."""
        if not cnic:
            raise ValueError("CNIC number is required to save the selected image.")
        if self.cnic_front_raw is None:
            raise ValueError("Please upload the CNIC front image before saving DIP images.")
        saved_path = save_cnic_dip_image(cnic, label, image)
        log_message(self.log, f"Saved DIP filter image '{label}' to archive: {saved_path}", "success")
        return saved_path

    def _export_pdf(self):
        """Generate and save a PDF compliance report for the last verification."""
        if not self.last_results or not self.last_manual:
            QMessageBox.warning(self, "No Data", "Please run a verification first.")
            return
        log_message(self.log, "Generating PDF report...", "info")
        path = generate_pdf_report(self.last_manual, self.last_results, self.last_compliance)
        if path:
            QMessageBox.information(
                self,
                "✔  PDF Report Saved",
                f"Report saved to:\n{path}\n\n"
                f"File: CipherPass_Report_{self.last_manual.get('cnic','').replace('-','')}_..."
            )
            log_message(self.log, f"PDF report saved: {path}", "success")
        else:
            QMessageBox.warning(self, "Export Failed", "Could not generate PDF. Check reportlab is installed.")

    def _on_face(self, frame):
        self.face_img = frame
        self.face_prev.setPixmap(numpy_to_pixmap(frame, 160, 160))
        log_message(self.log, "Face captured successfully.", "success")

    def _show_dip(self):
        img = self.doc_img if self.doc_img is not None else self.face_img
        if img is None:
            QMessageBox.warning(self, "No Image", "Please upload a CNIC or capture a face first.")
            return
        dlg = DipShowcaseDialog(
            self,
            image=img,
            image_label="CNIC Processing",
            cnic=self.cnic_in.text().strip(),
            save_callback=self._save_selected_dip_step,
        )
        dlg.exec_()

    def _verify(self):
        cnic = self.cnic_in.text().strip()
        if not cnic or not is_valid_person_name(self.name_in.text()):
            QMessageBox.warning(self, "Missing Information", "Please enter CNIC and full name.")
            return
        if self.face_img is None:
            QMessageBox.warning(self, "Face Required", "Please capture a face photo first.")
            return
        if self.cnic_front_raw is None:
            QMessageBox.warning(self, "Document Required", "Please upload the CNIC front image first.")
            return

        pre_profile = get_customer_profile(cnic)
        if pre_profile["criminal_record"].get("has_criminal_record"):
            risk = pre_profile["criminal_record"].get("risk_level", "high")
            crimes = pre_profile["criminal_record"].get("crimes", [])
            crime_list = "\n".join([
                "  ▸ " + c.get("type", "Unknown") + " (" + c.get("date", "") + ")"
                for c in crimes
            ])
            msg = (
                "⚠  This CNIC has a criminal record on file!\n\n"
                "Risk Level: " + risk.upper() + "\n"
                "Status: " + pre_profile["criminal_record"].get("status", "") + "\n\n"
                "Crimes on record:\n" + crime_list + "\n\n"
                "Proceeding to full verification and compliance review."
            )
            QMessageBox.warning(self, "WARNING — Criminal Record Detected", msg)

        prev_count = pre_profile.get("previous_count", 0)
        if prev_count >= 3:
            dup_msg = (
                "This CNIC has been verified " + str(prev_count) + " time(s) previously.\n\n"
                "Multiple verifications for the same CNIC may indicate:\n"
                "  ▸ Account takeover attempt\n"
                "  ▸ Identity theft\n"
                "  ▸ Repeat fraud attempt\n\n"
                "Proceeding with verification — compliance review recommended."
            )
            QMessageBox.warning(self, "WARNING — Duplicate Verification Alert", dup_msg)

        self.log.clear()
        self.prog.setVisible(True)
        self.verify_b.setEnabled(False)
        manual = {
            "cnic": cnic,
            "name": self.name_in.text().strip(),
            "father_name": self.father_in.text().strip(),
            "date_of_birth": self.dob_in.text().strip(),
            "address": self.addr_in.text().strip(),
        }
        self.current_manual = manual
        self.worker = VerificationWorker(cnic, self.face_img, self.doc_img, manual)
        self.worker.progress.connect(self.prog.setValue)
        self.worker.step.connect(lambda s: log_message(self.log, s, "info"))
        self.worker.result.connect(self._on_result)
        self.worker.start()

    def _on_result(self, r):
        self.prog.setVisible(False)
        self.verify_b.setEnabled(True)

        trust = r["trust_score"]
        color = "#48bb78" if trust >= 70 else ("#f6ad55" if trust >= 40 else "#fc8181")

        self.score_lbl.setText(f"{trust}/100")
        self.score_lbl.setStyleSheet(f"font-size:52px; font-weight:bold; color:{color};")
        self.risk_lbl.setText(r["risk_level"].upper() + " RISK  |  " + r.get("risk_message", ""))
        self.risk_lbl.setStyleSheet(f"color:{color}; font-size:13px; font-weight:bold;")

        self.person_lbl.setText(
            "✔  IDENTITY VERIFIED" if r.get("is_correct_person") else "✗  CHECK IDENTITY"
        )
        person_color = "#48bb78" if r.get("is_correct_person") else "#fc8181"
        self.person_lbl.setStyleSheet(f"color:{person_color}; font-size:13px; font-weight:bold;")

        cr = r.get("criminal_record", {})
        if cr.get("has_criminal_record"):
            self.crim_lbl.setText("⚠  CRIMINAL RECORD FOUND — " + cr.get("risk_level", "high").upper())
            self.crim_lbl.setStyleSheet("color:#ff4d4f; font-size:13px; font-weight:bold;")
        else:
            self.crim_lbl.setText("✔  CLEAR — No Criminal Record")
            self.crim_lbl.setStyleSheet("color:#48bb78; font-size:13px; font-weight:bold;")

        profile = r.get("profile", {})
        prev_count = profile.get("previous_count", 0)
        if prev_count >= 3:
            self.prev_verif_lbl.setText(f"⚠  DUPLICATE ALERT — {prev_count} previous verifications")
            self.prev_verif_lbl.setStyleSheet("color:#f6ad55; font-size:13px; font-weight:bold;")
            log_message(
                self.log,
                f"DUPLICATE ALERT: CNIC verified {prev_count} times previously — possible fraud.",
                "warning"
            )
        elif prev_count > 0:
            self.prev_verif_lbl.setText(f"{prev_count} previous verification(s) on record")
            self.prev_verif_lbl.setStyleSheet("color:#f6e05e; font-size:13px; font-weight:bold;")
        else:
            self.prev_verif_lbl.setText("✔  First-time verification")
            self.prev_verif_lbl.setStyleSheet("color:#68d391; font-size:13px;")

        self._archive_verification(self.current_manual, r)

        # Store for PDF export
        self.last_results = r
        self.last_manual = self.current_manual
        self.last_compliance = None

        if cr.get("has_criminal_record"):
            log_message(self.log, "Flagged customer — opening compliance review panel...", "warning")
            dlg = ComplianceReviewDialog(
                self,
                customer_name=self.current_manual.get("name", "Unknown"),
                criminal_record=cr,
                trust_score=r["trust_score"]
            )
            if dlg.exec_() == QDialog.Accepted:
                cd = dlg.result_data
                self.last_compliance = cd
                self._save_compliance_decision(self.current_manual, cd, r)
                self._show_compliance_report_in_log(cd, r)
                QMessageBox.information(
                    self,
                    "✔  Compliance Report Submitted",
                    f"Action:   {cd['action_full']}\n"
                    f"Officer:  {cd['officer_name']}\n"
                    f"Time:     {cd['timestamp'][:19].replace('T', '  ')}\n\n"
                    f"Report saved. Click 'Export PDF' to generate a printable report."
                )
            else:
                log_message(self.log, "Compliance review cancelled.", "warning")

        self._show_verification_summary_in_log(r)

        # Show export + DIP buttons & refresh live panels
        self.export_btn.setVisible(True)
        self.dip_btn.setVisible(True)
        self._update_dashboard()
        self._refresh_recent_verifications()

    def _show_compliance_report_in_log(self, cd: dict, r: dict):
        """Display a rich, visible compliance report block in the activity log."""
        ts = cd["timestamp"][:19].replace("T", " ")
        notes_text = cd.get("notes", "").strip() or "<i style='color:#718096;'>No notes entered.</i>"
        cr = r.get("criminal_record", {})
        crimes_html = ""
        for crime in cr.get("crimes", []):
            status_color = "#fc8181" if crime.get("status") == "convicted" else "#f6ad55"
            crimes_html += (
                f"<div style='margin:6px 0; padding:8px; background:#200e00;"
                f" border-left:3px solid #c05621; border-radius:4px;'>"
                f"<b style='color:#fc8181;'>{crime.get('type','')}</b>"
                f"<span style='color:#a0aec0;'> ({crime.get('date','')})</span><br>"
                f"<span style='color:#e2d4c0; font-size:11px;'>{crime.get('description','')}</span><br>"
                f"<span style='color:{status_color}; font-size:11px;'>"
                f"Status: {crime.get('status','').upper()}</span>"
                f"<span style='color:#a0aec0; font-size:11px;'>"
                f"  |  Penalty: {crime.get('penalty','N/A')}</span>"
                f"</div>"
            )

        action_color = "#fc8181" if "REJECT" in cd["action"] else "#f6ad55"
        html = f"""
<div style='margin:10px 0; padding:14px; background:#0d1a10;
    border:1px solid #276749; border-radius:10px;'>
  <div style='color:#38a169; font-size:14px; font-weight:bold; margin-bottom:8px;'>
    📋  COMPLIANCE REPORT SUBMITTED
  </div>
  <table style='width:100%; color:#e2e8f0; font-size:12px;'>
    <tr>
      <td style='color:#a0aec0; width:120px;'>Officer</td>
      <td><b style='color:#68d391;'>{cd['officer_name']}</b></td>
    </tr>
    <tr>
      <td style='color:#a0aec0;'>Action Taken</td>
      <td><b style='color:{action_color};'>{cd['action_full']}</b></td>
    </tr>
    <tr>
      <td style='color:#a0aec0;'>Timestamp</td>
      <td style='color:#90cdf4;'>{ts}</td>
    </tr>
    <tr>
      <td style='color:#a0aec0; vertical-align:top; padding-top:4px;'>Notes</td>
      <td style='color:#e2e8f0; padding-top:4px;'>{notes_text}</td>
    </tr>
  </table>
  <div style='margin-top:10px; color:#f6ad55; font-size:12px; font-weight:bold;'>
    Crimes on Record:
  </div>
  {crimes_html}
</div>
"""
        self.log.append(html)
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _show_verification_summary_in_log(self, r: dict):
        """Append a clean verification summary block to the log."""
        trust = r["trust_score"]
        t_color = "#48bb78" if trust >= 70 else ("#f6ad55" if trust >= 40 else "#fc8181")
        person_text = "✔  Identity Verified" if r.get("is_correct_person") else "✗  Identity Mismatch"
        person_color = "#48bb78" if r.get("is_correct_person") else "#fc8181"
        cr = r.get("criminal_record", {})
        crim_text = "✔  CLEAR" if not cr.get("has_criminal_record") else "⚠  FLAGGED"
        crim_color = "#48bb78" if not cr.get("has_criminal_record") else "#fc8181"
        flags = r.get("flags", [])
        flags_html = "".join(
            f"<span style='background:#1a2235; color:#90cdf4; border-radius:4px;"
            f" padding:2px 7px; margin:2px; font-size:11px;'>{f}</span>"
            for f in flags
        ) if flags else "<span style='color:#718096;'>No flags raised.</span>"

        html = f"""
<div style='margin:10px 0; padding:14px; background:#0d1421;
    border:1px solid #2d4a6e; border-radius:10px;'>
  <div style='color:#63b3ed; font-size:14px; font-weight:bold; margin-bottom:8px;'>
    🔐  VERIFICATION COMPLETE
  </div>
  <table style='width:100%; color:#e2e8f0; font-size:12px;'>
    <tr>
      <td style='color:#a0aec0; width:160px;'>Trust Score</td>
      <td><b style='color:{t_color}; font-size:15px;'>{trust}/100</b>
          <span style='color:{t_color};'> — {r["risk_level"].upper()} RISK</span></td>
    </tr>
    <tr>
      <td style='color:#a0aec0;'>Biometric Score</td>
      <td style='color:#e2e8f0;'>{r.get("face_score", 0)}%</td>
    </tr>
    <tr>
      <td style='color:#a0aec0;'>Document Score</td>
      <td style='color:#e2e8f0;'>{r.get("doc_score", 0)}%</td>
    </tr>
    <tr>
      <td style='color:#a0aec0;'>Identity Check</td>
      <td><b style='color:{person_color};'>{person_text}</b></td>
    </tr>
    <tr>
      <td style='color:#a0aec0;'>Criminal Record</td>
      <td><b style='color:{crim_color};'>{crim_text}</b></td>
    </tr>
  </table>
  <div style='margin-top:8px;'>
    <span style='color:#a0aec0; font-size:12px;'>Flags: </span>
    {flags_html}
  </div>
</div>
"""
        self.log.append(html)
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


def run_demo():
    """Headless console demo — runs simplified verification using demo database."""
    print("CipherPass — Headless Demo Mode\n")
    demo_cnic = "42101-1234567-1"
    manual = {"cnic": demo_cnic, "name": OFFICIAL_DATABASE.get(demo_cnic, {}).get("name", demo_cnic)}

    face_img = np.full((240, 240, 3), 200, dtype=np.uint8)
    cv2.circle(face_img, (120, 90), 40, (0, 0, 0), 3)
    doc_img = np.full((320, 240, 3), 255, dtype=np.uint8)
    cv2.putText(doc_img, demo_cnic, (8, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    try:
        fr = run_face_verification(face_img)
    except Exception:
        fr = {"confidence": 0.8, "liveness_score": 0.7}
    face_score = fr.get("confidence", 0.8)

    try:
        doc = analyze_document(doc_img)
    except Exception:
        doc = {"authenticity_score": 0.85}
    doc_score = doc.get("authenticity_score", 0.85)

    profile = get_customer_profile(demo_cnic)
    trust = calculate_trust_score(face_score, doc_score, 0.75)
    if profile["criminal_record"].get("has_criminal_record"):
        trust = max(0, trust - 40)
    if profile["decision"]["status"] == "REJECT":
        trust = max(0, trust - 25)

    bank = bank_record_for_cnic(demo_cnic)
    entered_name = manual.get("name", "")
    is_correct = True
    if bank and entered_name:
        from difflib import SequenceMatcher
        sim = SequenceMatcher(None, entered_name.lower(), bank.get("name", "").lower()).ratio()
        is_correct = sim >= 0.45
        if not is_correct:
            trust = max(0, trust - 35)

    results = {
        "cnic": demo_cnic,
        "entered_name": entered_name,
        "face_score": int(face_score * 100),
        "doc_score": int(doc_score * 100),
        "trust_score": int(trust),
        "risk_level": get_risk_level(trust)[0],
        "is_correct_person": is_correct,
        "criminal_record": profile.get("criminal_record", {}),
        "flags": generate_flags(face_score, doc_score, 0.75),
    }

    print(json.dumps(results, indent=2, ensure_ascii=False))


def main():
    app = QApplication(sys.argv)
    win = KYCApplication()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CipherPass — Encrypted Identity & Fraud Intelligence")
    parser.add_argument("--demo", action="store_true", help="Run headless console demo (no GUI)")
    args = parser.parse_args()
    if args.demo:
        run_demo()
    else:
        main()
