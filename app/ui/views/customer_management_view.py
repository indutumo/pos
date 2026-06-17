# app/ui/views/customer_management_view.py
import csv
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QDialog, QLabel, QLineEdit, QMessageBox, 
                             QAbstractItemView, QFileDialog)
from PySide6.QtCore import Qt, QMarginsF 
from PySide6.QtGui import QPdfWriter, QTextDocument, QPageLayout, QPageSize
from app.services.customer_service import CustomerService

class CustomerFormDialog(QDialog):
    def __init__(self, parent, customer_service: CustomerService, customer_to_edit=None):
        super().__init__(parent)
        self.customer_service = customer_service
        self.customer_to_edit = customer_to_edit
        
        self.setWindowTitle("Modify Customer Profile" if self.customer_to_edit else "Register New Customer Profile")
        self.setMinimumWidth(480)
        self.init_ui()
        self.populate_existing_data()
        self.adjustSize()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; color: #2b2d42; font-family: 'Segoe UI', Arial, sans-serif; }
            QLineEdit { border: 1px solid #ccd1d9; border-radius: 4px; padding: 8px; color: #2b2d42; background: #ffffff; font-size: 13px; }
            QLineEdit:focus { border: 1px solid #00adb5; background-color: #fafafa; }
            QLabel { font-weight: bold; color: #4a5568; font-size: 13px; margin-top: 4px; }
            QPushButton { border-radius: 4px; padding: 10px 15px; font-weight: bold; font-size: 13px; min-height: 20px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 25)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Full Customer Name *"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. John Doe")
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("Mobile Contact Number"))
        self.mobile_input = QLineEdit()
        self.mobile_input.setPlaceholderText("e.g. +1234567890")
        layout.addWidget(self.mobile_input)

        layout.addWidget(QLabel("Email Address Address"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("e.g. john.doe@enterprise.com")
        layout.addWidget(self.email_input)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background-color: #edf2f7; color: #4a5568; border: none;")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Synchronize Profile" if self.customer_to_edit else "Save Customer")
        self.save_btn.setStyleSheet("background-color: #00adb5; color: white; border: none;")
        self.save_btn.clicked.connect(self.process_submission)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def populate_existing_data(self):
        if self.customer_to_edit:
            self.name_input.setText(self.customer_to_edit.name)
            self.mobile_input.setText(self.customer_to_edit.mobile_number or "")
            self.email_input.setText(self.customer_to_edit.email or "")

    def process_submission(self):
        try:
            if self.customer_to_edit:
                self.customer_service.update_customer(
                    customer_id=self.customer_to_edit.id,
                    name=self.name_input.text(),
                    mobile_number=self.mobile_input.text(),
                    email=self.email_input.text()
                )
            else:
                self.customer_service.create_customer(
                    name=self.name_input.text(),
                    mobile_number=self.mobile_input.text(),
                    email=self.email_input.text()
                )
            QMessageBox.information(self, "Success", "Customer directory payload synchronized cleanly.")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Execution Inhibited", str(e))


class CustomerManagementView(QWidget):
    def __init__(self, current_user, db_session):
        super().__init__()
        self.current_user = current_user
        from app.repositories.customer_repo import CustomerRepository
        self.repo = CustomerRepository(db_session)
        self.service = CustomerService(self.repo)
        
        self.init_ui()
        self.reload_customer_records()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8f9fa; font-family: 'Segoe UI', Arial, sans-serif; color: #2b2d42; }
            QTableWidget { background-color: #ffffff; border: 1px solid #e1e4e8; border-radius: 6px; gridline-color: #edf2f7; }
            QHeaderView::section { background-color: #edf2f7; color: #4a5568; font-weight: bold; border: none; padding: 10px; font-size: 13px; }
            QLineEdit { border: 1px solid #ccd1d9; border-radius: 4px; padding: 8px; color: #2b2d42; background: #ffffff; font-size: 13px; }
            QLineEdit:focus { border: 1px solid #00adb5; }
            QPushButton#actionBtn { background-color: #00adb5; color: white; font-weight: bold; border: none; padding: 10px 16px; border-radius: 4px; }
            QPushButton#actionBtn:hover { background-color: #008c95; }
            QPushButton#secondaryBtn { background-color: #ffffff; color: #4a5568; border: 1px solid #ccd1d9; font-weight: bold; padding: 10px 16px; border-radius: 4px; }
            QPushButton#secondaryBtn:hover { background-color: #edf2f7; }
            QPushButton#inlineEditBtn { background-color: #00adb5; color: white; border: none; padding: 4px 12px; font-weight: bold; font-size: 11px; border-radius: 3px; min-height: 20px; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        top_bar = QHBoxLayout()
        title = QLabel("Customer Relationship Directory Matrix")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2b2d42;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.add_customer_btn = QPushButton("Add New Customer")
        self.add_customer_btn.setObjectName("actionBtn")
        self.add_customer_btn.clicked.connect(self.launch_creation_form)
        top_bar.addWidget(self.add_customer_btn)

        self.export_excel_btn = QPushButton("Export Excel CSV")
        self.export_excel_btn.setObjectName("secondaryBtn")
        self.export_excel_btn.clicked.connect(self.export_to_excel_format)
        top_bar.addWidget(self.export_excel_btn)

        self.export_pdf_btn = QPushButton("Export PDF Document")
        self.export_pdf_btn.setObjectName("secondaryBtn")
        self.export_pdf_btn.clicked.connect(self.export_to_pdf_format)
        top_bar.addWidget(self.export_pdf_btn)

        main_layout.addLayout(top_bar)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Accounts Matrix: Filter records dynamically via customer name or mobile tags...")
        self.search_input.textChanged.connect(self.reload_customer_records)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Customer ID", "Full Name", "Mobile Connection", "Email Address", "Registration Date", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self.launch_edit_form_from_selection)
        
        main_layout.addWidget(self.table)

    def reload_customer_records(self, *args):
        try:
            self.table.setRowCount(0)
            search_query = self.search_input.text()
            customers = self.service.get_customers_list(search_query)
            
            for row_idx, cust in enumerate(customers):
                self.table.insertRow(row_idx)
                
                id_item = QTableWidgetItem(str(cust.id))
                name_item = QTableWidgetItem(cust.name)
                mobile_item = QTableWidgetItem(cust.mobile_number if cust.mobile_number else "N/A")
                email_item = QTableWidgetItem(cust.email if cust.email else "N/A")
                
                created_str = cust.created_at.strftime("%Y-%m-%d %H:%M") if cust.created_at else "N/A"
                date_item = QTableWidgetItem(created_str)
                
                id_item.setTextAlignment(Qt.AlignCenter)
                mobile_item.setTextAlignment(Qt.AlignCenter)
                date_item.setTextAlignment(Qt.AlignCenter)

                self.table.setItem(row_idx, 0, id_item)
                self.table.setItem(row_idx, 1, name_item)
                self.table.setItem(row_idx, 2, mobile_item)
                self.table.setItem(row_idx, 3, email_item)
                self.table.setItem(row_idx, 4, date_item)

                action_container = QWidget()
                action_layout = QHBoxLayout(action_container)
                action_layout.setContentsMargins(0, 2, 0, 2)
                action_layout.setAlignment(Qt.AlignCenter)

                inline_edit_btn = QPushButton("Edit")
                inline_edit_btn.setObjectName("inlineEditBtn")
                inline_edit_btn.setCursor(Qt.PointingHandCursor)
                inline_edit_btn.setProperty("target_customer_id", cust.id)
                inline_edit_btn.clicked.connect(self.handle_inline_edit_click)

                action_layout.addWidget(inline_edit_btn)
                self.table.setCellWidget(row_idx, 5, action_container)

        except Exception as e:
            QMessageBox.critical(self, "Core Execution Fault", f"Data sync failure: {e}")

    def launch_creation_form(self):
        dialog = CustomerFormDialog(self, self.service)
        if dialog.exec() == QDialog.Accepted:
            self.reload_customer_records()

    def handle_inline_edit_click(self):
        button_sender = self.sender()
        if button_sender:
            target_id = button_sender.property("target_customer_id")
            self.execute_modification_pipeline(target_id)

    def launch_edit_form_from_selection(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            return
            
        id_item = self.table.item(current_row, 0)
        if id_item:
            self.execute_modification_pipeline(int(id_item.text()))

    def execute_modification_pipeline(self, customer_id: int):
        customer_to_edit = self.repo.get_by_id(customer_id)
        if customer_to_edit:
            dialog = CustomerFormDialog(self, self.service, customer_to_edit=customer_to_edit)
            if dialog.exec() == QDialog.Accepted:
                self.reload_customer_records()

    def export_to_excel_format(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Customer Directory Ledger", "", "Excel CSV Formats (*.csv)")
        if not path:
            return

        try:
            customers = self.service.get_customers_list(self.search_input.text())
            with open(path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, dialect='excel')
                writer.writerow(["Customer ID", "Full Name", "Mobile Number", "Email Address", "Created Record Timestamp"])
                
                for c in customers:
                    created_str = c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else ""
                    writer.writerow([c.id, c.name, c.mobile_number or "", c.email or "", created_str])
            
            QMessageBox.information(self, "Export Complete", "Customer index data stream extracted output cleanly generated.")
        except Exception as e:
            QMessageBox.critical(self, "Export Failure", f"Unable to safely stream data pipeline: {e}")

    def export_to_pdf_format(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Customer PDF Document Layout", "", "PDF Document Layout (*.pdf)")
        if not path:
            return

        try:
            customers = self.service.get_customers_list(self.search_input.text())
            
            html_content = """
            <html>
            <head>
                <style>
                    body { font-family: 'Segoe UI', Arial, sans-serif; color: #2b2d42; margin: 20px; }
                    h2 { text-align: center; color: #00adb5; font-size: 22pt; margin-bottom: 5px; }
                    .meta { text-align: center; font-size: 11pt; color: #718096; margin-bottom: 25px; }
                    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
                    th { background-color: #edf2f7; color: #4a5568; font-weight: bold; padding: 10px; border: 1px solid #cbd5e0; font-size: 12pt; }
                    td { padding: 8px; border: 1px solid #e2e8f0; font-size: 11pt; }
                    .center { text-align: center; }
                </style>
            </head>
            <body>
                <h2>SYSTEM CORE CUSTOMER RELATIONSHIP MANAGEMENT DIRECTORY</h2>
                <div class="meta">Generated via Central Management Administration View Grid Context</div>
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Customer Name</th>
                        <th class="center">Mobile Connection</th>
                        <th>Email Address</th>
                        <th class="center">Created Date</th>
                    </tr>
            """
            
            for c in customers:
                created_str = c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "N/A"
                html_content += f"""
                    <tr>
                        <td class="center">{c.id}</td>
                        <td style="font-weight: bold;">{c.name}</td>
                        <td class="center">{c.mobile_number if c.mobile_number else 'N/A'}</td>
                        <td>{c.email if c.email else 'N/A'}</td>
                        <td class="center">{created_str}</td>
                    </tr>
                """
                
            html_content += """
                </table>
            </body>
            </html>
            """

            document = QTextDocument()
            document.setHtml(html_content)

            writer = QPdfWriter(path)
            writer.setResolution(96)  # Standardize 96 DPI resolution tracking for high-DPI scaling outputs
            writer.setPageLayout(QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait, QMarginsF(15, 15, 15, 15)))

            document.print_(writer)
            QMessageBox.information(self, "Export Complete", "Vector customer registry ledger document successfully generated.")
        except Exception as e:
            QMessageBox.critical(self, "Export Failure", f"Unable to finalize vector pipeline layer composition: {e}")