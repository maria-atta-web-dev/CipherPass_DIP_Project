"""
================================================================================
DIP SHOWCASE DIALOG — CipherPass
================================================================================
Visual grid showing every DIP concept applied to the last verification image.
Each tile shows: step image + label + one-line DIP description.
================================================================================
"""

import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QGridLayout, QFrame, QComboBox,
    QSizePolicy, QTabWidget, QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage, QFont

from dip_concepts import run_showcase, get_quality_report, SHOWCASE_STEPS


# ── colour for each DIP category letter ─────────────────────────────────────
CATEGORY_COLOURS = {
    "A": ("#1a4b8a", "#63b3ed"),   # Spatial Filtering  — blue
    "B": ("#276749", "#68d391"),   # Edge Detection     — green
    "C": ("#744210", "#f6ad55"),   # Morphological      — orange
    "D": ("#553c9a", "#b794f4"),   # Frequency Domain   — purple
    "E": ("#702459", "#f687b3"),   # Thresholding       — pink
    "F": ("#234e52", "#4fd1c5"),   # Colour Space       — teal
    "G": ("#1a365d", "#90cdf4"),   # Histogram          — light blue
    "H": ("#1a202c", "#a0aec0"),   # Quality Assessment — grey
}

CATEGORY_NAMES = {
    "A": "Spatial Domain Filtering",
    "B": "Edge Detection",
    "C": "Morphological Operations",
    "D": "Frequency Domain (DFT)",
    "E": "Thresholding & Segmentation",
    "F": "Colour Space Conversion",
    "G": "Histogram Operations",
    "H": "Image Quality",
}


def _bgr_to_pixmap(img: np.ndarray, w: int = 140, h: int = 110) -> QPixmap:
    """Convert a BGR numpy array to a scaled QPixmap."""
    if img is None or img.size == 0:
        return QPixmap()
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    qimg = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format_RGB888)
    return QPixmap.fromImage(qimg).scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _cat(desc: str) -> str:
    """Extract category letter from description string like 'A: ...' """
    return desc[0] if desc and desc[0] in CATEGORY_COLOURS else "A"


class DipTile(QFrame):
    """Single DIP step tile: image + label + description."""

    def __init__(self, label: str, description: str, img: np.ndarray, click_callback=None, parent=None):
        super().__init__(parent)
        self._click_callback = click_callback
        self._label = label
        self._description = description
        self._img = img
        cat = _cat(description)
        bg_dark, accent = CATEGORY_COLOURS.get(cat, ("#1a2a3a", "#63b3ed"))

        self.setStyleSheet(
            f"QFrame {{ background:{bg_dark}; border:1px solid {accent}33;"
            f" border-radius:8px; }}"
        )
        self.setFixedSize(175, 195)
        self.setCursor(Qt.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setSpacing(3)
        lay.setContentsMargins(6, 6, 6, 6)

        # image
        img_lbl = QLabel()
        img_lbl.setAlignment(Qt.AlignCenter)
        img_lbl.setPixmap(_bgr_to_pixmap(img, 155, 115))
        img_lbl.setStyleSheet("border:none;")
        lay.addWidget(img_lbl)

        # label
        name_lbl = QLabel(label)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet(
            f"color:{accent}; font-size:11px; font-weight:bold; border:none;"
        )
        name_lbl.setWordWrap(True)
        lay.addWidget(name_lbl)

        # description (category letter stripped)
        desc_clean = description[3:] if len(description) > 3 and description[1] == ":" else description
        desc_lbl = QLabel(desc_clean)
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setStyleSheet("color:#718096; font-size:9px; border:none;")
        desc_lbl.setWordWrap(True)
        lay.addWidget(desc_lbl)

    def mousePressEvent(self, event):
        if self._click_callback:
            self._click_callback(self._label, self._description, self._img)
        super().mousePressEvent(event)


class DipZoomDialog(QDialog):
    """Popup viewer for a selected DIP filter image with save support."""

    def __init__(self, parent=None, label: str = "Step", description: str = "", image: np.ndarray = None,
                 cnic: str = None, save_callback=None):
        super().__init__(parent)
        self.setWindowTitle(f"{label} — Preview")
        self.setMinimumSize(760, 560)
        self.setStyleSheet(
            "QDialog { background:#0f1728; color:#e2e8f0; }"
            "QLabel { color:#e2e8f0; }"
            "QPushButton { background:#1e3a5f; color:#e2e8f0; border-radius:8px;"
            "padding:10px 18px; font-weight:bold; }"
            "QPushButton:hover { background:#2563a8; }"
        )

        self._image = image
        self._step_label = label
        self._description = description
        self._cnic = cnic
        self._save_callback = save_callback

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        title_lbl = QLabel(f"{label}")
        title_lbl.setStyleSheet("color:#63b3ed; font-size:18px; font-weight:bold;")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color:#a0aec0; font-size:12px;")
        layout.addWidget(desc_lbl)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        if image is not None:
            image_label.setPixmap(_bgr_to_pixmap(image, 700, 420))
        image_label.setStyleSheet(
            "background:#111827; border:1px solid #1e3a5f; border-radius:10px;"
        )
        layout.addWidget(image_label, 1)

        hint_lbl = QLabel(
            "Click Save to keep this filtered image in the customer archive for later review."
        )
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet("color:#94a3b8; font-size:11px;")
        layout.addWidget(hint_lbl)

        row = QHBoxLayout()
        row.addStretch()
        save_btn = QPushButton("💾  Save Filter Image")
        save_btn.setEnabled(bool(cnic and save_callback))
        save_btn.clicked.connect(self._on_save)
        row.addWidget(save_btn)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        row.addWidget(close_btn)
        layout.addLayout(row)

    def _on_save(self):
        if not self._save_callback or not self._cnic:
            QMessageBox.warning(self, "Save Unavailable",
                                "Please provide a CNIC number before saving a filter image.")
            return
        try:
            saved_path = self._save_callback(self._cnic, self._step_label, self._image)
            QMessageBox.information(self, "Saved", f"Filter image saved to:\n{saved_path}")
        except Exception as exc:
            QMessageBox.warning(self, "Save Failed", f"Unable to save image:\n{exc}")


class DipShowcaseDialog(QDialog):
    """
    Full-screen dialog showing all DIP steps in a scrollable grid,
    grouped by category in tabs.
    """

    def __init__(self, parent=None, image: np.ndarray = None, image_label: str = "Input",
                 cnic: str = None, save_callback=None):
        super().__init__(parent)
        self.setWindowTitle("🔬  DIP Showcase — CipherPass")
        self.setMinimumSize(1100, 720)
        self.setStyleSheet(
            "QDialog { background-color:#0d1421; color:#e2e8f0; }"
            "QTabWidget::pane { border:1px solid #1e3a5f; }"
            "QTabBar::tab { background:#111827; color:#718096; padding:7px 18px;"
            "  border-radius:4px 4px 0 0; font-size:11px; }"
            "QTabBar::tab:selected { background:#1a2a3a; color:#38b2ac;"
            "  border-bottom:2px solid #38b2ac; }"
            "QScrollArea { border:none; background:#0d1421; }"
            "QWidget { background:#0d1421; }"
        )

        self._image = image
        self._image_label = image_label
        self._cnic = cnic
        self._save_callback = save_callback
        self._results = run_showcase(image) if image is not None else []

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 10)
        root.setSpacing(10)

        # ── title row ────────────────────────────────────────────────────────
        title_row = QHBoxLayout()
        title = QLabel("🔬  Digital Image Processing Showcase")
        title.setStyleSheet(
            "color:#38b2ac; font-size:17px; font-weight:bold; letter-spacing:1px;"
        )
        title_row.addWidget(title)
        title_row.addStretch()

        # quality badge
        if image is not None:
            qr = get_quality_report(image)
            q_lbl = QLabel(
                f"📐 {qr['resolution']}  |  🎯 Blur: {qr['blur']}  |  {qr['verdict']}"
            )
            q_lbl.setStyleSheet(
                "background:#111827; color:#90cdf4; border:1px solid #1e3a5f;"
                " border-radius:8px; padding:5px 12px; font-size:11px;"
            )
            title_row.addWidget(q_lbl)

        # source selector
        self.src_combo = QComboBox()
        self.src_combo.addItem(f"🖼  {image_label}")
        self.src_combo.setStyleSheet(
            "background:#111827; color:#e2e8f0; border:1px solid #1e3a5f;"
            " border-radius:6px; padding:4px 10px; font-size:11px; min-width:140px;"
        )
        title_row.addWidget(self.src_combo)
        root.addLayout(title_row)

        # ── legend ───────────────────────────────────────────────────────────
        legend = QHBoxLayout()
        legend.setSpacing(6)
        for letter, name in CATEGORY_NAMES.items():
            _, accent = CATEGORY_COLOURS[letter]
            chip = QLabel(f"  {letter}: {name}  ")
            chip.setStyleSheet(
                f"background:{CATEGORY_COLOURS[letter][0]}; color:{accent};"
                f" border:1px solid {accent}55; border-radius:4px;"
                f" font-size:9px; padding:2px 4px;"
            )
            legend.addWidget(chip)
        legend.addStretch()
        root.addLayout(legend)

        # ── tab widget ───────────────────────────────────────────────────────
        tabs = QTabWidget()
        root.addWidget(tabs, 1)

        # "All Steps" tab
        all_scroll = self._make_scroll(self._results)
        tabs.addTab(all_scroll, f"🗂  All Steps ({len(self._results)})")

        # per-category tabs
        for letter, cat_name in CATEGORY_NAMES.items():
            subset = [
                (lbl, desc, img_arr)
                for lbl, desc, img_arr in self._results
                if _cat(desc) == letter
            ]
            if not subset:
                continue
            scroll = self._make_scroll(subset)
            tabs.addTab(scroll, f"{letter}: {cat_name.split('(')[0].strip()} ({len(subset)})")

        # ── bottom bar ───────────────────────────────────────────────────────
        bot = QHBoxLayout()
        bot.addStretch()
        close_btn = QPushButton("✕  Close")
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet(
            "background:#1e3a5f; color:#e2e8f0; border-radius:8px;"
            " font-weight:bold; padding:0 20px; font-size:12px;"
        )
        close_btn.clicked.connect(self.accept)
        bot.addWidget(close_btn)
        root.addLayout(bot)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _make_scroll(self, results: list) -> QScrollArea:
        """Build a scrollable grid of DipTile widgets."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(8)
        grid.setContentsMargins(8, 8, 8, 8)

        cols = 6
        for idx, (label, description, img_arr) in enumerate(results):
            tile = DipTile(label, description, img_arr,
                           click_callback=self._on_tile_clicked,
                           parent=content)
            grid.addWidget(tile, idx // cols, idx % cols)

        # fill last row
        rem = len(results) % cols
        if rem:
            for c in range(rem, cols):
                spacer = QWidget()
                spacer.setFixedSize(175, 195)
                grid.addWidget(spacer, len(results) // cols, c)

        scroll.setWidget(content)
        return scroll

    def _on_tile_clicked(self, label: str, description: str, image: np.ndarray):
        dlg = DipZoomDialog(
            self,
            label=label,
            description=description,
            image=image,
            cnic=self._cnic,
            save_callback=self._save_callback,
        )
        dlg.exec_()
