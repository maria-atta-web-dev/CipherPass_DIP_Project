"""
================================================================================
DIP CONCEPTS MODULE — CipherPass
================================================================================
Comprehensive Digital Image Processing concepts used in the KYC pipeline.
Each function is labelled with the DIP category it belongs to.

Categories:
  A. Spatial Domain Filtering
  B. Edge Detection
  C. Morphological Operations
  D. Frequency Domain (Fourier Transform)
  E. Thresholding & Segmentation
  F. Color Space Conversion
  G. Histogram Operations
  H. Image Quality Assessment
================================================================================
"""

import cv2
import numpy as np


# ────────────────────────────────────────────────────────────────────────────────
# A. SPATIAL DOMAIN FILTERING
# ────────────────────────────────────────────────────────────────────────────────

def apply_gaussian_blur(img: np.ndarray, ksize: int = 5) -> np.ndarray:
    """
    A1. Gaussian Blur — removes high-frequency noise using a Gaussian kernel.
    Used before edge detection to reduce false positives.
    """
    gray = _to_gray(img)
    return cv2.GaussianBlur(gray, (ksize, ksize), 0)


def apply_median_filter(img: np.ndarray, ksize: int = 5) -> np.ndarray:
    """
    A2. Median Filter — replaces each pixel with the median of its neighbourhood.
    Best for removing salt-and-pepper noise from CNIC scans.
    """
    gray = _to_gray(img)
    return cv2.medianBlur(gray, ksize)


def apply_bilateral_filter(img: np.ndarray) -> np.ndarray:
    """
    A3. Bilateral Filter — smooths while preserving edges.
    Used in CNIC enhancement to denoise without blurring card text.
    """
    gray = _to_gray(img)
    return cv2.bilateralFilter(gray, 9, 75, 75)


def apply_box_filter(img: np.ndarray, ksize: int = 5) -> np.ndarray:
    """
    A4. Box Filter (Averaging) — simple mean of neighbourhood pixels.
    Fastest smoothing; baseline for comparing other filters.
    """
    gray = _to_gray(img)
    return cv2.blur(gray, (ksize, ksize))


def apply_sharpening(img: np.ndarray) -> np.ndarray:
    """
    A5. Unsharp Masking (Sharpening) — enhances edges by subtracting a blurred copy.
    Formula: sharp = 1.6 × original − 0.6 × blurred
    Applied to CNIC scans before OCR to improve text readability.
    """
    gray = _to_gray(img)
    blurred = cv2.GaussianBlur(gray, (0, 0), 2)
    return cv2.addWeighted(gray, 1.6, blurred, -0.6, 0)


# ────────────────────────────────────────────────────────────────────────────────
# B. EDGE DETECTION
# ────────────────────────────────────────────────────────────────────────────────

def apply_canny(img: np.ndarray, low: int = 50, high: int = 150) -> np.ndarray:
    """
    B1. Canny Edge Detection — multi-stage: Gaussian blur → gradient → NMS → hysteresis.
    Used in face and document boundary detection.
    """
    gray = _to_gray(img)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    return cv2.Canny(blurred, low, high)


def apply_sobel_x(img: np.ndarray) -> np.ndarray:
    """
    B2. Sobel X — detects vertical edges (horizontal gradient).
    Highlights left/right boundaries of document fields.
    """
    gray = _to_gray(img)
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    return cv2.convertScaleAbs(sobelx)


def apply_sobel_y(img: np.ndarray) -> np.ndarray:
    """
    B3. Sobel Y — detects horizontal edges (vertical gradient).
    Highlights top/bottom boundaries of document fields.
    """
    gray = _to_gray(img)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    return cv2.convertScaleAbs(sobely)


def apply_laplacian(img: np.ndarray) -> np.ndarray:
    """
    B4. Laplacian (2nd derivative) — detects rapid intensity changes (all directions).
    Also used for blur/liveness scoring: variance of Laplacian measures sharpness.
    """
    gray = _to_gray(img)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return cv2.convertScaleAbs(lap)


def get_blur_score(img: np.ndarray) -> float:
    """
    B4b. Laplacian Variance Score — measures image sharpness.
    High variance → sharp (real face); low variance → blurry (fake photo).
    Threshold used in liveness detection: score > 100 → live face.
    """
    gray = _to_gray(img)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return float(lap.var())


# ────────────────────────────────────────────────────────────────────────────────
# C. MORPHOLOGICAL OPERATIONS
# ────────────────────────────────────────────────────────────────────────────────

def apply_erosion(img: np.ndarray, ksize: int = 3, itr: int = 1) -> np.ndarray:
    """
    C1. Erosion — shrinks bright regions; removes small white noise.
    Used after thresholding to clean up CNIC number regions.
    """
    binary = _to_binary(img)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (ksize, ksize))
    return cv2.erode(binary, kernel, iterations=itr)


def apply_dilation(img: np.ndarray, ksize: int = 3, itr: int = 1) -> np.ndarray:
    """
    C2. Dilation — expands bright regions; fills small gaps in text strokes.
    Used to connect broken digit strokes before OCR.
    """
    binary = _to_binary(img)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (ksize, ksize))
    return cv2.dilate(binary, kernel, iterations=itr)


def apply_opening(img: np.ndarray, ksize: int = 3) -> np.ndarray:
    """
    C3. Opening (Erosion → Dilation) — removes small noise while preserving shape.
    Cleans salt-and-pepper spots from binarised CNIC fields.
    """
    binary = _to_binary(img)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (ksize, ksize))
    return cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)


def apply_closing(img: np.ndarray, ksize: int = 3) -> np.ndarray:
    """
    C4. Closing (Dilation → Erosion) — fills small holes inside objects.
    Joins broken character strokes in scanned text for better OCR.
    """
    binary = _to_binary(img)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (ksize, ksize))
    return cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)


def apply_morph_gradient(img: np.ndarray, ksize: int = 3) -> np.ndarray:
    """
    C5. Morphological Gradient (Dilation − Erosion) — extracts object boundaries.
    Similar to edge detection but purely morphological.
    """
    binary = _to_binary(img)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (ksize, ksize))
    return cv2.morphologyEx(binary, cv2.MORPH_GRADIENT, kernel)


def apply_top_hat(img: np.ndarray, ksize: int = 15) -> np.ndarray:
    """
    C6. Top Hat (Image − Opening) — reveals bright structures smaller than kernel.
    Highlights fine text on uneven CNIC backgrounds.
    """
    gray = _to_gray(img)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (ksize, ksize))
    return cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)


# ────────────────────────────────────────────────────────────────────────────────
# D. FREQUENCY DOMAIN (FOURIER TRANSFORM)
# ────────────────────────────────────────────────────────────────────────────────

def apply_dft_magnitude(img: np.ndarray) -> np.ndarray:
    """
    D1. Discrete Fourier Transform — converts image to frequency domain.
    Magnitude spectrum shows frequency components (low-freq centre, high-freq edges).
    Used to detect periodical patterns in fake/printed ID documents.
    Bright centre = dominant low frequencies (smooth regions).
    Bright edges = high frequencies (fine text, noise).
    """
    gray = _to_gray(img)
    dft = np.fft.fft2(gray.astype(np.float32))
    dft_shift = np.fft.fftshift(dft)
    magnitude = 20 * np.log(np.abs(dft_shift) + 1)
    magnitude = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX)
    return magnitude.astype(np.uint8)


def apply_high_pass_filter(img: np.ndarray, radius: int = 30) -> np.ndarray:
    """
    D2. Frequency Domain High-Pass Filter — blocks low frequencies, keeps edges.
    Reveals fine detail and noise; used to detect printer patterns in fake CNICs.
    """
    gray = _to_gray(img).astype(np.float32)
    dft = np.fft.fftshift(np.fft.fft2(gray))
    h, w = gray.shape
    cy, cx = h // 2, w // 2
    mask = np.ones((h, w), np.float32)
    cv2.circle(mask, (cx, cy), radius, 0, -1)
    filtered = np.fft.ifft2(np.fft.ifftshift(dft * mask))
    result = cv2.normalize(np.abs(filtered), None, 0, 255, cv2.NORM_MINMAX)
    return result.astype(np.uint8)


def apply_low_pass_filter(img: np.ndarray, radius: int = 30) -> np.ndarray:
    """
    D3. Frequency Domain Low-Pass Filter — keeps only low frequencies (blurs).
    Equivalent to Gaussian blur but done in frequency domain.
    """
    gray = _to_gray(img).astype(np.float32)
    dft = np.fft.fftshift(np.fft.fft2(gray))
    h, w = gray.shape
    cy, cx = h // 2, w // 2
    mask = np.zeros((h, w), np.float32)
    cv2.circle(mask, (cx, cy), radius, 1, -1)
    filtered = np.fft.ifft2(np.fft.ifftshift(dft * mask))
    result = cv2.normalize(np.abs(filtered), None, 0, 255, cv2.NORM_MINMAX)
    return result.astype(np.uint8)


# ────────────────────────────────────────────────────────────────────────────────
# E. THRESHOLDING & SEGMENTATION
# ────────────────────────────────────────────────────────────────────────────────

def apply_otsu_threshold(img: np.ndarray) -> np.ndarray:
    """
    E1. Otsu's Thresholding — automatically finds the optimal threshold by
    minimising intra-class variance of pixel intensities (bimodal histogram).
    Used to binarise CNIC images before OCR.
    """
    gray = _to_gray(img)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def apply_adaptive_threshold(img: np.ndarray) -> np.ndarray:
    """
    E2. Adaptive Gaussian Thresholding — threshold computed per region using
    weighted Gaussian mean of the neighbourhood. Handles uneven lighting on CNICs.
    """
    gray = _to_gray(img)
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, 31, 8)


def apply_adaptive_mean_threshold(img: np.ndarray) -> np.ndarray:
    """
    E3. Adaptive Mean Thresholding — threshold = mean of neighbourhood − C.
    Simpler than Gaussian adaptive; good for evenly illuminated documents.
    """
    gray = _to_gray(img)
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                 cv2.THRESH_BINARY, 31, 8)


def apply_contour_detection(img: np.ndarray) -> np.ndarray:
    """
    E4. Contour Detection — finds object boundaries from binary image.
    Used to locate CNIC number regions and face bounding boxes.
    """
    gray = _to_gray(img)
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    cv2.drawContours(vis, contours, -1, (0, 220, 180), 1)
    return vis


# ────────────────────────────────────────────────────────────────────────────────
# F. COLOR SPACE CONVERSION
# ────────────────────────────────────────────────────────────────────────────────

def to_hsv(img: np.ndarray) -> np.ndarray:
    """
    F1. BGR → HSV — separates Hue, Saturation, Value.
    Used to detect skin-tone regions for face segmentation independent of lighting.
    """
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2HSV)


def to_lab(img: np.ndarray) -> np.ndarray:
    """
    F2. BGR → CIELAB — perceptually uniform colour space.
    L* = lightness, a* = green↔red, b* = blue↔yellow.
    Used for colour-based document authentication (hologram detection).
    """
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2LAB)


def to_ycrcb(img: np.ndarray) -> np.ndarray:
    """
    F3. BGR → YCrCb — separates luma (Y) from chroma (Cr, Cb).
    Skin detection range: Cr ∈ [133,173], Cb ∈ [77,127].
    Used for face region segmentation during liveness detection.
    """
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)


def extract_skin_mask(img: np.ndarray) -> np.ndarray:
    """
    F4. Skin Colour Segmentation — masks pixels in YCrCb skin tone range.
    Cr ∈ [133, 173], Cb ∈ [77, 127].
    Used to isolate face region from background before liveness check.
    """
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    lower = np.array([0, 133, 77], dtype=np.uint8)
    upper = np.array([255, 173, 127], dtype=np.uint8)
    mask = cv2.inRange(ycrcb, lower, upper)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)


# ────────────────────────────────────────────────────────────────────────────────
# G. HISTOGRAM OPERATIONS
# ────────────────────────────────────────────────────────────────────────────────

def apply_hist_equalization(img: np.ndarray) -> np.ndarray:
    """
    G1. Histogram Equalization — redistributes pixel intensities to span full 0–255.
    Improves contrast in dark/overexposed face and CNIC images.
    """
    gray = _to_gray(img)
    return cv2.equalizeHist(gray)


def apply_clahe(img: np.ndarray, clip: float = 2.5) -> np.ndarray:
    """
    G2. CLAHE — Contrast Limited Adaptive Histogram Equalization.
    Like histogram equalization but applied to local tiles to prevent over-amplification.
    clip_limit controls noise amplification. Used in CNIC scanner pipeline.
    """
    gray = _to_gray(img)
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    return clahe.apply(gray)


def compute_histogram(img: np.ndarray) -> np.ndarray:
    """
    G3. Histogram Correlation — computes and compares pixel intensity histograms.
    cv2.compareHist(h1, h2, HISTCMP_CORREL) → similarity score ∈ [-1, 1].
    Used for face-to-CNIC photo matching.
    """
    gray = _to_gray(img)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    cv2.normalize(hist, hist)
    vis = np.zeros((200, 256), dtype=np.uint8)
    for i, v in enumerate(hist[:, 0]):
        h = int(v * 190)
        cv2.line(vis, (i, 200), (i, 200 - h), 255, 1)
    return vis


# ────────────────────────────────────────────────────────────────────────────────
# H. IMAGE QUALITY ASSESSMENT
# ────────────────────────────────────────────────────────────────────────────────

def compute_psnr(original: np.ndarray, processed: np.ndarray) -> float:
    """
    H1. PSNR — Peak Signal-to-Noise Ratio.
    Measures how much noise was introduced by processing.
    PSNR (dB) = 10 × log10(MAX² / MSE). Higher = better quality.
    """
    g1 = _to_gray(original).astype(np.float64)
    g2 = _to_gray(processed).astype(np.float64)
    g2 = cv2.resize(g2, (g1.shape[1], g1.shape[0]))
    mse = np.mean((g1 - g2) ** 2)
    if mse == 0:
        return float('inf')
    return 10 * np.log10(255.0 ** 2 / mse)


def compute_blur_score(img: np.ndarray) -> float:
    """
    H2. Blur Score — variance of the Laplacian operator output.
    Lower variance = blurrier image. Used in liveness detection.
    Score > 150: Sharp (live face)
    Score > 100: Acceptable
    Score < 50:  Blurry (possible fake photo)
    """
    return get_blur_score(img)


def compute_ssim_approx(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    H3. SSIM approximation — Structural Similarity Index.
    Compares luminance, contrast, and structure between two images.
    Range: [-1, 1], where 1 = identical. Used in CNIC re-scan comparison.
    """
    g1 = _to_gray(img1).astype(np.float64)
    g2 = _to_gray(img2).astype(np.float64)
    g2 = cv2.resize(g2, (g1.shape[1], g1.shape[0]))
    mu1, mu2 = g1.mean(), g2.mean()
    s1, s2 = g1.std(), g2.std()
    s12 = np.mean((g1 - mu1) * (g2 - mu2))
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    return float((2 * mu1 * mu2 + c1) * (2 * s12 + c2) /
                 ((mu1 ** 2 + mu2 ** 2 + c1) * (s1 ** 2 + s2 ** 2 + c2)))


# ────────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ────────────────────────────────────────────────────────────────────────────────

def _to_gray(img: np.ndarray) -> np.ndarray:
    if img is None or img.size == 0:
        return np.zeros((100, 100), dtype=np.uint8)
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img.copy()


def _to_binary(img: np.ndarray) -> np.ndarray:
    gray = _to_gray(img)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def _gray_to_bgr(img: np.ndarray) -> np.ndarray:
    if len(img.shape) == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img


# ────────────────────────────────────────────────────────────────────────────────
# FULL SHOWCASE PIPELINE — returns ordered list of (label, description, bgr_image)
# ────────────────────────────────────────────────────────────────────────────────

SHOWCASE_STEPS = [
    # label, description, function, category
    ("Original",               "Input image as captured",                          lambda i: i),
    ("Grayscale",              "A: Colour→Intensity conversion (luminance only)",   lambda i: _gray_to_bgr(_to_gray(i))),
    ("Gaussian Blur",          "A: Low-pass spatial filter — Gaussian kernel 5×5", lambda i: _gray_to_bgr(apply_gaussian_blur(i))),
    ("Median Filter",          "A: Non-linear filter — removes salt & pepper noise",lambda i: _gray_to_bgr(apply_median_filter(i))),
    ("Bilateral Filter",       "A: Edge-preserving smoothing for CNIC denoising",  lambda i: _gray_to_bgr(apply_bilateral_filter(i))),
    ("Sharpening",             "A: Unsharp mask — improves OCR text clarity",      lambda i: _gray_to_bgr(apply_sharpening(i))),
    ("Hist. Equalization",     "G: Redistributes intensities → full 0–255 range",  lambda i: _gray_to_bgr(apply_hist_equalization(i))),
    ("CLAHE",                  "G: Adaptive local contrast enhancement",            lambda i: _gray_to_bgr(apply_clahe(i))),
    ("Canny Edges",            "B: Multi-stage edge detector — NMS + hysteresis",  lambda i: _gray_to_bgr(apply_canny(i))),
    ("Sobel X",                "B: Horizontal gradient — vertical edges",          lambda i: _gray_to_bgr(apply_sobel_x(i))),
    ("Sobel Y",                "B: Vertical gradient — horizontal edges",          lambda i: _gray_to_bgr(apply_sobel_y(i))),
    ("Laplacian",              "B: 2nd-order derivative — all-direction edges",    lambda i: _gray_to_bgr(apply_laplacian(i))),
    ("Otsu Threshold",         "E: Global auto-threshold from bimodal histogram",  lambda i: _gray_to_bgr(apply_otsu_threshold(i))),
    ("Adaptive Threshold",     "E: Local Gaussian threshold — handles shadows",    lambda i: _gray_to_bgr(apply_adaptive_threshold(i))),
    ("Erosion",                "C: Shrinks bright pixels — removes noise dots",    lambda i: _gray_to_bgr(apply_erosion(i))),
    ("Dilation",               "C: Grows bright pixels — fills character gaps",    lambda i: _gray_to_bgr(apply_dilation(i))),
    ("Opening",                "C: Erosion→Dilation — clean noise, keep shape",    lambda i: _gray_to_bgr(apply_opening(i))),
    ("Closing",                "C: Dilation→Erosion — fill holes in strokes",      lambda i: _gray_to_bgr(apply_closing(i))),
    ("Morph. Gradient",        "C: Dilation − Erosion = object boundaries",        lambda i: _gray_to_bgr(apply_morph_gradient(i))),
    ("Top Hat",                "C: Image − Opening = bright features on bg",       lambda i: _gray_to_bgr(apply_top_hat(i))),
    ("DFT Magnitude",          "D: Fourier spectrum — freq. domain representation",lambda i: _gray_to_bgr(apply_dft_magnitude(i))),
    ("High-Pass Filter",       "D: Keeps high-freq — detects print patterns",      lambda i: _gray_to_bgr(apply_high_pass_filter(i))),
    ("Low-Pass Filter",        "D: Keeps low-freq — frequency-domain blur",        lambda i: _gray_to_bgr(apply_low_pass_filter(i))),
    ("Contour Detection",      "E: Object boundary tracing from binary image",     lambda i: apply_contour_detection(i)),
    ("Histogram Plot",         "G: Pixel intensity distribution (256 bins)",       lambda i: _gray_to_bgr(compute_histogram(i))),
    ("Skin Mask",              "F: YCrCb skin-tone segmentation for face region",  lambda i: _gray_to_bgr(extract_skin_mask(i))),
    ("HSV Colour Space",       "F: Hue-Saturation-Value — lighting-invariant",     lambda i: to_hsv(i)),
    ("LAB Colour Space",       "F: CIELAB — perceptually uniform colour model",    lambda i: to_lab(i)),
]


def run_showcase(image: np.ndarray) -> list:
    """
    Run all DIP showcase steps on an image.
    Returns list of (label, description, bgr_image).
    """
    if image is None or image.size == 0:
        return []
    results = []
    for label, description, fn in SHOWCASE_STEPS:
        try:
            out = fn(image)
            if out is None or out.size == 0:
                continue
            if len(out.shape) == 2:
                out = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
            results.append((label, description, out))
        except Exception as e:
            continue
    return results


def get_quality_report(image: np.ndarray) -> dict:
    """
    Compute image quality metrics for KYC compliance reporting.
    Returns blur score, resolution, and quality verdict.
    """
    if image is None or image.size == 0:
        return {"blur": 0.0, "resolution": "N/A", "verdict": "No image"}
    h, w = image.shape[:2]
    blur = compute_blur_score(image)
    res = f"{w}×{h} px"
    if blur > 150:
        verdict = "Sharp — suitable for KYC"
    elif blur > 80:
        verdict = "Acceptable — use in adequate light"
    else:
        verdict = "Blurry — retake required"
    return {"blur": round(blur, 1), "resolution": res, "verdict": verdict}
