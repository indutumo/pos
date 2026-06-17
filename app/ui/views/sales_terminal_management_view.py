# app/ui/views/sales_terminal_management_view.py
import enum
from datetime import datetime
from decimal import Decimal

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
                             QDialog, QLabel, QComboBox, QMessageBox, QLineEdit,
                             QAbstractItemView, QSpinBox, QDoubleSpinBox, QFormLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintDialog

from app.repositories.sales_repo import SalesRepository
from app.services.sales_service import SalesService
from app.models.schema import Product, Customer, Payment, PaymentMethod 

# ====================================================================
# Printer Helper Function
# ====================================================================
def print_thermal_receipt(parent_widget, receipt_obj):
    """Generates an HTML document optimized for a thermal printer and triggers the print dialog."""
    
    # Organization Details (Configure as needed)
    org_name = "Zola POS Terminal"
    org_location = "Nairobi, Kenya"
    org_mobile = "+254 700 000 000"
    
    date_str = receipt_obj.receipt_date.strftime('%Y-%m-%d %H:%M') if receipt_obj.receipt_date else "N/A"
    customer_name = receipt_obj.customer.name if receipt_obj.customer else "Walk-in Guest"
    cashier_name = receipt_obj.user.name if receipt_obj.user else "System"

    # Build the HTML template for the receipt
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: monospace; font-size: 10pt; color: #000; margin: 0; padding: 0; }}
            .center {{ text-align: center; }}
            .left {{ text-align: left; }}
            .right {{ text-align: right; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ padding: 4px 0; border-bottom: 1px dashed #000; }}
            h2 {{ margin: 5px 0; font-size: 14pt; }}
            p {{ margin: 3px 0; }}
            .divider {{ border-top: 1px dashed #000; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="center">
            <h2>{org_name}</h2>
            <p>{org_location}</p>
            <p>Tel: {org_mobile}</p>
        </div>
        <div class="divider"></div>
        <div class="left">
            <p><b>Receipt #:</b> {receipt_obj.receipt_number}</p>
            <p><b>Date:</b> {date_str}</p>
            <p><b>Cashier:</b> {cashier_name}</p>
            <p><b>Customer:</b> {customer_name}</p>
        </div>
        <table>
            <tr>
                <th class="left">Item</th>
                <th class="center">Qty</th>
                <th class="right">Price</th>
                <th class="right">Total</th>
            </tr>
    """

    # Append items
    for sale in receipt_obj.sales:
        item_name = sale.product.name if sale.product else "Deleted Item"
        subtotal = sale.quantity * sale.price
        html += f"""
            <tr>
                <td class="left">{item_name}</td>
                <td class="center">{sale.quantity}</td>
                <td class="right">${sale.price:.2f}</td>
                <td class="right">${subtotal:.2f}</td>
            </tr>
        """

    # Append totals
    html += f"""
        </table>
        <br>
        <div class="right">
            <h3>Total: ${receipt_obj.total:.2f}</h3>
            <h3>Paid: ${receipt_obj.paid_amount:.2f}</h3>
        </div>
        <div class="divider"></div>
        <div class="center">
            <p>Thank you for your business!</p>
        </div>
    </body>
    </html>
    """

    document = QTextDocument()
    document.setHtml(html)

    # Configure the printer
    printer = QPrinter(QPrinter.HighResolution)
    # Most thermal printers run continuously, so setting it to default layout lets the driver handle the roll
    
    dialog = QPrintDialog(printer, parent_widget)
    dialog.setWindowTitle("Print Receipt")
    
    if dialog.exec() == QDialog.Accepted:
        document.print_(printer)


class ReceiptDetailsDialog(QDialog):
    """Inspects targeted line-item rows mapped inside individual BillReceipt records."""
    def __init__(self, parent, receipt_obj):
        super().__init__(parent)
        self.receipt_obj = receipt_obj
        self.setWindowTitle(f"Invoice breakdown: {receipt_obj.receipt_number}")
        self.setMinimumSize(600, 450)
        
        layout = QVBoxLayout(self)
        
        meta_lbl = QLabel(
            f"<b>Receipt Token:</b> {receipt_obj.receipt_number}<br>"
            f"<b>Date:</b> {receipt_obj.receipt_date.strftime('%Y-%m-%d %H:%M')}<br>"
            f"<b>Cashier Account:</b> {receipt_obj.user.name if receipt_obj.user else 'System'}<br>"
            f"<b>Client Profile:</b> {receipt_obj.customer.name if receipt_obj.customer else 'Walk-in Guest'}<br>"
            f"<b>Status Condition:</b> <font color='blue'>{receipt_obj.status.value}</font>"
        )
        meta_lbl.setStyleSheet("font-size: 13px; line-height: 140%; padding: 5px;")
        layout.addWidget(meta_lbl)

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Product Item Description", "Unit Sold Price", "Quantity Ordered", "Subtotal Calculation"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        table.setRowCount(len(receipt_obj.sales))
        for idx, sale in enumerate(receipt_obj.sales):
            sub = sale.quantity * sale.price
            table.setItem(idx, 0, QTableWidgetItem(sale.product.name if sale.product else "Deleted Entry"))
            table.setItem(idx, 1, QTableWidgetItem(f"${sale.price:.2f}"))
            table.setItem(idx, 2, QTableWidgetItem(str(sale.quantity)))
            table.setItem(idx, 3, QTableWidgetItem(f"${sub:.2f}"))
            
        layout.addWidget(table)
        
        summary_lbl = QLabel(f"<h3>Grand Total: ${receipt_obj.total:.2f} | Tendered Paid: ${receipt_obj.paid_amount:.2f}</h3>")
        summary_lbl.setAlignment(Qt.AlignRight)
        layout.addWidget(summary_lbl)

        # Action Buttons Box
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.print_btn = QPushButton("Print Thermal Receipt")
        self.print_btn.setStyleSheet("background: #00adb5; color: white; padding: 6px 12px; font-weight: bold;")
        self.print_btn.clicked.connect(self.trigger_print)
        btn_box.addWidget(self.print_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_box.addWidget(close_btn)

        layout.addLayout(btn_box)

    def trigger_print(self):
        print_thermal_receipt(self, self.receipt_obj)


# ====================================================================
# Advanced Split-Payment Ledger Engine & Dynamic Dialog
# ====================================================================
class PaymentProcessingDialog(QDialog):
    def __init__(self, parent, grand_total: Decimal):
        super().__init__(parent)
        self.setWindowTitle("Split-Payment Processing Terminal")
        self.setMinimumSize(500, 400)
        
        self.total_required = grand_total
        self.running_balance = grand_total
        self.payments_staged = []  # List of accumulated payment dictionaries
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Summary Header Banner Status Indicators
        self.summary_box = QHBoxLayout()
        self.total_lbl = QLabel(f"<b>Total Order:</b> ${self.total_required:.2f}")
        self.balance_lbl = QLabel(f"<b>Remaining Balance:</b> ${self.running_balance:.2f}")
        self.balance_lbl.setStyleSheet("color: #e63946; font-size: 14px; font-weight: bold;")
        self.summary_box.addWidget(self.total_lbl)
        self.summary_box.addWidget(self.balance_lbl)
        layout.addLayout(self.summary_box)
        
        # Action Transaction Inputs Box
        form = QFormLayout()
        self.method_combo = QComboBox()
        for method in PaymentMethod:
            self.method_combo.addItem(method.value, method)
        self.method_combo.currentIndexChanged.connect(self.handle_method_context_switch)
        form.addRow("Payment Method Used:", self.method_combo)
        
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0.01, 999999.99)
        self.amount_input.setValue(float(self.running_balance))
        self.amount_input.setPrefix("$ ")
        form.addRow("Amount Collected:", self.amount_input)
        
        self.add_payment_btn = QPushButton("Register Payment Slice")
        self.add_payment_btn.setStyleSheet("background: #00adb5; color: white;")
        self.add_payment_btn.clicked.connect(self.stage_payment_slice)
        form.addRow(self.add_payment_btn)
        layout.addLayout(form)
        
        # Currently Collected Installment Slices Grid View 
        layout.addWidget(QLabel("<b>Staged Payment Sub-Entries:</b>"))
        self.staged_table = QTableWidget(0, 4)
        self.staged_table.setHorizontalHeaderLabels(["Method Channel", "Amount Paid", "Invoice Balance", "Cash Change"])
        self.staged_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.staged_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.staged_table)
        
        # Close Window Execution Buttons Block
        btn_box = QHBoxLayout()
        cancel_btn = QPushButton("Abort Order")
        cancel_btn.clicked.connect(self.reject)
        
        self.commit_btn = QPushButton("Complete & Close BillReceipt")
        self.commit_btn.setEnabled(False)  # Disabled until remaining balance hits zero
        self.commit_btn.setStyleSheet("background: #38a169; color: white; font-weight: bold;")
        self.commit_btn.clicked.connect(self.accept)
        
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(self.commit_btn)
        layout.addLayout(btn_box)

    def handle_method_context_switch(self):
        # Auto-adjust expected collection inputs to fit current remaining balance constraints
        if self.running_balance > 0:
            self.amount_input.setValue(float(self.running_balance))

    def stage_payment_slice(self):
        chosen_method = self.method_combo.currentData()
        collected = Decimal(str(self.amount_input.value()))
        
        if collected <= 0:
            return
            
        change_returned = Decimal("0.00")
        calculated_balance = self.running_balance - collected
        
        # CASH rules: Extra money turns into physical cash change back to the client
        if chosen_method == PaymentMethod.CASH and calculated_balance < 0:
            change_returned = abs(calculated_balance)
            calculated_balance = Decimal("0.00")
            
        # Digital banking routes (BANK, MOBILE_MONEY) do not dispense change directly
        elif chosen_method in (PaymentMethod.BANK, PaymentMethod.MOBILE_MONEY) and calculated_balance < 0:
            QMessageBox.warning(self, "Transaction Bound Exception", 
                                "Digital payments cannot exceed the exact remaining invoice balance due.")
            return
            
        self.running_balance = calculated_balance
        
        # Log this specific step transaction block safely
        self.payments_staged.append({
            'method': chosen_method,
            'amount': collected - change_returned if calculated_balance == 0 else collected,
            'balance': self.running_balance,
            'change': change_returned
        })
        
        # Redraw dialog status arrays
        self.refresh_staged_grid()
        self.balance_lbl.setText(f"<b>Remaining Balance:</b> ${self.running_balance:.2f}")
        
        if self.running_balance <= 0:
            self.balance_lbl.setStyleSheet("color: #2a9d8f; font-size: 14px; font-weight: bold;")
            self.balance_lbl.setText("<b>Invoice Paid In Full</b>")
            self.commit_btn.setEnabled(True)
            self.add_payment_btn.setEnabled(False)
        else:
            self.amount_input.setValue(float(self.running_balance))

    def refresh_staged_grid(self):
        self.staged_table.setRowCount(0)
        for idx, p in enumerate(self.payments_staged):
            self.staged_table.insertRow(idx)
            self.staged_table.setItem(idx, 0, QTableWidgetItem(p['method'].value))
            self.staged_table.setItem(idx, 1, QTableWidgetItem(f"${p['amount']:.2f}"))
            self.staged_table.setItem(idx, 2, QTableWidgetItem(f"${p['balance']:.2f}"))
            self.staged_table.setItem(idx, 3, QTableWidgetItem(f"${p['change']:.2f}"))


class SalesTerminalManagementView(QWidget):
    def __init__(self, current_user, db_session):
        super().__init__()
        self.current_user = current_user
        self.db_session = db_session
        self.repo = SalesRepository(self.db_session)
        self.service = SalesService(self.repo)
        self.active_cart = [] 

        self.init_ui()
        self.reload_terminal_combos()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8f9fa; font-family: 'Segoe UI', Arial; color: #2b2d42; }
            QTableWidget { background-color: #ffffff; border: 1px solid #e1e4e8; border-radius: 4px; }
            QHeaderView::section { background-color: #edf2f7; font-weight: bold; padding: 6px; }
            QPushButton { border-radius: 4px; font-weight: bold; padding: 8px 12px; }
            QLineEdit, QComboBox, QDoubleSpinBox { border: 1px solid #ccd1d9; padding: 6px; border-radius: 4px; background: white; }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #00adb5; }
        """)

        master_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        self.build_pos_terminal_tab()
        self.build_receipt_registry_tab()
        self.build_flat_sales_tab()
        self.build_payments_ledger_tab()  
        
        master_layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self.handle_tab_switches)

    def build_pos_terminal_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        
        left_pane = QVBoxLayout()
        form = QFormLayout()
        
        self.cust_combo = QComboBox()
        form.addRow("Target Client Profile:", self.cust_combo)
        
        self.barcode_scan_input = QLineEdit()
        self.barcode_scan_input.setPlaceholderText("Scan barcode here for instant cart addition...")
        self.barcode_scan_input.returnPressed.connect(self.handle_instant_barcode_scan)
        form.addRow("Barcode Quick Scan:", self.barcode_scan_input)
        
        self.prod_combo = QComboBox()
        self.prod_combo.setEditable(True)
        self.prod_combo.setInsertPolicy(QComboBox.NoInsert)
        if self.prod_combo.completer():
            self.prod_combo.completer().setFilterMode(Qt.MatchContains)
            self.prod_combo.completer().setCaseSensitivity(Qt.CaseInsensitive)
            
        form.addRow("Search / Add Item:", self.prod_combo)
        
        self.qty_input = QSpinBox()
        self.qty_input.setRange(1, 9999)
        form.addRow("Item Execution Quantity:", self.qty_input)
        
        add_cart_btn = QPushButton("Append Item to Cart Ledger")
        add_cart_btn.setStyleSheet("background: #00adb5; color: white;")
        add_cart_btn.clicked.connect(self.add_item_to_cart_cache)
        
        left_pane.addLayout(form)
        left_pane.addWidget(add_cart_btn)
        left_pane.addStretch()
        
        right_pane = QVBoxLayout()
        right_pane.addWidget(QLabel("<b>Active Staged Cart Rows (Double click Price or Qty to edit):</b>"))
        
        self.cart_table = QTableWidget(0, 4)
        self.cart_table.setHorizontalHeaderLabels(["Item Identity", "Selling Price ($)", "Qty", "Total"])
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cart_table.cellChanged.connect(self.handle_cart_cell_changed)
        
        right_pane.addWidget(self.cart_table)
        
        checkout_box = QHBoxLayout()
        self.running_total_lbl = QLabel("Total: $0.00")
        self.running_total_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        commit_btn = QPushButton("Finalize Terminal Receipt")
        commit_btn.setStyleSheet("background: #38a169; color: white; font-size: 14px; padding: 10px 20px;")
        commit_btn.clicked.connect(self.execute_cart_checkout)
        
        checkout_box.addWidget(self.running_total_lbl)
        checkout_box.addStretch()
        checkout_box.addWidget(commit_btn)
        right_pane.addLayout(checkout_box)
        
        layout.addLayout(left_pane, 1)
        layout.addLayout(right_pane, 2)
        self.tabs.addTab(page, "Sales POS")

    def build_receipt_registry_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        search_box = QHBoxLayout()
        self.receipt_search = QLineEdit()
        self.receipt_search.setPlaceholderText("Filter receipts by invoice unique number token or customer name string elements...")
        self.receipt_search.textChanged.connect(self.refresh_receipts_register)
        search_box.addWidget(self.receipt_search)
        layout.addLayout(search_box)
        
        self.receipt_table = QTableWidget(0, 6)
        self.receipt_table.setHorizontalHeaderLabels(["Invoice Code Token", "Client Mapping", "Grand Valuation", "Tendered Value", "Condition State", "Created Timestamp"])
        self.receipt_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.receipt_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.receipt_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.receipt_table.doubleClicked.connect(self.inspect_selected_receipt)
        
        layout.addWidget(self.receipt_table)
        self.tabs.addTab(page, "Receipt List")

    def build_flat_sales_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        search_box = QHBoxLayout()
        self.sales_search = QLineEdit()
        self.sales_search.setPlaceholderText("Filter item logs by direct matching item definitions...")
        self.sales_search.textChanged.connect(self.refresh_sales_history)
        search_box.addWidget(self.sales_search)
        layout.addLayout(search_box)
        
        self.sales_table = QTableWidget(0, 5)
        self.sales_table.setHorizontalHeaderLabels(["Item Identity Name", "Unit Transaction Price", "Quantity Transacted", "Operator Counter User", "Date Captured"])
        self.sales_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sales_table.setEditTriggers(QAbstractItemView.NoEditTriggers) 
        
        layout.addWidget(self.sales_table)
        self.tabs.addTab(page, "Sales List")

    def build_payments_ledger_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        info_banner = QLabel("<b>Global Payments Activity Log</b> (Accessible by all operational profiles)")
        info_banner.setStyleSheet("color: #555; font-size: 12px; padding: 2px;")
        layout.addWidget(info_banner)
        
        self.payments_table = QTableWidget(0, 7)
        self.payments_table.setHorizontalHeaderLabels([
            "Payment ID", "Receipt Number", "Method Channel", 
            "Amount Received", "Remaining Balance", "Change Handed", "Processed Date"
        ])
        self.payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.payments_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        layout.addWidget(self.payments_table)
        self.tabs.addTab(page, "Payments List")

    def handle_tab_switches(self, idx):
        if idx == 0:
            self.reload_terminal_combos()
        elif idx == 1:
            self.refresh_receipts_register()
        elif idx == 2:
            self.refresh_sales_history()
        elif idx == 3:
            self.refresh_payments_ledger()

    def reload_terminal_combos(self):
        self.prod_combo.clear()
        self.cust_combo.clear()
        
        self.cust_combo.addItem("Anonymous Walk-in Customer Guest Account", 0)
        try:
            for c in self.db_session.query(Customer).order_by(Customer.name.asc()).all():
                self.cust_combo.addItem(c.name, c.id)
                
            active_products = self.db_session.query(Product).filter(Product.status == "ACTIVE").order_by(Product.name.asc()).all()
            
            for p in active_products:
                product_price = getattr(p, 'selling_price', 0.00)
                price_display = float(product_price) if product_price is not None else 0.00
                
                self.prod_combo.addItem(
                    f"{p.name} [BC: {p.barcode}] (Stock: {p.quantity} | ${price_display:.2f})", 
                    p.id
                )
            self.prod_combo.setCurrentIndex(-1)
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.warning(self, "Pipeline Error", f"Sync fail context error parsing configuration metadata frames: {e}")

    def handle_instant_barcode_scan(self):
        scanned_token = self.barcode_scan_input.text().strip()
        if not scanned_token:
            return
            
        try:
            product = self.db_session.query(Product).filter(
                Product.barcode == scanned_token, 
                Product.status == "ACTIVE"
            ).first()
            
            if not product:
                QMessageBox.warning(self, "Item Missing", f"No active catalog item matches barcode token: '{scanned_token}'")
                self.barcode_scan_input.clear()
                return
                
            scan_qty = self.qty_input.value()
            if scan_qty > product.quantity:
                QMessageBox.warning(self, "Stock Shortage", f"Cannot allocate {scan_qty} items. Only {product.quantity} units are available.")
                self.barcode_scan_input.clear()
                return

            for cached_item in self.active_cart:
                if cached_item['product_id'] == product.id:
                    if (cached_item['qty'] + scan_qty) > product.quantity:
                        QMessageBox.warning(self, "Stock Violation", "Combined allocation quantities breach system stock bounds.")
                        self.barcode_scan_input.clear()
                        return
                    cached_item['qty'] += scan_qty
                    self.redraw_cart_table()
                    self.barcode_scan_input.clear()
                    return

            resolved_price = getattr(product, 'selling_price', 0.00)
            self.active_cart.append({
                'product_id': product.id,
                'name': product.name,
                'qty': scan_qty,
                'unit_price': float(resolved_price) if resolved_price is not None else 0.00
            })
            self.redraw_cart_table()
            self.barcode_scan_input.clear()
            
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Scan Processing Error", f"Error querying hardware scanning pipelines: {e}")

    def add_item_to_cart_cache(self, *args):
        target_idx = self.prod_combo.currentIndex()
        if target_idx < 0:
            QMessageBox.warning(self, "Selection Missing", "Please select a valid product entry item from the list before attempting addition.")
            return
            
        p_id = self.prod_combo.itemData(target_idx)
        product = self.db_session.query(Product).filter(Product.id == p_id).first()
        qty = self.qty_input.value()
        
        if not product:
            return
            
        if qty > product.quantity:
            QMessageBox.warning(self, "Stock Limit Exception", f"Cannot order {qty} units. Only {product.quantity} components exist inside matching tracking configurations.")
            return

        for cached_item in self.active_cart:
            if cached_item['product_id'] == p_id:
                if (cached_item['qty'] + qty) > product.quantity:
                    QMessageBox.warning(self, "Stock Boundary Violation", "Accumulated loop requests exceed localized core component parameters.")
                    return
                cached_item['qty'] += qty
                self.redraw_cart_table()
                return

        resolved_price = getattr(product, 'selling_price', 0.00)
        self.active_cart.append({
            'product_id': p_id,
            'name': product.name,
            'qty': qty,
            'unit_price': float(resolved_price) if resolved_price is not None else 0.00
        })
        self.redraw_cart_table()

    def handle_cart_cell_changed(self, row, column):
        if column not in (1, 2):  
            return
            
        ui_item = self.cart_table.item(row, column)
        if not ui_item:
            return
            
        cart_item = self.active_cart[row]

        if column == 1:
            try:
                clean_text = ui_item.text().replace('$', '').strip()
                new_price = float(clean_text)
                if new_price < 0:
                    raise ValueError()
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Selling price must be a valid non-negative float value.")
                self.redraw_cart_table()
                return
                
            cart_item['unit_price'] = new_price
            self.redraw_cart_table()

        elif column == 2:
            try:
                new_qty = int(ui_item.text().strip())
                if new_qty <= 0:
                    raise ValueError()
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Quantity ordered must be a valid non-zero integer.")
                self.redraw_cart_table()
                return

            p_id = cart_item['product_id']
            product = self.db_session.query(Product).filter(Product.id == p_id).first()
            if product and new_qty > product.quantity:
                QMessageBox.warning(self, "Stock Boundary Violation", f"Cannot adjust to {new_qty} units. Only {product.quantity} components exist in stock.")
                self.redraw_cart_table()
                return
                
            cart_item['qty'] = new_qty
            self.redraw_cart_table()

    def redraw_cart_table(self):
        self.cart_table.blockSignals(True)
        self.cart_table.setRowCount(0)
        accumulated_total = Decimal('0.00')
        
        for idx, item in enumerate(self.active_cart):
            self.cart_table.insertRow(idx)
            sub = Decimal(str(item['qty'])) * Decimal(str(item['unit_price']))
            accumulated_total += sub
            
            name_cell = QTableWidgetItem(item['name'])
            name_cell.setFlags(name_cell.flags() & ~Qt.ItemIsEditable) 
            
            price_cell = QTableWidgetItem(f"{item['unit_price']:.2f}")
            price_cell.setFlags(price_cell.flags() | Qt.ItemIsEditable) 
            
            qty_cell = QTableWidgetItem(str(item['qty']))
            qty_cell.setFlags(qty_cell.flags() | Qt.ItemIsEditable) 
            
            total_cell = QTableWidgetItem(f"${sub:.2f}")
            total_cell.setFlags(total_cell.flags() & ~Qt.ItemIsEditable) 
            
            self.cart_table.setItem(idx, 0, name_cell)
            self.cart_table.setItem(idx, 1, price_cell)
            self.cart_table.setItem(idx, 2, qty_cell)
            self.cart_table.setItem(idx, 3, total_cell)
            
        self.running_total_lbl.setText(f"Total: ${accumulated_total:.2f}")
        self.cart_table.blockSignals(False) 

    # ====================================================================
    # FIXED: Split Payment Transaction Execution & Model Injection
    # ====================================================================
    def execute_cart_checkout(self, *args):
        if not self.active_cart:
            QMessageBox.warning(self, "Processing Halting", "Staging array queue contains zero items. Operation aborted.")
            return

        grand_total = Decimal('0.00')
        for item in self.active_cart:
            grand_total += Decimal(str(item['qty'])) * Decimal(str(item['unit_price']))

        # 1. Trigger split-payment dialog validation
        pmt_dialog = PaymentProcessingDialog(self, grand_total)
        if pmt_dialog.exec() != QDialog.Accepted:
            return  # Abandon payment window exit path

        c_id = self.cust_combo.currentData()
        
        try:
            # 2. Complete order structure creation inside core service tier 
            # We initialize total tendered as matching order grand total valuation
            receipt_obj = self.service.checkout_cart(
                current_user=self.current_user,
                customer_id=c_id,
                cart_items=self.active_cart,
                paid_amount=float(grand_total)
            )
            
            receipt_id = receipt_obj.id if hasattr(receipt_obj, 'id') else receipt_obj
            
            # 3. Iteratively write all payment installments out to the database session
            for p_slice in pmt_dialog.payments_staged:
                payment_record = Payment(
                    receipt_id=receipt_id,
                    amount=p_slice['amount'],
                    balance=p_slice['balance'],
                    change_amount=p_slice['change'],
                    payment_method=p_slice['method'],
                    user_id=self.current_user.id,
                    payment_date=datetime.utcnow()
                )
                self.db_session.add(payment_record)
            
            # 4. CRITICAL INJECTION: Process the active shift changes before committing
            self.service.process_shift_aggregation(self.db_session, self.current_user.id, pmt_dialog.payments_staged)
            
            # 5. Commit everything atomically (payments and shift modifications)
            self.db_session.commit()
            
            QMessageBox.information(self, "Order Finalized", "All split-payment options validated. Bill Receipt completed successfully.")
            
            # 6. Ask the user if they want to print the receipt now
            full_receipt_obj = self.db_session.query(type(receipt_obj)).filter_by(id=receipt_id).first()
            if full_receipt_obj:
                reply = QMessageBox.question(
                    self, 'Print Receipt', 
                    'Would you like to print the receipt now?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    print_thermal_receipt(self, full_receipt_obj)
            
            self.active_cart = []
            self.redraw_cart_table()
            self.reload_terminal_combos()
            self.barcode_scan_input.setFocus()
            
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Database Constraint Fault", f"Execution error modifying structural tables: {e}")

    def refresh_receipts_register(self, *args):
        self.receipt_table.setRowCount(0)
        query_str = self.receipt_search.text()
        try:
            records = self.service.get_receipts_ledger(query_str)
            for r_idx, rec in enumerate(records):
                self.receipt_table.insertRow(r_idx)
                
                inv_item = QTableWidgetItem(rec.receipt_number)
                inv_item.setData(Qt.UserRole, rec.id)
                
                client_str = rec.customer.name if rec.customer else "Walk-In Guest Account"
                date_str = rec.receipt_date.strftime("%Y-%m-%d %H:%M") if rec.receipt_date else "N/A"
                
                self.receipt_table.setItem(r_idx, 0, inv_item)
                self.receipt_table.setItem(r_idx, 1, QTableWidgetItem(client_str))
                self.receipt_table.setItem(r_idx, 2, QTableWidgetItem(f"${rec.total:.2f}"))
                self.receipt_table.setItem(r_idx, 3, QTableWidgetItem(f"${rec.paid_amount:.2f}"))
                self.receipt_table.setItem(r_idx, 4, QTableWidgetItem(rec.status.value if hasattr(rec.status, 'value') else str(rec.status)))
                self.receipt_table.setItem(r_idx, 5, QTableWidgetItem(date_str))
        except Exception as e:
            self.db_session.rollback()
            print(f"Failed to read historical receipts safely: {e}")

    def inspect_selected_receipt(self, model_index):
        row = model_index.row()
        target_item = self.receipt_table.item(row, 0)
        receipt_id = target_item.data(Qt.UserRole)
        
        receipt_obj = self.service.get_receipt_details(receipt_id)
        if receipt_obj:
            dialog = ReceiptDetailsDialog(self, receipt_obj)
            dialog.exec()

    def refresh_sales_history(self, *args):
        self.sales_table.setRowCount(0)
        query_str = self.sales_search.text()
        try:
            records = self.service.get_flat_sales_history(query_str)
            for idx, s in enumerate(records):
                self.sales_table.insertRow(idx)
                prod_str = s.product.name if s.product else "Unknown Row Reference"
                cashier_str = s.user.name if s.user else "System Counter"
                date_str = s.sale_date.strftime("%Y-%m-%d %H:%M") if s.sale_date else "N/A"
                
                self.sales_table.setItem(idx, 0, QTableWidgetItem(prod_str))
                self.sales_table.setItem(idx, 1, QTableWidgetItem(f"${s.price:.2f}"))
                self.sales_table.setItem(idx, 2, QTableWidgetItem(str(s.quantity)))
                self.sales_table.setItem(idx, 3, QTableWidgetItem(cashier_str))
                self.sales_table.setItem(idx, 4, QTableWidgetItem(date_str))
        except Exception as e:
            self.db_session.rollback()
            print(f"Failed to load sales items log map: {e}")

    def refresh_payments_ledger(self):
        self.payments_table.setRowCount(0)
        try:
            payments = self.db_session.query(Payment).order_by(Payment.payment_date.desc()).all()
            for idx, pmt in enumerate(payments):
                self.payments_table.insertRow(idx)
                
                rec_num = pmt.receipt.receipt_number if pmt.receipt else f"ID: {pmt.receipt_id}"
                method_name = pmt.payment_method.value if hasattr(pmt.payment_method, 'value') else str(pmt.payment_method)
                date_str = pmt.payment_date.strftime("%Y-%m-%d %H:%M:%S") if pmt.payment_date else "N/A"
                
                self.payments_table.setItem(idx, 0, QTableWidgetItem(str(pmt.id)))
                self.payments_table.setItem(idx, 1, QTableWidgetItem(rec_num))
                self.payments_table.setItem(idx, 2, QTableWidgetItem(method_name))
                self.payments_table.setItem(idx, 3, QTableWidgetItem(f"${pmt.amount:.2f}"))
                self.payments_table.setItem(idx, 4, QTableWidgetItem(f"${pmt.balance:.2f}"))
                self.payments_table.setItem(idx, 5, QTableWidgetItem(f"${pmt.change_amount:.2f}"))
                self.payments_table.setItem(idx, 6, QTableWidgetItem(date_str))
        except Exception as e:
            self.db_session.rollback()
            print(f"Error compiling global payments audit grid: {e}")