# app/ui/views/stocktake_management_view.py
import csv
import math
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QTableWidget, QTableWidgetItem, QHeaderView, 
                               QDialog, QLabel, QComboBox, QMessageBox, QLineEdit,
                               QAbstractItemView, QFileDialog, QSpinBox, QFormLayout)
from PySide6.QtCore import Qt, QMarginsF 
from PySide6.QtGui import QPdfWriter, QTextDocument, QPageLayout, QPageSize
from app.services.stocktake_service import StockTakeService
from app.models.schema import Product

class StockTakeFormDialog(QDialog):
    def __init__(self, parent, stocktake_service: StockTakeService, current_user, db_session):
        super().__init__(parent)
        self.stocktake_service = stocktake_service
        self.current_user = current_user
        self.db_session = db_session 
        
        self.setWindowTitle("Log New Inventory Reconciliation Entry")
        self.setMinimumWidth(480)
        self.init_ui()
        self.load_product_selections()
        self.adjustSize()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; color: #2b2d42; font-family: 'Segoe UI', Arial, sans-serif; }
            QComboBox, QSpinBox { border: 1px solid #ccd1d9; border-radius: 4px; padding: 8px; color: #2b2d42; background: #ffffff; font-size: 13px; }
            QComboBox:focus, QSpinBox:focus { border: 1px solid #00adb5; background-color: #fafafa; }
            QLabel { font-weight: bold; color: #4a5568; font-size: 13px; }
            QPushButton { border-radius: 4px; padding: 10px 15px; font-weight: bold; font-size: 13px; min-height: 20px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 25)
        layout.setSpacing(12)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignLeft)

        self.product_combo = QComboBox()
        self.product_combo.setMinimumWidth(260)
        self.product_combo.currentIndexChanged.connect(self.handle_product_changed)
        form_layout.addRow("Select Target Product *", self.product_combo)

        self.system_qty_lbl = QLabel("0")
        self.system_qty_lbl.setStyleSheet("font-weight: normal; font-size: 14px; color: #2d3748;")
        form_layout.addRow("Current System Book Quantity:", self.system_qty_lbl)

        self.actual_qty_input = QSpinBox()
        self.actual_qty_input.setRange(0, 9999999)
        self.actual_qty_input.valueChanged.connect(self.calculate_live_variance)
        form_layout.addRow("Physical Counted Stock *", self.actual_qty_input)

        self.variance_lbl = QLabel("0")
        self.variance_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        form_layout.addRow("Computed Discrepancy Variance:", self.variance_lbl)

        layout.addLayout(form_layout)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background-color: #edf2f7; color: #4a5568; border: none;")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Commit Audit Adjustment")
        self.save_btn.setStyleSheet("background-color: #00adb5; color: white; border: none;")
        self.save_btn.clicked.connect(self.process_submission)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def load_product_selections(self):
        try:
            products = self.stocktake_service.get_available_products(self.current_user)
            self.product_combo.addItem("-- Choose Catalog Entry Item --", None)
            for p in products:
                self.product_combo.addItem(f"{p.name} [{p.barcode}]", p.id)
        except Exception as e:
            QMessageBox.warning(self, "Lookup Fault", f"Unable to safely pull inventory tracking labels: {e}")

    def handle_product_changed(self, *args):
        product_id = self.product_combo.currentData()
        if product_id:
            product = self.db_session.query(Product).filter(Product.id == product_id).first()
            if product:
                self.system_qty_lbl.setText(str(product.quantity))
                self.calculate_live_variance()
        else:
            self.system_qty_lbl.setText("0")
            self.variance_lbl.setText("0")
            self.variance_lbl.setStyleSheet("font-weight: bold; color: #4a5568;")

    def calculate_live_variance(self, *args):
        try:
            sys_qty = int(self.system_qty_lbl.text())
            actual_qty = self.actual_qty_input.value()
            variance = actual_qty - sys_qty
            
            prefix = "+" if variance > 0 else ""
            self.variance_lbl.setText(f"{prefix}{variance} units")
            
            if variance < 0:
                self.variance_lbl.setStyleSheet("font-weight: bold; color: #e53e3e; font-size: 14px;")
            elif variance > 0:
                self.variance_lbl.setStyleSheet("font-weight: bold; color: #38a169; font-size: 14px;")
            else:
                self.variance_lbl.setStyleSheet("font-weight: bold; color: #4a5568; font-size: 14px;")
        except ValueError:
            pass

    def process_submission(self):
        product_id = self.product_combo.currentData()
        if not product_id:
            QMessageBox.warning(self, "Validation Error", "Please select a target product to proceed with the stock take audit.")
            return

        try:
            self.stocktake_service.execute_stocktake(
                current_user=self.current_user,
                product_id=product_id,
                actual_quantity=self.actual_qty_input.value()
            )
            QMessageBox.information(self, "Audit Finalized", "Stock take recorded. The system inventory ledger has updated successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Execution Fault", str(e))


class StockTakeManagementView(QWidget):
    def __init__(self, current_user, db_session):
        super().__init__()
        self.current_user = current_user
        self.db_session = db_session
        from app.repositories.stocktake_repo import StockTakeRepository
        self.repo = StockTakeRepository(self.db_session)
        self.service = StockTakeService(self.repo)
        
        # Pagination State
        self.current_page = 1
        self.items_per_page = 30
        self.total_pages = 1

        self.init_ui()
        self.reload_audit_records()

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
            QPushButton#paginationBtn { background-color: #ffffff; color: #4a5568; border: 1px solid #ccd1d9; font-weight: bold; padding: 6px 12px; border-radius: 4px; }
            QPushButton#paginationBtn:hover { background-color: #edf2f7; }
            QPushButton#paginationBtn:disabled { background-color: #f1f3f5; color: #adb5bd; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Top Bar
        top_bar = QHBoxLayout()
        title = QLabel("Stock Take")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2b2d42;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.add_audit_btn = QPushButton("+ Stock Take")
        self.add_audit_btn.setObjectName("actionBtn")
        self.add_audit_btn.clicked.connect(self.launch_audit_form)
        top_bar.addWidget(self.add_audit_btn)

        self.export_excel_btn = QPushButton("Excel CSV")
        self.export_excel_btn.setObjectName("secondaryBtn")
        self.export_excel_btn.clicked.connect(self.export_to_excel_format)
        top_bar.addWidget(self.export_excel_btn)

        self.export_pdf_btn = QPushButton("PDF")
        self.export_pdf_btn.setObjectName("secondaryBtn")
        self.export_pdf_btn.clicked.connect(self.export_to_pdf_format)
        top_bar.addWidget(self.export_pdf_btn)

        main_layout.addLayout(top_bar)

        # Search Bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Audit Ledger: Type product identity nomenclature here for dynamic filtration filters...")
        self.search_input.textChanged.connect(self.on_filter_changed)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)

        # Data Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Audit Session ID", "Product Name", "Expected Book Qty", "Physical Count Qty", "Variance Offset", "Verified By", "Execution Date"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        main_layout.addWidget(self.table)

        # Pagination Controls
        pagination_layout = QHBoxLayout()
        self.prev_btn = QPushButton("<< Previous")
        self.prev_btn.setObjectName("paginationBtn")
        self.prev_btn.clicked.connect(self.prev_page)
        
        self.page_label = QLabel("Page 1 of 1")
        self.page_label.setStyleSheet("font-weight: bold; color: #4a5568;")
        self.page_label.setAlignment(Qt.AlignCenter)
        
        self.next_btn = QPushButton("Next >>")
        self.next_btn.setObjectName("paginationBtn")
        self.next_btn.clicked.connect(self.next_page)
        
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.prev_btn)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_btn)
        pagination_layout.addStretch()
        
        main_layout.addLayout(pagination_layout)

    def on_filter_changed(self):
        self.current_page = 1
        self.reload_audit_records()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.reload_audit_records()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.reload_audit_records()

    def reload_audit_records(self, *args):
        try:
            self.table.setRowCount(0)
            search_query = self.search_input.text()
            
            # Retrieve pagination counts
            total_records = self.service.get_total_count(self.current_user, search_query)
            self.total_pages = max(1, math.ceil(total_records / self.items_per_page))
            
            # Update Pagination UI
            self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
            self.prev_btn.setEnabled(self.current_page > 1)
            self.next_btn.setEnabled(self.current_page < self.total_pages)

            # Fetch Sliced Data
            records = self.service.get_stocktakes_paginated(
                current_user=self.current_user,
                search_query=search_query, 
                limit=self.items_per_page, 
                offset=(self.current_page - 1) * self.items_per_page
            )
            
            for row_idx, rec in enumerate(records):
                self.table.insertRow(row_idx)
                
                id_item = QTableWidgetItem(str(rec.id))
                prod_item = QTableWidgetItem(rec.product.name if rec.product else "Deleted Product")
                sys_item = QTableWidgetItem(str(rec.quantity))
                act_item = QTableWidgetItem(str(rec.actual_quantity))
                
                prefix = "+" if rec.difference > 0 else ""
                diff_item = QTableWidgetItem(f"{prefix}{rec.difference}")
                user_item = QTableWidgetItem(rec.user.name if rec.user else "System Space")
                
                date_str = rec.stocktake_date.strftime("%Y-%m-%d %H:%M") if rec.stocktake_date else "N/A"
                date_item = QTableWidgetItem(date_str)
                
                id_item.setTextAlignment(Qt.AlignCenter)
                sys_item.setTextAlignment(Qt.AlignCenter)
                act_item.setTextAlignment(Qt.AlignCenter)
                diff_item.setTextAlignment(Qt.AlignCenter)
                date_item.setTextAlignment(Qt.AlignCenter)

                if rec.difference < 0:
                    diff_item.setForeground(Qt.GlobalColor.red)
                elif rec.difference > 0:
                    diff_item.setForeground(Qt.GlobalColor.darkGreen)

                self.table.setItem(row_idx, 0, id_item)
                self.table.setItem(row_idx, 1, prod_item)
                self.table.setItem(row_idx, 2, sys_item)
                self.table.setItem(row_idx, 3, act_item)
                self.table.setItem(row_idx, 4, diff_item)
                self.table.setItem(row_idx, 5, user_item)
                self.table.setItem(row_idx, 6, date_item)

        except Exception as e:
            QMessageBox.critical(self, "Core Sync Failure", f"Unable to display log sequences: {e}")

    def launch_audit_form(self, *args):
        dialog = StockTakeFormDialog(self, self.service, self.current_user, self.db_session)
        if dialog.exec() == QDialog.Accepted:
            self.reload_audit_records()

    def export_to_excel_format(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Stock Take Ledger", "", "Excel CSV Formats (*.csv)")
        if not path:
            return

        try:
            records = self.service.get_stocktakes_list(self.current_user, self.search_input.text())
            with open(path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, dialect='excel')
                writer.writerow(["Session ID", "Product Identity", "Expected Book Quantity", "Physical Counted Quantity", "Variance Offset", "Auditor Worker Target", "Timestamp"])
                
                for r in records:
                    date_str = r.stocktake_date.strftime("%Y-%m-%d %H:%M") if r.stocktake_date else ""
                    writer.writerow([r.id, r.product.name if r.product else "", r.quantity, r.actual_quantity, r.difference, r.user.name if r.user else "", date_str])
            
            QMessageBox.information(self, "Export Complete", "Audit tracking extraction files generated successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Export Failure", f"Unable to safely stream data output files: {e}")

    def export_to_pdf_format(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Stock Audit Layout", "", "PDF Document Layout (*.pdf)")
        if not path:
            return

        try:
            records = self.service.get_stocktakes_list(self.current_user, self.search_input.text())
            
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
                <h2>SYSTEM CORE STOCK TAKE AUDIT VALUATION JOURNAL</h2>
                <div class="meta">Generated via Central Management Administration View Grid Context</div>
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Product Context Item</th>
                        <th class="center">Expected Book Qty</th>
                        <th class="center">Physical Count</th>
                        <th class="center">Variance Balance</th>
                        <th>Verified Auditor</th>
                        <th class="center">Execution Date</th>
                    </tr>
            """
            
            for r in records:
                date_str = r.stocktake_date.strftime("%Y-%m-%d %H:%M") if r.stocktake_date else "N/A"
                prefix = "+" if r.difference > 0 else ""
                html_content += f"""
                    <tr>
                        <td class="center">{r.id}</td>
                        <td style="font-weight: bold;">{r.product.name if r.product else 'Deleted Product'}</td>
                        <td class="center">{r.quantity}</td>
                        <td class="center">{r.actual_quantity}</td>
                        <td class="center" style="color: {'green' if r.difference >= 0 else 'red'}; font-weight: bold;">{prefix}{r.difference}</td>
                        <td>{r.user.name if r.user else 'System Space'}</td>
                        <td class="center">{date_str}</td>
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
            QMessageBox.information(self, "Export Complete", "Vector audit ledger output sheets generated cleanly.")
        except Exception as e:
            QMessageBox.critical(self, "Export Failure", f"Unable to finalize vector layout pipelines: {e}")