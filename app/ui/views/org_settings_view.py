from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, 
                             QLineEdit, QPushButton, QMessageBox, QLabel)
from app.repositories.org_repo import OrganizationRepository

class OrganizationSettingsView(QWidget):
    def __init__(self, user, db_session):
        super().__init__()
        self.user = user
        self.repo = OrganizationRepository(db_session)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = QLineEdit()
        self.addr_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.kra_input = QLineEdit()

        form.addRow("Business Name:", self.name_input)
        form.addRow("Address:", self.addr_input)
        form.addRow("Phone:", self.phone_input)
        form.addRow("KRA PIN:", self.kra_input)

        self.save_btn = QPushButton("Save Organization Profile")
        self.save_btn.setStyleSheet("background-color: #00adb5; color: white; padding: 10px; font-weight: bold;")
        self.save_btn.clicked.connect(self.save_changes)

        layout.addWidget(QLabel("Organization Profile Settings"))
        layout.addLayout(form)
        layout.addWidget(self.save_btn)
        layout.addStretch()

    def load_data(self):
        profile = self.repo.get_profile()
        self.name_input.setText(profile.name)
        self.addr_input.setText(profile.address)
        self.phone_input.setText(profile.phone)
        self.kra_input.setText(profile.kra_pin)
        
        # Disable inputs if not admin (UI-level feedback)
        if self.user.role.role_name != "ADMIN":
            self.name_input.setEnabled(False)
            self.addr_input.setEnabled(False)
            self.phone_input.setEnabled(False)
            self.kra_input.setEnabled(False)
            self.save_btn.setEnabled(False)
            self.save_btn.setText("Access Denied: Admin Only")

    def save_changes(self):
        # Logic-level security check
        if self.user.role.role_name != "ADMIN":
            QMessageBox.critical(self, "Access Denied", "Only administrators are permitted to update organization details.")
            return

        try:
            self.repo.update_profile(
                self.name_input.text(),
                self.addr_input.text(),
                self.phone_input.text(),
                self.kra_input.text()
            )
            QMessageBox.information(self, "Success", "Profile updated successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")