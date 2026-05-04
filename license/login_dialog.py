"""
Login Dialog — Giao diện nhập License Key cho Gwen-TTS.

Hiển thị dialog modal yêu cầu người dùng nhập key trước khi truy cập
giao diện chính. Hỗ trợ:
- Tự động điền key đã lưu (nếu có)
- Hiển thị trạng thái xác thực real-time
- Nút liên hệ admin qua Telegram
"""

import sys
import webbrowser
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QApplication, QFrame, QWidget,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon

from .checker import verify_license, get_cached_key, clear_license_cache
from .firebase_config import APP_NAME, ADMIN_TELEGRAM


class LoginDialog(QDialog):
    """Dialog nhập License Key — chặn truy cập app cho đến khi verify OK."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Kích hoạt bản quyền")
        self.setFixedSize(520, 380)
        self.setModal(True)
        
        # Không cho phép đóng bằng nút X (buộc nhập key)
        self.setWindowFlags(
            self.windowFlags()
            & ~Qt.WindowContextHelpButtonHint  # Bỏ nút ? trên Windows
        )
        
        self._license_valid = False
        self._verified_key = None
        
        self._init_ui()
        self._apply_style()
        
        # Tự động điền key đã lưu (nếu có)
        cached_key = get_cached_key()
        if cached_key:
            self.input_key.setText(cached_key)
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 25, 30, 25)
        
        # Header
        title = QLabel(f"🔐 {APP_NAME}")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 22, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; margin-bottom: 5px;")
        layout.addWidget(title)
        
        subtitle = QLabel("Nhập License Key để kích hoạt ứng dụng")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #7f8c8d; font-size: 13px; margin-bottom: 10px;")
        layout.addWidget(subtitle)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #ecf0f1;")
        layout.addWidget(line)
        
        # Key input
        key_label = QLabel("License Key:")
        key_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 14px;")
        layout.addWidget(key_label)
        
        self.input_key = QLineEdit()
        self.input_key.setPlaceholderText("GWEN-XXXX-YYYY-ZZZZ")
        self.input_key.setMaxLength(30)
        self.input_key.setAlignment(Qt.AlignCenter)
        self.input_key.setFont(QFont("Consolas", 16))
        self.input_key.setMinimumHeight(45)
        self.input_key.returnPressed.connect(self._on_verify)
        # Auto uppercase
        self.input_key.textChanged.connect(self._auto_uppercase)
        layout.addWidget(self.input_key)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 13px; padding: 8px;")
        self.status_label.setMinimumHeight(50)
        layout.addWidget(self.status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_verify = QPushButton("🔑  Kích hoạt")
        self.btn_verify.setMinimumHeight(42)
        self.btn_verify.setCursor(Qt.PointingHandCursor)
        self.btn_verify.clicked.connect(self._on_verify)
        btn_layout.addWidget(self.btn_verify)
        
        self.btn_contact = QPushButton("💬  Mua Key")
        self.btn_contact.setMinimumHeight(42)
        self.btn_contact.setCursor(Qt.PointingHandCursor)
        self.btn_contact.clicked.connect(self._on_contact)
        btn_layout.addWidget(self.btn_contact)
        
        layout.addLayout(btn_layout)
        
        # Exit button
        self.btn_exit = QPushButton("Thoát ứng dụng")
        self.btn_exit.setMinimumHeight(35)
        self.btn_exit.setCursor(Qt.PointingHandCursor)
        self.btn_exit.setStyleSheet(
            "background-color: transparent; color: #95a5a6; "
            "border: 1px solid #bdc3c7; font-size: 12px;"
        )
        self.btn_exit.clicked.connect(self._on_exit)
        layout.addWidget(self.btn_exit)
    
    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QLineEdit {
                border: 2px solid #3498db;
                border-radius: 8px;
                padding: 8px 15px;
                font-size: 16px;
                background-color: #f8f9fa;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border-color: #2980b9;
                background-color: #ffffff;
            }
            QPushButton#btn_verify {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton#btn_verify:hover {
                background-color: #2ecc71;
            }
        """)
        # Áp dụng style riêng cho nút Kích hoạt
        self.btn_verify.setStyleSheet(
            "background-color: #27ae60; color: white; border: none; "
            "border-radius: 8px; font-size: 15px; font-weight: bold;"
        )
        self.btn_contact.setStyleSheet(
            "background-color: #3498db; color: white; border: none; "
            "border-radius: 8px; font-size: 14px; font-weight: bold;"
        )
    
    def _auto_uppercase(self, text):
        """Tự động chuyển input sang chữ hoa."""
        cursor_pos = self.input_key.cursorPosition()
        self.input_key.blockSignals(True)
        self.input_key.setText(text.upper())
        self.input_key.setCursorPosition(cursor_pos)
        self.input_key.blockSignals(False)
    
    def _on_verify(self):
        """Xử lý khi bấm nút Kích hoạt."""
        key = self.input_key.text().strip()
        
        if not key:
            self.status_label.setText("⚠️ Vui lòng nhập License Key")
            self.status_label.setStyleSheet(
                "color: #e67e22; font-size: 13px; padding: 8px;"
            )
            return
        
        # Hiển thị đang xác thực
        self.btn_verify.setEnabled(False)
        self.btn_verify.setText("⏳  Đang xác thực...")
        self.status_label.setText("Đang kết nối server...")
        self.status_label.setStyleSheet(
            "color: #3498db; font-size: 13px; padding: 8px;"
        )
        QApplication.processEvents()
        
        # Gọi verify
        result = verify_license(key)
        
        self.btn_verify.setEnabled(True)
        self.btn_verify.setText("🔑  Kích hoạt")
        
        if result.valid:
            self.status_label.setText(result.message)
            self.status_label.setStyleSheet(
                "color: #27ae60; font-size: 13px; padding: 8px; font-weight: bold;"
            )
            self._license_valid = True
            self._verified_key = key
            # Đợi 1s rồi đóng dialog
            QTimer.singleShot(1000, self.accept)
        else:
            self.status_label.setText(result.message)
            self.status_label.setStyleSheet(
                "color: #e74c3c; font-size: 13px; padding: 8px;"
            )
    
    def _on_contact(self):
        """Mở Telegram admin."""
        if ADMIN_TELEGRAM:
            webbrowser.open(ADMIN_TELEGRAM)
        else:
            QMessageBox.information(
                self, "Liên hệ",
                "Vui lòng liên hệ admin qua Telegram để mua license key."
            )
    
    def _on_exit(self):
        """Thoát ứng dụng."""
        self.reject()
    
    def closeEvent(self, event):
        """Ngăn đóng dialog bằng nút X — buộc dùng nút Thoát."""
        if not self._license_valid:
            event.ignore()
        else:
            event.accept()
    
    @property
    def is_verified(self) -> bool:
        return self._license_valid
    
    @property
    def verified_key(self) -> str:
        return self._verified_key


def check_license_or_exit(app: QApplication) -> bool:
    """Kiểm tra license trước khi mở app chính.
    
    Nếu có key trong cache, thử verify tự động.
    Nếu không có hoặc verify fail → hiện LoginDialog.
    
    Args:
        app: QApplication instance
    
    Returns:
        True nếu license hợp lệ, False nếu người dùng chọn thoát.
    """
    # Thử verify key đã lưu trong cache
    cached_key = get_cached_key()
    if cached_key:
        result = verify_license(cached_key)
        if result.valid:
            print(f"[License] {result.message}")
            return True
    
    # Hiện dialog nhập key
    dialog = LoginDialog()
    result = dialog.exec_()
    
    if result == QDialog.Accepted and dialog.is_verified:
        return True
    
    return False
