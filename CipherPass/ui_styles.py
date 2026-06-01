"""CipherPass — Premium UI theme for PyQt5."""

APP_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0b0f1a;
    color: #e8eaed;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    margin-top: 20px;
    padding: 18px 14px 14px 14px;
    background-color: #111827;
    font-weight: bold;
    font-size: 13px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 18px;
    padding: 2px 10px;
    color: #38b2ac;
    font-size: 13px;
    font-weight: bold;
}
QLineEdit {
    background-color: #1a2235;
    border: 1px solid #2d4a6e;
    border-radius: 8px;
    padding: 10px 14px;
    color: #e2e8f0;
    font-size: 13px;
}
QLineEdit:focus {
    border: 2px solid #38b2ac;
    background-color: #1e2d45;
}
QLineEdit:hover {
    border: 1px solid #4a7fa8;
}
QPushButton {
    background-color: #1e3a5f;
    color: #e2e8f0;
    border: none;
    padding: 10px 18px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #2563a8;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #1a4080;
}
QPushButton:disabled {
    background-color: #1a2235;
    color: #4a5568;
}
QTextEdit {
    background-color: #0d1421;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    color: #a8d8b0;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 10px;
    line-height: 1.5;
}
QProgressBar {
    background-color: #1a2235;
    border: none;
    border-radius: 8px;
    text-align: center;
    color: #e2e8f0;
    font-weight: bold;
    min-height: 18px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #38b2ac, stop:1 #4299e1);
    border-radius: 8px;
}
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical {
    background: #111827;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #2d4a6e;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #38b2ac; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QTableWidget {
    background-color: #111827;
    gridline-color: #1e3a5f;
    border-radius: 10px;
    border: none;
}
QHeaderView::section {
    background-color: #1e3a5f;
    color: #e2e8f0;
    padding: 10px;
    border: none;
    font-weight: bold;
}
QComboBox {
    background-color: #1a2235;
    border: 1px solid #2d4a6e;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e2e8f0;
    font-size: 13px;
}
QComboBox:hover { border: 1px solid #38b2ac; }
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #1a2235;
    border: 1px solid #2d4a6e;
    color: #e2e8f0;
    selection-background-color: #2563a8;
}
QDialog {
    background-color: #0f1728;
    color: #e2e8f0;
}
QLabel {
    color: #cbd5e0;
}
QMessageBox {
    background-color: #0f1728;
}
"""

HEADER_STYLE = """
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0d2137, stop:0.5 #0f2d3f, stop:1 #0d2a3a);
    border-radius: 14px;
    padding: 20px 24px;
    border: 1px solid #1e3a5f;
"""

BTN_PRIMARY = """
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #38b2ac, stop:1 #2c9f9a);
    color: #0a1628;
    font-weight: bold;
    border-radius: 8px;
    padding: 10px 18px;
"""

BTN_DANGER = """
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #c53030, stop:1 #e53e3e);
    color: white;
    font-weight: bold;
    border-radius: 8px;
    padding: 10px 18px;
"""

BTN_SUCCESS = """
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #276749, stop:1 #38a169);
    color: white;
    font-weight: bold;
    border-radius: 8px;
    padding: 10px 18px;
"""

BTN_WARNING = """
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #c05621, stop:1 #ed8936);
    color: white;
    font-weight: bold;
    border-radius: 8px;
    padding: 10px 18px;
"""

BTN_VERIFY = """
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1a4b8a, stop:1 #2563a8);
    color: #ffffff;
    font-size: 15px;
    font-weight: bold;
    padding: 16px;
    border-radius: 10px;
    border: 1px solid #3a7bd5;
    letter-spacing: 1px;
"""
