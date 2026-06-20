# app/ui/views/user_management_view.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QDialog, QLabel, QLineEdit, QComboBox, QMessageBox, QAbstractItemView)
from PySide6.QtCore import Qt
from app.services.user_service import UserService
from app.models.schema import UserStatus

class UserFormDialog(QDialog):
    def __init__(self, parent, user_service: UserService, current_user, user_to_edit=None):
        super().__init__(parent)
        self.user_service = user_service
        self.current_user = current_user
        self.user_to_edit = user_to_edit  # If populated, dialog runs in 'Edit Mode'
        
        self.setWindowTitle("Edit Operator Profile" if self.user_to_edit else "Provision New User Profile")
        self.setFixedSize(460, 620) 
        self.init_ui()
        self.populate_existing_data()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; color: #2b2d42; font-family: 'Segoe UI', Arial, sans-serif; }
            QLineEdit, QComboBox { 
                border: 1px solid #ccd1d9; border-radius: 4px; padding: 8px; color: #2b2d42; background: #ffffff;
                font-size: 13px; min-height: 22px;
            }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #00adb5; background-color: #fafafa; }
            QLabel { font-weight: bold; color: #4a5568; font-size: 13px; margin-top: 2px; }
            QPushButton { border-radius: 4px; padding: 10px 15px; font-weight: bold; font-size: 13px; min-height: 20px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 25)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Full Operator Name *"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("John Doe")
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("System Unique Username *"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("johndoe")
        layout.addWidget(self.username_input)

        layout.addWidget(QLabel("Email Address (Optional)"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("johndoe@company.com")
        layout.addWidget(self.email_input)

        layout.addWidget(QLabel("Mobile Number (Optional)"))
        self.mobile_input = QLineEdit()
        self.mobile_input.setPlaceholderText("e.g., +254700000000")
        layout.addWidget(self.mobile_input)

        self.pin_label = QLabel("Secure Access PIN *")
        layout.addWidget(self.pin_label)
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.pin_input)

        layout.addWidget(QLabel("Assigned Business Role Context *"))
        self.role_combo = QComboBox()
        layout.addWidget(self.role_combo)

        try:
            roles = self.user_service.get_roles_list(self.current_user)
            for role in roles:
                self.role_combo.addItem(role.role_name, role.id)
        except Exception as e:
            QMessageBox.critical(self, "Core Fault", f"Unable to establish authorization matrix map link: {e}")

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background-color: #edf2f7; color: #4a5568; border: none;")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save Changes" if self.user_to_edit else "Save Access Profile")
        self.save_btn.setStyleSheet("background-color: #00adb5; color: white; border: none;")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.process_submission)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def populate_existing_data(self):
        if self.user_to_edit:
            self.name_input.setText(self.user_to_edit.name)
            self.username_input.setText(self.user_to_edit.username)
            self.email_input.setText(self.user_to_edit.email if self.user_to_edit.email else "")
            self.mobile_input.setText(self.user_to_edit.mobile_number if self.user_to_edit.mobile_number else "")
            
            # Make the PIN field visually and structurally optional during updates
            self.pin_label.setText("Update Access PIN (Leave blank to keep current)")
            self.pin_input.setPlaceholderText("Enter new numeric key combinations only if changing")
            
            index = self.role_combo.findData(self.user_to_edit.role_id)
            if index >= 0:
                self.role_combo.setCurrentIndex(index)

    def process_submission(self):
        try:
            if self.user_to_edit:
                self.user_service.update_user_details(
                    current_user=self.current_user,
                    target_user_id=self.user_to_edit.id,
                    name=self.name_input.text(),
                    username=self.username_input.text(),
                    role_id=self.role_combo.currentData(),
                    mobile_number=self.mobile_input.text(),
                    email=self.email_input.text(),
                    pin=self.pin_input.text()
                )
            else:
                self.user_service.create_new_user(
                    current_user=self.current_user,
                    name=self.name_input.text(),
                    username=self.username_input.text(),
                    pin=self.pin_input.text(),
                    role_id=self.role_combo.currentData(),
                    mobile_number=self.mobile_input.text(),
                    email=self.email_input.text()
                )
            QMessageBox.information(self, "Success", "Operational credential configuration synchronized successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Operation Rejected", str(e))


class UserManagementView(QWidget):
    def __init__(self, current_user, db_session):
        super().__init__()
        self.current_user = current_user
        self.db_session = db_session
        from app.repositories.user_repo import UserRepository
        self.repo = UserRepository(db_session)
        self.service = UserService(self.repo)
        
        self.init_ui()
        self.reload_user_records()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8f9fa; font-family: 'Segoe UI', Arial, sans-serif; color: #2b2d42; }
            QTableWidget { background-color: #ffffff; border: 1px solid #e1e4e8; border-radius: 6px; gridline-color: #edf2f7; }
            QHeaderView::section { background-color: #edf2f7; color: #4a5568; font-weight: bold; border: none; padding: 10px; font-size: 13px; }
            QPushButton#actionBtn { background-color: #00adb5; color: white; font-weight: bold; border: none; padding: 10px 16px; border-radius: 4px; }
            QPushButton#actionBtn:hover { background-color: #008c95; }
            QPushButton#secondaryBtn { background-color: #ffffff; color: #4a5568; border: 1px solid #ccd1d9; font-weight: bold; padding: 10px 16px; border-radius: 4px; }
            QPushButton#secondaryBtn:hover { background-color: #edf2f7; color: #1a202c; }
            QPushButton#toggleBtn { background-color: #ffffff; color: #4a5568; border: 1px solid #ccd1d9; font-weight: bold; padding: 10px 16px; border-radius: 4px; }
            QPushButton#toggleBtn:hover { background-color: #fff5f5; color: #e53e3e; border: 1px solid #e53e3e; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        top_bar = QHBoxLayout()
        title = QLabel("System List")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2b2d42;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.add_user_btn = QPushButton("+ User")
        self.add_user_btn.setObjectName("actionBtn")
        self.add_user_btn.setCursor(Qt.PointingHandCursor)
        self.add_user_btn.clicked.connect(self.launch_creation_form)
        top_bar.addWidget(self.add_user_btn)

        self.edit_user_btn = QPushButton("Edit User")
        self.edit_user_btn.setObjectName("secondaryBtn")
        self.edit_user_btn.setCursor(Qt.PointingHandCursor)
        self.edit_user_btn.clicked.connect(self.launch_edit_form)
        top_bar.addWidget(self.edit_user_btn)

        self.toggle_status_btn = QPushButton("Update Status")
        self.toggle_status_btn.setObjectName("toggleBtn")
        self.toggle_status_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_status_btn.clicked.connect(self.execute_status_toggle)
        top_bar.addWidget(self.toggle_status_btn)

        main_layout.addLayout(top_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Internal ID", "Full Name", "Username ID", "Email Address", "Mobile Number", "Access Clearance", "Status Profile"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self.launch_edit_form) # Support double-click to edit rows
        
        main_layout.addWidget(self.table)

    def reload_user_records(self):
        try:
            self.table.setRowCount(0)
            users = self.service.get_users_list(self.current_user)
            
            for row_idx, user in enumerate(users):
                self.table.insertRow(row_idx)
                
                id_item = QTableWidgetItem(str(user.id))
                name_item = QTableWidgetItem(user.name)
                uname_item = QTableWidgetItem(user.username)
                email_item = QTableWidgetItem(user.email if user.email else "—")
                mobile_item = QTableWidgetItem(user.mobile_number if user.mobile_number else "—")
                role_item = QTableWidgetItem(user.role.role_name)
                status_item = QTableWidgetItem(user.status.value)
                
                id_item.setTextAlignment(Qt.AlignCenter)
                status_item.setTextAlignment(Qt.AlignCenter)

                if user.status.value == "ACTIVE":
                    status_item.setForeground(Qt.GlobalColor.darkGreen)
                else:
                    status_item.setForeground(Qt.GlobalColor.red)

                self.table.setItem(row_idx, 0, id_item)
                self.table.setItem(row_idx, 1, name_item)
                self.table.setItem(row_idx, 2, uname_item)
                self.table.setItem(row_idx, 3, email_item)
                self.table.setItem(row_idx, 4, mobile_item)
                self.table.setItem(row_idx, 5, role_item)
                self.table.setItem(row_idx, 6, status_item)

        except PermissionError as pe:
            QMessageBox.critical(self, "Security Restriction", str(pe))
        except Exception as e:
            QMessageBox.critical(self, "Data Engine Failure", f"Could not sync structural details: {e}")

    def launch_creation_form(self):
        dialog = UserFormDialog(self, self.service, self.current_user)
        if dialog.exec() == QDialog.Accepted:
            self.reload_user_records()

    def launch_edit_form(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selection Required", "Please choose an operator from the list grid to edit.")
            return

        target_row = selected_rows[0].row()
        target_id = int(self.table.item(target_row, 0).text())
        
        # Load object context from DB
        user_to_edit = self.repo.get_user_by_id(target_id)
        
        if user_to_edit:
            dialog = UserFormDialog(self, self.service, self.current_user, user_to_edit=user_to_edit)
            if dialog.exec() == QDialog.Accepted:
                self.reload_user_records()
        else:
            QMessageBox.critical(self, "Error", "Could not locate targeted user context in active session database memory.")

    def execute_status_toggle(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selection Required", "Please choose a user record grid line from the table layout.")
            return

        target_row = selected_rows[0].row()
        target_id = int(self.table.item(target_row, 0).text())

        try:
            self.service.toggle_user_status(self.current_user, target_id)
            self.reload_user_records()
        except Exception as e:
            QMessageBox.warning(self, "Action Disallowed", str(e))