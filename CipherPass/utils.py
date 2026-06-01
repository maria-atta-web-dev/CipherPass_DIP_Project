"""
================================================================================
UTILITIES MODULE - Helper Functions for the Fraud Detection System
================================================================================
This module provides utility functions for:
- Image conversion and resizing
- Case reference generation
- Logging with timestamps and colors
- Report generation
"""

import cv2
import numpy as np
import tempfile
import os
import random
from datetime import datetime
from PyQt5.QtGui import QPixmap, QImage


def first_valid_image(*images):
    """Pick first non-empty numpy image (avoid 'or' on arrays)."""
    for img in images:
        if img is not None and hasattr(img, "size") and img.size > 0:
            return img
    return None


def numpy_to_pixmap(img_array, max_width=None, max_height=None):
    """
    Convert OpenCV numpy array to QPixmap for display in Qt widgets.
    
    DIP CONCEPT: Color space conversion (BGR to RGB) for correct display
    
    Args:
        img_array: OpenCV image (numpy array, BGR format)
        max_width: Maximum width for resizing (optional)
        max_height: Maximum height for resizing (optional)
        
    Returns:
        QPixmap: Qt-compatible image for display
    """
    if img_array is None:
        return QPixmap()
    
    img = img_array.copy()
    
    if max_width and max_height:
        img = resize_with_aspect(img, max_width, max_height)
    
    # DIP CONCEPT: Convert BGR (OpenCV) to RGB (Qt)
    if len(img.shape) == 3:
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    else:
        img_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    
    h, w, ch = img_rgb.shape
    bytes_per_line = ch * w
    qt_image = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
    
    return QPixmap.fromImage(qt_image)


def resize_with_aspect(img, max_w, max_h):
    """
    Resize image while maintaining aspect ratio.
    
    DIP CONCEPT: Image scaling with aspect ratio preservation
    """
    h, w = img.shape[:2]
    scale = min(max_w / w, max_h / h)
    
    if scale < 1:
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    return img


def generate_case_ref():
    """Generate a unique case reference number. Format: CASE-YYYY-NNNN"""
    year = datetime.now().year
    random_num = random.randint(1000, 9999)
    return f"CASE-{year}-{random_num}"


def save_temp_image(numpy_array, prefix="temp_"):
    """Save numpy array image to temporary file"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg', prefix=prefix)
    cv2.imwrite(temp_file.name, numpy_array)
    temp_file.close()
    return temp_file.name


def cleanup_temp_file(file_path):
    """Delete temporary file"""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        print(f"Error cleaning up temp file: {e}")


def log_message(text_widget, message, level="info"):
    """
    Add timestamped message to QTextEdit with color coding.
    
    Log Levels:
    - info: White text (standard information)
    - success: Green text (operation completed)
    - warning: Orange text (cautionary notice)
    - error: Red text (error occurred)
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if level == "success":
        emoji = "✓"
        color = "#3fb950"
    elif level == "warning":
        emoji = "⚠"
        color = "#d29922"
    elif level == "error":
        emoji = "✗"
        color = "#f85149"
    else:
        emoji = "ℹ"
        color = "#e6edf3"
    
    formatted_msg = f'<span style="color: #8b949e;">[{timestamp}]</span> ' \
                    f'<span style="color: {color};">{emoji} {message}</span>'
    
    text_widget.append(formatted_msg)
    
    # Auto-scroll to bottom
    scrollbar = text_widget.verticalScrollBar()
    scrollbar.setValue(scrollbar.maximum())


def generate_report_text(session_data: dict) -> str:
    """Generate a formatted text report for printing/saving"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""
{'='*65}
FRAUD DETECTION & TRUST VERIFICATION SYSTEM
OFFICIAL VERIFICATION REPORT
{'='*65}

Report Generated: {now}

{'*'*65}
CASE INFORMATION
{'*'*65}
Case Reference    : {session_data.get('case_ref', 'N/A')}
Subject Name      : {session_data.get('subject_name', 'N/A')}
Document Type     : {session_data.get('doc_type', 'N/A')}

{'*'*65}
MODULE RESULTS
{'*'*65}
Face Biometric    : {session_data.get('face_score', 0):.1f}% 
Document Auth     : {session_data.get('doc_score', 0):.1f}%
Signature Match   : {session_data.get('sig_score', 0):.1f}%

{'*'*65}
VERDICT
{'*'*65}
TRUST SCORE       : {session_data.get('trust_score', 0)}/100
RISK LEVEL        : {session_data.get('risk_level', 'N/A').upper()}
VERDICT           : {session_data.get('risk_message', 'N/A')}

{'*'*65}
FLAGS RAISED
{'*'*65}
"""
    
    flags = session_data.get('flags', [])
    if flags:
        for flag in flags:
            report += f"• {flag}\n"
    else:
        report += "No flags raised. Identity appears legitimate.\n"
    
    report += f"""
{'*'*65}
RECOMMENDATION
{'*'*65}
{session_data.get('recommendation', 'N/A')}

{'='*65}
END OF REPORT
{'='*65}
"""
    
    return report