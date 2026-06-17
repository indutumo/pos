from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, 
                             QPushButton, QLabel, QMessageBox, QFrame)
from PySide6.QtCore import Qt, Signal
from app.core.database import SessionLocal
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService

class LoginWindow(QWidget):
    authenticated = Signal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zola POS System")
        self.setFixedSize(450, 350)
        self.init_ui()
        
        self.db = SessionLocal()
        self.user_repo = UserRepository(self.db)
        self.auth_service = AuthService(self.user_repo)

    def init_ui(self):
        # Modern Light Palette Styling
        self.setStyleSheet("""
            QWidget {
                background-color: #f4f6f9;
                color: #2b2d42;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QFrame#loginCard {
                background-color: #ffffff;
                border: 1px solid #e1e4e8;
                border-radius: 8px;
                padding: 20px;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #ccd1d9;
                border-radius: 4px;
                padding: 10px;
                color: #2b2d42;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #00adb5;
                background-color: #f9fbfb;
            }
            QPushButton {
                background-color: #00adb5;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #008c95;
            }
            QPushButton:pressed {
                background-color: #006b72;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("loginCard")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(15)

        self.title_label = QLabel("POINT OF SALE LOGIN")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #00adb5; margin-bottom: 10px;")

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")

        self.pin_input = QLineEdit()
        self.pin_input.setPlaceholderText("PIN")
        self.pin_input.setEchoMode(QLineEdit.Password)

        self.login_btn = QPushButton("SIGN IN")
        self.login_btn.clicked.connect(self.handle_login)
        self.username_input.returnPressed.connect(self.handle_login)
        self.pin_input.returnPressed.connect(self.handle_login)

        card_layout.addWidget(self.title_label)
        card_layout.addWidget(self.username_input)
        card_layout.addWidget(self.pin_input)
        card_layout.addWidget(self.login_btn)

        main_layout.addWidget(card)
        self.setLayout(main_layout)

    def handle_login(self):
        username = self.username_input.text().strip()
        pin = self.pin_input.text().strip()

        if not username or not pin:
            QMessageBox.warning(self, "Validation Error", "All fields are strictly required.")
            return

        success, result = self.auth_service.authenticate(username, pin)
        
        if success:
            user = result
            self.authenticated.emit(user)
        else:
            QMessageBox.critical(self, "Access Denied", result)

    def closeEvent(self, event):
        self.db.close()
        event.accept()