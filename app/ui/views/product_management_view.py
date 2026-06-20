# app/ui/views/product_management_view.py
import csv
import math
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QTableWidget, QTableWidgetItem, QHeaderView, 
                               QDialog, QLabel, QLineEdit, QComboBox, QMessageBox, 
                               QAbstractItemView, QFileDialog, QTextEdit, QSpinBox, QDoubleSpinBox)
from PySide6.QtCore import Qt, QMarginsF 
from PySide6.QtGui import QPdfWriter, QTextDocument, QPageLayout, QPageSize
from app.services.product_service import ProductService
from app.models.schema import ProductStatus


class ProductFormDialog(QDialog):
    def __init__(self, parent, product_service: ProductService, current_user, product_to_edit=None):
        super().__init__(parent)
        self.product_service = product_service
        self.current_user = current_user
        self.product_to_edit = product_to_edit
        
        self.setWindowTitle("Modify Catalog Item" if self.product_to_edit else "Catalog New Product Profile")
        
        # High-DPI Fix: Using flexible sizing to prevent component clipping across systems
        self.setMinimumWidth(480)
        self.init_ui()
        self.populate_existing_data()
        self.adjustSize()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; color: #2b2d42; font-family: 'Segoe UI', Arial, sans-serif; }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit { 
                border: 1px solid #ccd1d9; border-radius: 4px; padding: 6px; color: #2b2d42; background: #ffffff;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus { 
                border: 1px solid #00adb5; background-color: #fafafa; 
            }
            QLabel { font-weight: bold; color: #4a5568; font-size: 13px; margin-top: 2px; }
            QPushButton { border-radius: 4px; padding: 10px 15px; font-weight: bold; font-size: 13px; min-height: 20px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 25)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Product Name *"))
        self.name_input = QLineEdit()
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("Barcode Identifier Tag *"))
        self.barcode_input = QLineEdit()
        layout.addWidget(self.barcode_input)

        pricing_layout = QHBoxLayout()
        pricing_layout.setSpacing(10)
        
        buy_vbox = QVBoxLayout()
        buy_vbox.addWidget(QLabel("Buying Price *"))
        self.buying_input = QDoubleSpinBox()
        self.buying_input.setRange(0.00, 9999999.99)
        self.buying_input.setDecimals(2)
        buy_vbox.addWidget(self.buying_input)
        
        sell_vbox = QVBoxLayout()
        sell_vbox.addWidget(QLabel("Selling Price *"))
        self.selling_input = QDoubleSpinBox()
        self.selling_input.setRange(0.00, 9999999.99)
        self.selling_input.setDecimals(2)
        sell_vbox.addWidget(self.selling_input)
        
        pricing_layout.addLayout(buy_vbox)
        pricing_layout.addLayout(sell_vbox)
        layout.addLayout(pricing_layout)

        layout.addWidget(QLabel("Current Core Quantity *"))
        self.qty_input = QSpinBox()
        self.qty_input.setRange(0, 9999999)
        layout.addWidget(self.qty_input)

        layout.addWidget(QLabel("Internal Status Matrix *"))
        self.status_combo = QComboBox()
        for status in ProductStatus:
            self.status_combo.addItem(status.value, status.name)
        layout.addWidget(self.status_combo)

        layout.addWidget(QLabel("Extended Contextual Description"))
        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(70)
        layout.addWidget(self.desc_input)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background-color: #edf2f7; color: #4a5568; border: none;")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Synchronize Records" if self.product_to_edit else "Save Entry Block")
        self.save_btn.setStyleSheet("background-color: #00adb5; color: white; border: none;")
        self.save_btn.clicked.connect(self.process_submission)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def populate_existing_data(self):
        if self.product_to_edit:
            self.name_input.setText(self.product_to_edit.name)
            self.barcode_input.setText(self.product_to_edit.barcode)
            self.buying_input.setValue(float(self.product_to_edit.buying_price))
            self.selling_input.setValue(float(self.product_to_edit.selling_price))
            self.qty_input.setValue(self.product_to_edit.quantity)
            self.desc_input.setPlainText(self.product_to_edit.description if self.product_to_edit.description else "")
            
            idx = self.status_combo.findText(self.product_to_edit.status.value)
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)

    def process_submission(self):
        try:
            if self.product_to_edit:
                self.product_service.update_product(
                    current_user=self.current_user,
                    product_id=self.product_to_edit.id,
                    name=self.name_input.text(),
                    barcode=self.barcode_input.text(),
                    buying_price=self.buying_input.value(),
                    selling_price=self.selling_input.value(),
                    quantity=self.qty_input.value(),
                    description=self.desc_input.toPlainText(),
                    status_value=self.status_combo.currentText()
                )
            else:
                self.product_service.create_product(
                    current_user=self.current_user,
                    name=self.name_input.text(),
                    barcode=self.barcode_input.text(),
                    buying_price=self.buying_input.value(),
                    selling_price=self.selling_input.value(),
                    quantity=self.qty_input.value(),
                    description=self.desc_input.toPlainText()
                )
            QMessageBox.information(self, "Success", "Product information synchronized cleanly.")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Execution Inhibited", str(e))


class ProductManagementView(QWidget):
    def __init__(self, current_user, db_session):
        super().__init__()
        self.current_user = current_user
        self.db_session = db_session  
        
        from app.repositories.product_repo import ProductRepository
        self.repo = ProductRepository(db_session)
        self.service = ProductService(self.repo)
        
        # Pagination State
        self.current_page = 1
        self.items_per_page = 25  # Set your desired items per page here
        self.total_pages = 1
        self.total_items = 0

        self.init_ui()
        self.reload_product_records()
        self.evaluate_security_clearance_locks()

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
            QPushButton#secondaryBtn:disabled { background-color: #f1f3f5; color: #a0aec0; border: 1px solid #e2e8f0; }
            QPushButton#inlineEditBtn { background-color: #00adb5; color: white; border: none; padding: 4px 12px; font-weight: bold; font-size: 11px; border-radius: 3px; min-height: 20px; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        top_bar = QHBoxLayout()
        title = QLabel("Inventory Catalog")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2b2d42;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.add_product_btn = QPushButton("+ New Product")
        self.add_product_btn.setObjectName("actionBtn")
        self.add_product_btn.clicked.connect(self.launch_creation_form)
        top_bar.addWidget(self.add_product_btn)

        self.export_excel_btn = QPushButton("Excel")
        self.export_excel_btn.setObjectName("secondaryBtn")
        self.export_excel_btn.clicked.connect(self.export_to_excel_format)
        top_bar.addWidget(self.export_excel_btn)

        self.export_pdf_btn = QPushButton("PDF")
        self.export_pdf_btn.setObjectName("secondaryBtn")
        self.export_pdf_btn.clicked.connect(self.export_to_pdf_format)
        top_bar.addWidget(self.export_pdf_btn)

        main_layout.addLayout(top_bar)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Live Search Matrix: Enter product name or scan physical barcode token...")
        
        # Reset to page 1 whenever search text changes
        self.search_input.textChanged.connect(self.reset_pagination_and_reload)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Item ID", "Barcode Scan", "Product Name", "Wholesale Cost", "Retail Out", "Stock Level", "Status Profile", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self.launch_edit_form_from_selection)
        
        main_layout.addWidget(self.table)

        # ==========================================
        # NEW: Pagination Controls Layout
        # ==========================================
        pagination_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("◄ Previous")
        self.prev_btn.setObjectName("secondaryBtn")
        self.prev_btn.clicked.connect(self.go_to_prev_page)
        
        self.page_info_label = QLabel("Page 1 of 1")
        self.page_info_label.setAlignment(Qt.AlignCenter)
        self.page_info_label.setStyleSheet("font-weight: bold; color: #4a5568;")
        
        self.next_btn = QPushButton("Next ►")
        self.next_btn.setObjectName("secondaryBtn")
        self.next_btn.clicked.connect(self.go_to_next_page)

        pagination_layout.addStretch()
        pagination_layout.addWidget(self.prev_btn)
        pagination_layout.addWidget(self.page_info_label)
        pagination_layout.addWidget(self.next_btn)
        pagination_layout.addStretch()
        
        main_layout.addLayout(pagination_layout)

    def has_mutation_privilege(self) -> bool:
        ALLOWED_MUTATION_ROLES = ["ADMIN", "STORE_MANAGER", "MANAGE_STOCK"]
        return self.current_user and self.current_user.role.role_name in ALLOWED_MUTATION_ROLES

    def evaluate_security_clearance_locks(self):
        if not self.has_mutation_privilege():
            self.add_product_btn.setVisible(False)
            self.add_product_btn.setEnabled(False)
            self.table.setColumnHidden(7, True)

    def showEvent(self, event):
        super().showEvent(event)
        self.reload_product_records()

    # ==========================================
    # NEW: Pagination Navigation Methods
    # ==========================================
    def reset_pagination_and_reload(self):
        self.current_page = 1
        self.reload_product_records()

    def go_to_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.reload_product_records()

    def go_to_next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.reload_product_records()

    def update_pagination_ui(self):
        """Updates the state of pagination labels and buttons."""
        self.page_info_label.setText(f"Page {self.current_page} of {self.total_pages} (Total: {self.total_items})")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)

    def reload_product_records(self):
        try:
            if self.db_session:
                self.db_session.expire_all()

            self.table.setRowCount(0)
            search_query = self.search_input.text()
            
            # Fetch all matching records 
            all_products = self.service.get_products_list(search_query)
            
            # Pagination Math
            self.total_items = len(all_products)
            self.total_pages = math.ceil(self.total_items / self.items_per_page)
            if self.total_pages == 0:
                self.total_pages = 1
                
            # Prevent out-of-bounds pages if data is deleted or heavily filtered
            if self.current_page > self.total_pages:
                self.current_page = self.total_pages

            # Slice the current page's data
            start_idx = (self.current_page - 1) * self.items_per_page
            end_idx = start_idx + self.items_per_page
            paged_products = all_products[start_idx:end_idx]

            self.update_pagination_ui()
            
            for row_idx, prod in enumerate(paged_products):
                self.table.insertRow(row_idx)
                
                id_item = QTableWidgetItem(str(prod.id))
                barcode_item = QTableWidgetItem(prod.barcode)
                name_item = QTableWidgetItem(prod.name)
                buy_item = QTableWidgetItem(f"${prod.buying_price:,.2f}")
                sell_item = QTableWidgetItem(f"${prod.selling_price:,.2f}")
                qty_item = QTableWidgetItem(str(prod.quantity))
                status_item = QTableWidgetItem(prod.status.value)
                
                id_item.setTextAlignment(Qt.AlignCenter)
                barcode_item.setTextAlignment(Qt.AlignCenter)
                qty_item.setTextAlignment(Qt.AlignCenter)
                status_item.setTextAlignment(Qt.AlignCenter)

                if prod.status.value == "ACTIVE":
                    status_item.setForeground(Qt.GlobalColor.darkGreen)
                else:
                    status_item.setForeground(Qt.GlobalColor.red)

                self.table.setItem(row_idx, 0, id_item)
                self.table.setItem(row_idx, 1, barcode_item)
                self.table.setItem(row_idx, 2, name_item)
                self.table.setItem(row_idx, 3, buy_item)
                self.table.setItem(row_idx, 4, sell_item)
                self.table.setItem(row_idx, 5, qty_item)
                self.table.setItem(row_idx, 6, status_item)

                if self.has_mutation_privilege():
                    action_container = QWidget()
                    action_layout = QHBoxLayout(action_container)
                    action_layout.setContentsMargins(0, 2, 0, 2)
                    action_layout.setAlignment(Qt.AlignCenter)

                    inline_edit_btn = QPushButton("Edit")
                    inline_edit_btn.setObjectName("inlineEditBtn")
                    inline_edit_btn.setCursor(Qt.PointingHandCursor)
                    inline_edit_btn.setProperty("target_product_id", prod.id)
                    inline_edit_btn.clicked.connect(self.handle_inline_edit_click)

                    action_layout.addWidget(inline_edit_btn)
                    self.table.setCellWidget(row_idx, 7, action_container)

        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Core Execution Fault", f"Data sync failure: {e}")

    def launch_creation_form(self):
        if not self.has_mutation_privilege():
            return
        dialog = ProductFormDialog(self, self.service, self.current_user)
        if dialog.exec() == QDialog.Accepted:
            self.reload_product_records()

    def handle_inline_edit_click(self):
        if not self.has_mutation_privilege():
            return
        button_sender = self.sender()
        if button_sender:
            target_id = button_sender.property("target_product_id")
            self.execute_modification_pipeline(target_id)

    def launch_edit_form_from_selection(self):
        if not self.has_mutation_privilege():
            return
            
        current_row = self.table.currentRow()
        if current_row < 0:
            return
            
        id_item = self.table.item(current_row, 0)
        if id_item:
            self.execute_modification_pipeline(int(id_item.text()))

    def execute_modification_pipeline(self, product_id: int):
        product_to_edit = self.repo.get_by_id(product_id)
        if product_to_edit:
            dialog = ProductFormDialog(self, self.service, self.current_user, product_to_edit=product_to_edit)
            if dialog.exec() == QDialog.Accepted:
                self.reload_product_records()

    def export_to_excel_format(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Inventory File Spreadsheet", "", "Excel CSV Formats (*.csv)")
        if not path:
            return

        try:
            products = self.service.get_products_list(self.search_input.text())
            with open(path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, dialect='excel')
                writer.writerow(["Internal ID", "Barcode Token", "Product Name", "Description", "Buying Cost", "Selling Price", "Quantity On Hand", "Status Context"])
                
                for p in products:
                    writer.writerow([p.id, p.barcode, p.name, p.description or "", p.buying_price, p.selling_price, p.quantity, p.status.value])
            
            QMessageBox.information(self, "Export Complete", "Data pipeline output generated cleanly in targeting output destination.")
        except Exception as e:
            QMessageBox.critical(self, "Export Failure", f"Unable to safely stream data pipeline to localized drive context: {e}")

    def export_to_pdf_format(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Document Report", "", "PDF Document Layout (*.pdf)")
        if not path:
            return

        try:
            products = self.service.get_products_list(self.search_input.text())
            
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
                    .right { text-align: right; }
                </style>
            </head>
            <body>
                <h2>SYSTEM INVENTORY STOCK VALUATION REPORT</h2>
                <div class="meta">Generated via Central Management Administration View Grid Context</div>
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Barcode</th>
                        <th>Product Name</th>
                        <th class="right">Wholesale Cost</th>
                        <th class="right">Retail Out</th>
                        <th class="center">Stock Qty</th>
                        <th class="center">Status</th>
                    </tr>
            """
            
            for p in products:
                html_content += f"""
                    <tr>
                        <td class="center">{p.id}</td>
                        <td class="center">{p.barcode}</td>
                        <td>{p.name}</td>
                        <td class="right">${p.buying_price:,.2f}</td>
                        <td class="right">${p.selling_price:,.2f}</td>
                        <td class="center">{p.quantity}</td>
                        <td class="center" style="color: {'green' if p.status.value == 'ACTIVE' else 'red'}; font-weight: bold;">{p.status.value}</td>
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
            writer.setResolution(96)
            writer.setPageLayout(QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait, QMarginsF(15, 15, 15, 15)))

            document.print_(writer)
            QMessageBox.information(self, "Export Complete", "PDF document output generated cleanly.")
            
        except Exception as e:
            QMessageBox.critical(self, "Export Failure", f"Unable to generate PDF document: {e}")