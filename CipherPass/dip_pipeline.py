"""
================================================================================
Digital Image Processing (DIP) Pipeline — CipherPass
================================================================================
Expanded 12-step pipeline covering all core DIP categories.
Each step returns an image + label for presentation slides / PDF reports.

Steps grouped by DIP category:
  A. Spatial Filtering   → Grayscale, Gaussian, Bilateral, Sharpening
  B. Edge Detection      → Canny, Sobel X/Y, Laplacian
  C. Morphological       → Erosion, Dilation, Closing
  E. Thresholding        → Otsu, Adaptive
  G. Histogram           → Histogram Equalization, CLAHE
================================================================================
"""

import cv2
import numpy as np

from dip_concepts import (
    apply_gaussian_blur,
    apply_bilateral_filter,
    apply_sharpening,
    apply_canny,
    apply_sobel_x,
    apply_sobel_y,
    apply_laplacian,
    apply_otsu_threshold,
    apply_adaptive_threshold,
    apply_erosion,
    apply_dilation,
    apply_closing,
    apply_hist_equalization,
    apply_clahe,
    apply_dft_magnitude,
    run_showcase,
    get_quality_report,
    _to_gray,
    _gray_to_bgr,
)


# ── Pipeline step registry ───────────────────────────────────────────────────

DIP_STEPS = [
    ("1. Original",                 "original"),
    ("2. Grayscale",                "grayscale"),
    ("3. Histogram Equalization",   "equalized"),
    ("4. CLAHE",                    "clahe"),
    ("5. Gaussian Blur",            "blurred"),
    ("6. Bilateral Filter",         "bilateral"),
    ("7. Sharpening",               "sharpened"),
    ("8. Canny Edges",              "edges"),
    ("9. Sobel X",                  "sobelx"),
    ("10. Sobel Y",                 "sobely"),
    ("11. Otsu Threshold",          "binary"),
    ("12. Adaptive Threshold",      "adaptive"),
    ("13. Erosion",                 "erosion"),
    ("14. Dilation",                "dilation"),
    ("15. Closing",                 "closing"),
    ("16. Laplacian",               "laplacian"),
    ("17. DFT Magnitude",           "dft"),
]


def run_dip_pipeline(image: np.ndarray) -> dict:
    """
    Run the full 17-step DIP pipeline on any input image
    (face capture, CNIC scan, or document photo).

    Returns dict:
      steps  — list of BGR images (one per step)
      labels — list of display labels
    """
    if image is None or image.size == 0:
        return {"steps": [], "labels": []}

    def to_bgr(img):
        return _gray_to_bgr(img)

    gray      = _to_gray(image)
    equalized = apply_hist_equalization(image)
    clahe_img = apply_clahe(image)
    blurred   = apply_gaussian_blur(image)
    bilateral = apply_bilateral_filter(image)
    sharpened = apply_sharpening(image)
    edges     = apply_canny(image)
    sobelx    = apply_sobel_x(image)
    sobely    = apply_sobel_y(image)
    binary    = apply_otsu_threshold(image)
    adaptive  = apply_adaptive_threshold(image)
    erosion   = apply_erosion(image)
    dilation  = apply_dilation(image)
    closing   = apply_closing(image)
    laplacian = apply_laplacian(image)
    dft       = apply_dft_magnitude(image)

    steps = [
        image.copy(),
        to_bgr(gray),
        to_bgr(equalized),
        to_bgr(clahe_img),
        to_bgr(blurred),
        to_bgr(bilateral),
        to_bgr(sharpened),
        to_bgr(edges),
        to_bgr(sobelx),
        to_bgr(sobely),
        to_bgr(binary),
        to_bgr(adaptive),
        to_bgr(erosion),
        to_bgr(dilation),
        to_bgr(closing),
        to_bgr(laplacian),
        to_bgr(dft),
    ]
    labels = [s[0] for s in DIP_STEPS]
    return {"steps": steps, "labels": labels}


def get_dip_summary() -> str:
    """One-paragraph description suitable for reports and PDF exports."""
    return (
        "CipherPass DIP Pipeline (17 steps across 5 categories):\n"
        "  A. Spatial Filtering  → Grayscale · Hist. Equalization · CLAHE · "
        "Gaussian Blur · Bilateral Filter · Sharpening\n"
        "  B. Edge Detection     → Canny · Sobel X · Sobel Y · Laplacian\n"
        "  C. Morphological      → Erosion · Dilation · Closing\n"
        "  E. Thresholding       → Otsu · Adaptive Gaussian\n"
        "  D. Frequency Domain   → DFT Magnitude Spectrum\n\n"
        "Applied sequentially to CNIC, face, and signature images before "
        "fraud analysis and AML screening."
    )
