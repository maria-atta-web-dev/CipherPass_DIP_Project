"""
================================================================================
DOCUMENT MODULE - Document Scanning, Tampering Detection, Forgery Analysis
DIP Concepts: Edge Detection, Perspective Transform, ELA, Copy-Move Detection
================================================================================
"""

import cv2
import numpy as np


def preprocess_for_scanning(img):
    """DIP: Grayscale → Gaussian Blur → Canny Edge → Dilation"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    kernel = np.ones((5, 5), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)
    return gray, blurred, edges


def find_document_contour(edges):
    """DIP: Contour detection and polygon approximation"""
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    
    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) == 4:
            return order_corners(approx.reshape(4, 2))
    return None


def order_corners(pts):
    """Order points: TL, TR, BR, BL"""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def perspective_transform(img, corners):
    """DIP: Homography matrix for deskewing documents"""
    (tl, tr, br, bl) = corners
    
    w1 = np.linalg.norm(tr - tl)
    w2 = np.linalg.norm(br - bl)
    h1 = np.linalg.norm(tl - bl)
    h2 = np.linalg.norm(tr - br)
    
    max_w = max(int(w1), int(w2))
    max_h = max(int(h1), int(h2))
    
    dst = np.array([[0, 0], [max_w-1, 0], [max_w-1, max_h-1], [0, max_h-1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(corners, dst)
    return cv2.warpPerspective(img, M, (max_w, max_h))


def detect_tampering(img):
    """DIP: Multi-method tampering detection"""
    tampering_score = 0.0
    indicators = []
    
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()
    
    # Edge density analysis
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size
    
    if edge_density < 0.03:
        tampering_score += 0.3
        indicators.append("Low edge density - Possible forged document")
    elif edge_density > 0.25:
        tampering_score += 0.2
        indicators.append("High edge density - Possible over-processing")
    
    # Blur detection (Laplacian variance)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 50:
        tampering_score += 0.25
        indicators.append(f"Image blurry (variance={laplacian_var:.1f}) - Possible photocopy")
    elif laplacian_var > 500:
        tampering_score += 0.15
        indicators.append("Unusual sharpness - Possible digital manipulation")
    
    # Contrast analysis
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist_norm = hist / hist.sum()
    hist_std = np.std(hist_norm)
    if hist_std < 0.008:
        tampering_score += 0.2
        indicators.append("Poor contrast - Possible manipulation")
    
    # Check for JPEG artifacts
    _, jpeg_encoded = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    jpeg_decoded = cv2.imdecode(jpeg_encoded, cv2.IMREAD_COLOR)
    diff = cv2.absdiff(img, jpeg_decoded)
    compression_error = np.mean(diff)
    
    if compression_error > 8:
        tampering_score += 0.2
        indicators.append(f"JPEG compression artifacts detected - Possible editing")
    
    return min(tampering_score, 1.0), indicators


def detect_ela(img, quality=90):
    """
    DIP: Error Level Analysis (ELA) for JPEG forgery detection
    Original JPEG images have consistent error levels; edited areas show differences
    """
    _, encoded = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    
    diff = cv2.absdiff(img, decoded)
    ela = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    
    ela_mean = np.mean(ela)
    ela_std = np.std(ela)
    
    forged = ela_std > 12
    score = min(ela_std / 25, 1.0)
    
    indicators = []
    if forged:
        indicators.append(f"ELA detected inconsistencies (std={ela_std:.1f}) - Possible image editing")
    
    return {'forgery_detected': forged, 'score': score, 'indicators': indicators, 'ela_image': ela}


def detect_copy_move_forgery(img):
    """
    DIP: Copy-Move Forgery Detection using SIFT feature matching
    Detects cloned/copied regions within the same image
    """
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        
        # Use ORB as alternative to SIFT (no extra dependencies)
        orb = cv2.ORB_create(nfeatures=500)
        keypoints, descriptors = orb.detectAndCompute(gray, None)
        
        if descriptors is None or len(descriptors) < 20:
            return {'forgery_detected': False, 'score': 0, 'indicators': []}
        
        # Match features using brute force matcher
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = bf.knnMatch(descriptors, descriptors, k=2)
        
        # Filter good matches (excluding self-matches)
        good_matches = []
        for i, (m, n) in enumerate(matches):
            if len(match_pair := (m, n)) == 2:
                m, n = match_pair
                if m.distance < 0.75 * n.distance and m.queryIdx != m.trainIdx:
                    good_matches.append(m)
        
        # Detect potential copy-move if many good matches
        if len(good_matches) > 15:
            score = min(len(good_matches) / 80, 1.0)
            return {
                'forgery_detected': score > 0.4,
                'score': score,
                'indicators': [f"Copy-move detected: {len(good_matches)} matching regions"] if score > 0.4 else []
            }
    except Exception as e:
        print(f"Copy-move detection error: {e}")
    
    return {'forgery_detected': False, 'score': 0, 'indicators': []}


def analyze_document(img, doc_type="cnic"):
    """Complete document analysis pipeline"""
    steps = []
    
    gray, blurred, edges = preprocess_for_scanning(img)
    steps.append("Preprocessing: Grayscale + Gaussian Blur + Canny Edge")
    
    corners = find_document_contour(edges)
    
    if corners is not None:
        scanned = perspective_transform(img, corners)
        steps.append("Perspective transform applied - Document deskewed")
    else:
        scanned = img
        steps.append("No document boundaries detected - Using original image")
    
    tampering_score, indicators = detect_tampering(scanned)
    steps.append(f"Tampering detection score: {tampering_score:.2%}")
    
    # Additional forgery detection
    ela_result = detect_ela(scanned)
    if ela_result['forgery_detected']:
        indicators.extend(ela_result['indicators'])
        tampering_score = max(tampering_score, ela_result['score'])
        steps.append(f"ELA forgery detected: {ela_result['score']:.2%}")
    
    copy_move = detect_copy_move_forgery(scanned)
    if copy_move['forgery_detected']:
        indicators.extend(copy_move['indicators'])
        tampering_score = max(tampering_score, copy_move['score'])
        steps.append(f"Copy-move forgery detected: {copy_move['score']:.2%}")
    
    authenticity = 1.0 - tampering_score
    
    return {
        'authentic': authenticity > 0.6,
        'authenticity_score': authenticity,
        'tampering_score': tampering_score,
        'indicators': indicators,
        'scanned_img': scanned,
        'edge_img': edges,
        'gray_img': gray,
        'steps_log': steps
    }
