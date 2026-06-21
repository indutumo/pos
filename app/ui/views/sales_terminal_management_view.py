# app/ui/views/sales_terminal_management_view.py
import enum
import math
from datetime import datetime
from decimal import Decimal

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QDialog, QLabel, QComboBox, QMessageBox, QLineEdit,
    QAbstractItemView, QSpinBox, QDoubleSpinBox, QFormLayout,
    QFrame, QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt, QSize, QEvent, QPoint, QTimer, Signal
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintDialog

from app.repositories.sales_repo import SalesRepository, PAGE_SIZE
from app.services.sales_service import SalesService
from app.models.schema import Product, Customer, Payment, PaymentMethod
from app.repositories.org_repo import OrganizationRepository

# ====================================================================
# Reusable Pagination Bar Widget
# ====================================================================
class PaginationBar(QWidget):
    """
    A compact row of  ‹ Prev | Page N of M | Next ›  controls.
    Caller must connect `on_page_changed` to their reload method.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = 1
        self.total_pages = 1
        self._callback = None

        bar = QHBoxLayout(self)
        bar.setContentsMargins(0, 4, 0, 4)

        self.prev_btn = QPushButton("‹ Prev")
        self.prev_btn.setFixedWidth(70)
        self.prev_btn.clicked.connect(self._go_prev)

        self.page_lbl = QLabel("Page 1 of 1")
        self.page_lbl.setAlignment(Qt.AlignCenter)
        self.page_lbl.setStyleSheet("font-size: 12px;")

        self.next_btn = QPushButton("Next ›")
        self.next_btn.setFixedWidth(70)
        self.next_btn.clicked.connect(self._go_next)

        bar.addStretch()
        bar.addWidget(self.prev_btn)
        bar.addWidget(self.page_lbl)
        bar.addWidget(self.next_btn)
        bar.addStretch()

    # ------------------------------------------------------------------
    def set_callback(self, fn):
        self._callback = fn

    def update_state(self, current_page: int, total_count: int):
        self.current_page = current_page
        self.total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
        self.page_lbl.setText(f"Page {self.current_page} of {self.total_pages}")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)

    # ------------------------------------------------------------------
    def _go_prev(self):
        if self.current_page > 1:
            self.current_page -= 1
            if self._callback:
                self._callback()

    def _go_next(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            if self._callback:
                self._callback()

    def reset(self):
        self.current_page = 1


# ====================================================================
# Reusable Product Search Widget (type-ahead, rich result rows)
# ====================================================================
class ProductSearchWidget(QWidget):
    """
    A modern, type-ahead product picker.
    """

    productSelected = Signal(object)
    LOW_STOCK_THRESHOLD = 5
    MAX_RESULTS = 100

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_products = []
        self._filtered = []
        self._selected_id = None
        self._highlighted_row = -1

        self._build_ui()
        self._build_popup()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by product name or barcode…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textEdited.connect(self._on_text_edited)
        self.search_input.installEventFilter(self)
        layout.addWidget(self.search_input)

        self.selection_lbl = QLabel("No product selected")
        self.selection_lbl.setStyleSheet(self._idle_label_style())
        layout.addWidget(self.selection_lbl)

    def _build_popup(self):
        # Include FramelessWindowHint to ensure clean popup behavior
        self.popup = QFrame(self, Qt.ToolTip | Qt.FramelessWindowHint)

        self.popup.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)
        self.popup.setFocusPolicy(Qt.NoFocus)
        self.popup.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.popup.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.popup.setObjectName("ProductSearchPopup")
        self.popup.setStyleSheet("""
            #ProductSearchPopup {
                background: white;
                border: 1px solid #d0d4d9;
                border-radius: 8px;
            }
        """)
        popup_layout = QVBoxLayout(self.popup)
        popup_layout.setContentsMargins(4, 4, 4, 4)
        popup_layout.setSpacing(0)

        self.results_list = QListWidget()
        self.results_list.setFocusPolicy(Qt.NoFocus)
        self.results_list.setMouseTracking(True)
        self.results_list.viewport().setMouseTracking(True)
        self.results_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.results_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.results_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.results_list.setStyleSheet("""
            QListWidget { border: none; outline: none; background: transparent; }
            QListWidget::item { border-radius: 6px; margin: 1px 0; }
            QListWidget::item:hover { background: #f3f6f8; }
            QListWidget::item:selected { background: #e6f9fa; }
        """)
        self.results_list.itemClicked.connect(self._on_item_clicked)
        self.results_list.itemEntered.connect(self._on_item_hovered)
        popup_layout.addWidget(self.results_list)

        self.empty_lbl = QLabel("No matching products")
        self.empty_lbl.setAlignment(Qt.AlignCenter)
        self.empty_lbl.setStyleSheet("color: #8a8f98; padding: 16px; font-size: 12px;")
        self.empty_lbl.hide()
        popup_layout.addWidget(self.empty_lbl)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_products(self, products):
        self._all_products = products
        self.clear_selection()

    def selected_product_id(self):
        return self._selected_id

    def clear_selection(self):
        self._selected_id = None
        self._filtered = []
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        self.selection_lbl.setText("No product selected")
        self.selection_lbl.setStyleSheet(self._idle_label_style())
        self._hide_popup()

    # ------------------------------------------------------------------
    # Filtering & popup rendering
    # ------------------------------------------------------------------
    def _on_text_edited(self, text):
        self._selected_id = None
        query = text.strip().lower()

        if not query:
            self._filtered = []
            self._hide_popup()
            self.selection_lbl.setText("No product selected")
            self.selection_lbl.setStyleSheet(self._idle_label_style())
            self.productSelected.emit(None)
            return

        self._filtered = [
            p for p in self._all_products
            if query in p["name"].lower() or query in str(p.get("barcode") or "").lower()
        ][:self.MAX_RESULTS]

        self.selection_lbl.setText("No product selected")
        self.selection_lbl.setStyleSheet(self._idle_label_style())
        self._populate_results()
        self._show_popup()

    def _populate_results(self):
        self.results_list.clear()
        self._highlighted_row = -1

        if not self._filtered:
            self.results_list.hide()
            self.empty_lbl.show()
            return

        self.results_list.show()
        self.empty_lbl.hide()

        row_width = max(self.search_input.width(), 320)
        for product in self._filtered:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, product["id"])
            item.setSizeHint(QSize(row_width, 56))
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, self._make_row_widget(product))

        self.results_list.setCurrentRow(-1)

    def _make_row_widget(self, product):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(10)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        name_lbl = QLabel(product["name"])
        name_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #2b2d42;")
        barcode_text = f"Barcode: {product['barcode']}" if product.get("barcode") else "No barcode"
        barcode_lbl = QLabel(barcode_text)
        barcode_lbl.setStyleSheet("font-size: 11px; color: #8a8f98;")
        text_box.addWidget(name_lbl)
        text_box.addWidget(barcode_lbl)
        h.addLayout(text_box, 1)

        bg, fg, badge_text = self._stock_badge_style(product["quantity"])
        stock_lbl = QLabel(badge_text)
        stock_lbl.setAlignment(Qt.AlignCenter)
        stock_lbl.setStyleSheet(f"""
            background: {bg}; color: {fg};
            font-size: 10px; font-weight: 700;
            padding: 3px 9px; border-radius: 8px;
        """)

        price_lbl = QLabel(f"${product['price']:.2f}")
        price_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        price_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #00adb5;")

        right_box = QVBoxLayout()
        right_box.setSpacing(3)
        right_box.addWidget(stock_lbl, 0, Qt.AlignRight)
        right_box.addWidget(price_lbl, 0, Qt.AlignRight)
        h.addLayout(right_box)

        return row

    def _stock_badge_style(self, stock):
        if stock <= 0:
            return "#fde2e1", "#c0392b", "Out of stock"
        if stock <= self.LOW_STOCK_THRESHOLD:
            return "#fdf3d8", "#b8860b", f"{stock} left"
        return "#e3f6e8", "#2a9d6f", f"{stock} in stock"

    def _idle_label_style(self):
        return "color: #8a8f98; font-size: 11px; padding-left: 2px;"

    # ------------------------------------------------------------------
    # Popup show / hide / position
    # ------------------------------------------------------------------
    def _show_popup(self):
        anchor_bottom = self.search_input.mapToGlobal(
            self.search_input.rect().bottomLeft()
        )
        anchor_top = self.search_input.mapToGlobal(
            self.search_input.rect().topLeft()
        )

        width = max(self.search_input.width(), 320)
        self.popup.resize(width, self.popup.height())

        row_count = len(self._filtered)
        content_height = (56 * row_count) + 16 if self._filtered else 60

        screen = self.search_input.screen()
        screen_rect = screen.availableGeometry() if screen else None

        if screen_rect:
            space_below = screen_rect.bottom() - anchor_bottom.y()
            space_above = anchor_top.y() - screen_rect.top()

            show_below = (
                content_height <= space_below
                or space_below >= space_above
            )

            if show_below:
                final_height = min(content_height, max(space_below - 8, 60))
                pos = anchor_bottom
            else:
                final_height = min(content_height, max(space_above - 8, 60))
                pos = anchor_top - QPoint(0, final_height)

            self.popup.resize(width, final_height)
            self.popup.move(pos)
        else:
            self.popup.resize(width, content_height)
            self.popup.move(anchor_bottom)

        self.popup.show()

        # IMPORTANT
        self.popup.raise_()
        self.search_input.setFocus(Qt.OtherFocusReason)
        self.search_input.activateWindow()

    def _hide_popup(self):
        if hasattr(self, "popup") and self.popup:
            self.popup.hide()

    # ------------------------------------------------------------------
    # Selection handling
    # ------------------------------------------------------------------
    def _on_item_clicked(self, item):
        product_id = item.data(Qt.UserRole)
        product = next((p for p in self._filtered if p["id"] == product_id), None)
        if product:
            self._select_product(product)

    def _on_item_hovered(self, item):
        self._highlighted_row = self.results_list.row(item)

    def _select_product(self, product):
        self._selected_id = product["id"]

        self.search_input.blockSignals(True)
        self.search_input.setText(product["name"])
        self.search_input.blockSignals(False)
        self._hide_popup()

        bg, fg, _ = self._stock_badge_style(product["quantity"])
        self.selection_lbl.setText(f"Selected • {product['quantity']} in stock • ${product['price']:.2f}")
        self.selection_lbl.setStyleSheet(f"color: {fg}; font-size: 11px; font-weight: 700; padding-left: 2px;")

        self.productSelected.emit(product["id"])

    # ------------------------------------------------------------------
    # Keyboard navigation (Up / Down / Enter / Escape)
    # ------------------------------------------------------------------
    def eventFilter(self, obj, event):

        if obj is self.search_input:

            if event.type() == QEvent.FocusOut:
                if self.popup.isVisible():
                    QTimer.singleShot(
                        0,
                        lambda: self.search_input.setFocus(
                            Qt.OtherFocusReason
                        )
                    )
                return False

            if event.type() == QEvent.KeyPress:
                key = event.key()

                if key in (Qt.Key_Down, Qt.Key_Up):
                    if self.popup.isVisible() and self._filtered:
                        self._move_highlight(
                            1 if key == Qt.Key_Down else -1
                        )
                        return True

                if key in (Qt.Key_Return, Qt.Key_Enter):
                    if self.popup.isVisible() and self._filtered:
                        row = (
                            self._highlighted_row
                            if self._highlighted_row >= 0
                            else 0
                        )
                        self._select_product(self._filtered[row])
                        return True

                if key == Qt.Key_Escape:
                    self._hide_popup()
                    return True

        return super().eventFilter(obj, event)

    def _move_highlight(self, direction):
        if not self._filtered:
            return
        self._highlighted_row = (self._highlighted_row + direction) % len(self._filtered)
        self.results_list.setCurrentRow(self._highlighted_row)


# ====================================================================
# Printer Helper Function
# ====================================================================
def print_thermal_receipt(parent_widget, receipt_obj, db_session):
    # 1. Fetch dynamic organization data
    org_repo = OrganizationRepository(db_session)
    org = org_repo.get_profile()
    
    # 2. Extract values with fallbacks
    org_name = org.name or "Zola POS"
    org_address = org.address or "Nairobi, Kenya"
    org_mobile = org.phone or ""
    org_kra = org.kra_pin or ""

    date_str = receipt_obj.receipt_date.strftime("%Y-%m-%d %H:%M") if receipt_obj.receipt_date else "N/A"
    customer_name = receipt_obj.customer.name if receipt_obj.customer else "Walk-in Guest"
    cashier_name = receipt_obj.user.name if receipt_obj.user else "System"

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
            <p>{org_address}</p>
            <p>Tel: {org_mobile}</p>
            <p>PIN: {org_kra}</p>
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

    printer = QPrinter(QPrinter.HighResolution)
    dialog = QPrintDialog(printer, parent_widget)
    dialog.setWindowTitle("Print Receipt")

    if dialog.exec() == QDialog.Accepted:
        document.print_(printer)

# ====================================================================
# Receipt Details Dialog
# ====================================================================
class ReceiptDetailsDialog(QDialog):
    def __init__(self, parent, receipt_obj, db_session):
        super().__init__(parent)
        self.receipt_obj = receipt_obj
        self.db_session = db_session # Store the session here
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
        table.setHorizontalHeaderLabels(
            ["Product Item Description", "Unit Sold Price", "Quantity Ordered", "Subtotal Calculation"]
        )
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

        summary_lbl = QLabel(
            f"<h3>Grand Total: ${receipt_obj.total:.2f} | Tendered Paid: ${receipt_obj.paid_amount:.2f}</h3>"
        )
        summary_lbl.setAlignment(Qt.AlignRight)
        layout.addWidget(summary_lbl)

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
        # Now passing the session to the printer
        print_thermal_receipt(self, self.receipt_obj, self.db_session)


# ====================================================================
# Split-Payment Dialog
# ====================================================================
class PaymentProcessingDialog(QDialog):
    def __init__(self, parent, grand_total: Decimal):
        super().__init__(parent)
        self.setWindowTitle("Split-Payment Processing Terminal")
        self.setMinimumSize(500, 400)

        self.total_required = grand_total
        self.running_balance = grand_total
        self.payments_staged = []

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.summary_box = QHBoxLayout()
        self.total_lbl = QLabel(f"<b>Total Order:</b> ${self.total_required:.2f}")
        self.balance_lbl = QLabel(f"<b>Remaining Balance:</b> ${self.running_balance:.2f}")
        self.balance_lbl.setStyleSheet("color: #e63946; font-size: 14px; font-weight: bold;")
        self.summary_box.addWidget(self.total_lbl)
        self.summary_box.addWidget(self.balance_lbl)
        layout.addLayout(self.summary_box)

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

        layout.addWidget(QLabel("<b>Staged Payment Sub-Entries:</b>"))
        self.staged_table = QTableWidget(0, 4)
        self.staged_table.setHorizontalHeaderLabels(
            ["Method Channel", "Amount Paid", "Invoice Balance", "Cash Change"]
        )
        self.staged_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.staged_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.staged_table)

        btn_box = QHBoxLayout()
        cancel_btn = QPushButton("Abort Order")
        cancel_btn.clicked.connect(self.reject)

        self.commit_btn = QPushButton("Complete & Close BillReceipt")
        self.commit_btn.setEnabled(False)
        self.commit_btn.setStyleSheet("background: #38a169; color: white; font-weight: bold;")
        self.commit_btn.clicked.connect(self.accept)

        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(self.commit_btn)
        layout.addLayout(btn_box)

    def handle_method_context_switch(self):
        if self.running_balance > 0:
            self.amount_input.setValue(float(self.running_balance))

    def stage_payment_slice(self):
        chosen_method = self.method_combo.currentData()
        collected = Decimal(str(self.amount_input.value()))

        if collected <= 0:
            return

        change_returned = Decimal("0.00")
        calculated_balance = self.running_balance - collected

        if chosen_method == PaymentMethod.CASH and calculated_balance < 0:
            change_returned = abs(calculated_balance)
            calculated_balance = Decimal("0.00")
        elif chosen_method in (PaymentMethod.BANK, PaymentMethod.MOBILE_MONEY) and calculated_balance < 0:
            QMessageBox.warning(
                self, "Transaction Bound Exception",
                "Digital payments cannot exceed the exact remaining invoice balance due.",
            )
            return

        self.running_balance = calculated_balance

        self.payments_staged.append({
            "method": chosen_method,
            "amount": collected - change_returned if calculated_balance == 0 else collected,
            "balance": self.running_balance,
            "change": change_returned,
        })

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
            self.staged_table.setItem(idx, 0, QTableWidgetItem(p["method"].value))
            self.staged_table.setItem(idx, 1, QTableWidgetItem(f"${p['amount']:.2f}"))
            self.staged_table.setItem(idx, 2, QTableWidgetItem(f"${p['balance']:.2f}"))
            self.staged_table.setItem(idx, 3, QTableWidgetItem(f"${p['change']:.2f}"))


# ====================================================================
# Main Sales Terminal View
# ====================================================================
class SalesTerminalManagementView(QWidget):
    def __init__(self, current_user, db_session):
        super().__init__()
        self.current_user = current_user
        self.db_session = db_session
        self.repo = SalesRepository(self.db_session)
        self.service = SalesService(self.repo)
        self.active_cart = []

        self._receipt_page = 1
        self._sales_page = 1
        self._payments_page = 1

        self.init_ui()
        self.reload_terminal_combos()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def init_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8f9fa; font-family: 'Segoe UI', Arial; color: #2b2d42; }
            QTableWidget { background-color: #ffffff; border: 1px solid #e1e4e8; border-radius: 4px; }
            QHeaderView::section { background-color: #edf2f7; font-weight: bold; padding: 6px; }
            QPushButton { border-radius: 4px; font-weight: bold; padding: 8px 12px; }
            QLineEdit, QComboBox, QDoubleSpinBox {
                border: 1px solid #ccd1d9; padding: 6px; border-radius: 4px; background: white;
            }
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

    # ---- POS Tab -------------------------------------------------------

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

        self.product_search = ProductSearchWidget()
        form.addRow("Search / Add Item:", self.product_search)

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

    # ---- Receipt Registry Tab -----------------------------------------

    def build_receipt_registry_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        search_box = QHBoxLayout()
        self.receipt_search = QLineEdit()
        self.receipt_search.setPlaceholderText(
            "Filter receipts by invoice number or customer name..."
        )
        
        self.receipt_search_timer = QTimer(self)
        self.receipt_search_timer.setSingleShot(True)
        self.receipt_search_timer.setInterval(300)
        self.receipt_search_timer.timeout.connect(self._trigger_receipt_search)
        
        self.receipt_search.textChanged.connect(self._on_receipt_search_changed)
        search_box.addWidget(self.receipt_search)
        layout.addLayout(search_box)

        self.receipt_table = QTableWidget(0, 6)
        self.receipt_table.setHorizontalHeaderLabels(
            ["Invoice Code Token", "Client Mapping", "Grand Valuation",
             "Tendered Value", "Condition State", "Created Timestamp"]
        )
        self.receipt_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.receipt_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.receipt_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.receipt_table.doubleClicked.connect(self.inspect_selected_receipt)
        layout.addWidget(self.receipt_table)

        self.receipt_pager = PaginationBar()
        self.receipt_pager.set_callback(self.refresh_receipts_register)
        layout.addWidget(self.receipt_pager)

        self.tabs.addTab(page, "Receipt List")

    # ---- Sales List Tab -----------------------------------------------

    def build_flat_sales_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        search_box = QHBoxLayout()
        self.sales_search = QLineEdit()
        self.sales_search.setPlaceholderText("Filter item logs by product name...")
        
        self.sales_search_timer = QTimer(self)
        self.sales_search_timer.setSingleShot(True)
        self.sales_search_timer.setInterval(300)
        self.sales_search_timer.timeout.connect(self._trigger_sales_search)
        
        self.sales_search.textChanged.connect(self._on_sales_search_changed)
        search_box.addWidget(self.sales_search)
        layout.addLayout(search_box)

        self.sales_table = QTableWidget(0, 5)
        self.sales_table.setHorizontalHeaderLabels(
            ["Item Identity Name", "Unit Transaction Price", "Quantity Transacted",
             "Operator Counter User", "Date Captured"]
        )
        self.sales_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sales_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.sales_table)

        self.sales_pager = PaginationBar()
        self.sales_pager.set_callback(self.refresh_sales_history)
        layout.addWidget(self.sales_pager)

        self.tabs.addTab(page, "Sales List")

    # ---- Payments Ledger Tab ------------------------------------------

    def build_payments_ledger_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        info_banner = QLabel("<b>Global Payments Activity Log</b> (Accessible by all operational profiles)")
        info_banner.setStyleSheet("color: #555; font-size: 12px; padding: 2px;")
        layout.addWidget(info_banner)

        self.payments_table = QTableWidget(0, 7)
        self.payments_table.setHorizontalHeaderLabels(
            ["Payment ID", "Receipt Number", "Method Channel",
             "Amount Received", "Remaining Balance", "Change Handed", "Processed Date"]
        )
        self.payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.payments_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.payments_table)

        self.payments_pager = PaginationBar()
        self.payments_pager.set_callback(self.refresh_payments_ledger)
        layout.addWidget(self.payments_pager)

        self.tabs.addTab(page, "Payments List")

    # ------------------------------------------------------------------
    # Search-changed helpers (Timer debounced)
    # ------------------------------------------------------------------

    def _on_receipt_search_changed(self, *args):
        self.receipt_search_timer.start()

    def _trigger_receipt_search(self):
        self.receipt_pager.reset()
        self.refresh_receipts_register()

    def _on_sales_search_changed(self, *args):
        self.sales_search_timer.start()

    def _trigger_sales_search(self):
        self.sales_pager.reset()
        self.refresh_sales_history()

    # ------------------------------------------------------------------
    # Tab switch handler
    # ------------------------------------------------------------------

    def handle_tab_switches(self, idx):
        if idx == 0:
            self.reload_terminal_combos()
        elif idx == 1:
            self.refresh_receipts_register()
        elif idx == 2:
            self.refresh_sales_history()
        elif idx == 3:
            self.refresh_payments_ledger()

    # ------------------------------------------------------------------
    # POS helpers
    # ------------------------------------------------------------------

    def reload_terminal_combos(self):
        self.cust_combo.clear()
        self.cust_combo.addItem("Anonymous Walk-in Customer Guest Account", 0)

        try:
            for c in self.db_session.query(Customer).order_by(Customer.name.asc()).all():
                self.cust_combo.addItem(c.name, c.id)

            active_products = (
                self.db_session.query(Product)
                .filter(Product.status == "ACTIVE")
                .order_by(Product.name.asc())
                .all()
            )

            product_dicts = []
            for p in active_products:
                product_price = getattr(p, "selling_price", 0.00)
                price_display = float(product_price) if product_price is not None else 0.00
                product_dicts.append({
                    "id": p.id,
                    "name": p.name,
                    "barcode": p.barcode,
                    "quantity": p.quantity,
                    "price": price_display,
                })

            self.product_search.set_products(product_dicts)
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.warning(self, "Pipeline Error", f"Sync fail context error: {e}")

    def handle_instant_barcode_scan(self):
        scanned_token = self.barcode_scan_input.text().strip()
        if not scanned_token:
            return

        try:
            product = self.db_session.query(Product).filter(
                Product.barcode == scanned_token,
                Product.status == "ACTIVE",
            ).first()

            if not product:
                QMessageBox.warning(self, "Item Missing", f"No active item matches barcode: '{scanned_token}'")
                self.barcode_scan_input.clear()
                return

            scan_qty = self.qty_input.value()
            if scan_qty > product.quantity:
                QMessageBox.warning(self, "Stock Shortage",
                                    f"Cannot allocate {scan_qty}. Only {product.quantity} units available.")
                self.barcode_scan_input.clear()
                return

            for cached_item in self.active_cart:
                if cached_item["product_id"] == product.id:
                    if (cached_item["qty"] + scan_qty) > product.quantity:
                        QMessageBox.warning(self, "Stock Violation",
                                            "Combined quantities breach stock bounds.")
                        self.barcode_scan_input.clear()
                        return
                    cached_item["qty"] += scan_qty
                    self.redraw_cart_table()
                    self.barcode_scan_input.clear()
                    return

            resolved_price = getattr(product, "selling_price", 0.00)
            self.active_cart.append({
                "product_id": product.id,
                "name": product.name,
                "qty": scan_qty,
                "unit_price": float(resolved_price) if resolved_price is not None else 0.00,
            })
            self.redraw_cart_table()
            self.barcode_scan_input.clear()

        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Scan Processing Error", f"Error in scanning pipeline: {e}")

    def add_item_to_cart_cache(self, *args):
        p_id = self.product_search.selected_product_id()
        if p_id is None:
            QMessageBox.warning(self, "Selection Missing", "Please search and select a product before adding.")
            return

        product = self.db_session.query(Product).filter(Product.id == p_id).first()
        qty = self.qty_input.value()

        if not product:
            return

        if qty > product.quantity:
            QMessageBox.warning(self, "Stock Limit Exception",
                                f"Cannot order {qty} units. Only {product.quantity} in stock.")
            return

        for cached_item in self.active_cart:
            if cached_item["product_id"] == p_id:
                if (cached_item["qty"] + qty) > product.quantity:
                    QMessageBox.warning(self, "Stock Boundary Violation",
                                        "Accumulated quantities exceed available stock.")
                    return
                cached_item["qty"] += qty
                self.redraw_cart_table()
                return

        resolved_price = getattr(product, "selling_price", 0.00)
        self.active_cart.append({
            "product_id": p_id,
            "name": product.name,
            "qty": qty,
            "unit_price": float(resolved_price) if resolved_price is not None else 0.00,
        })
        self.redraw_cart_table()

        self.product_search.clear_selection()
        self.qty_input.setValue(1)
        self.product_search.search_input.setFocus()

    def handle_cart_cell_changed(self, row, column):
        if column not in (1, 2):
            return
        ui_item = self.cart_table.item(row, column)
        if not ui_item:
            return
        cart_item = self.active_cart[row]

        if column == 1:
            try:
                new_price = float(ui_item.text().replace("$", "").strip())
                if new_price < 0:
                    raise ValueError()
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Price must be a valid non-negative number.")
                self.redraw_cart_table()
                return
            cart_item["unit_price"] = new_price
            self.redraw_cart_table()

        elif column == 2:
            try:
                new_qty = int(ui_item.text().strip())
                if new_qty <= 0:
                    raise ValueError()
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Quantity must be a positive integer.")
                self.redraw_cart_table()
                return
            product = self.db_session.query(Product).filter(Product.id == cart_item["product_id"]).first()
            if product and new_qty > product.quantity:
                QMessageBox.warning(self, "Stock Boundary Violation",
                                    f"Cannot set {new_qty}. Only {product.quantity} in stock.")
                self.redraw_cart_table()
                return
            cart_item["qty"] = new_qty
            self.redraw_cart_table()

    def redraw_cart_table(self):
        self.cart_table.blockSignals(True)
        self.cart_table.setRowCount(0)
        accumulated_total = Decimal("0.00")

        for idx, item in enumerate(self.active_cart):
            self.cart_table.insertRow(idx)
            sub = Decimal(str(item["qty"])) * Decimal(str(item["unit_price"]))
            accumulated_total += sub

            name_cell = QTableWidgetItem(item["name"])
            name_cell.setFlags(name_cell.flags() & ~Qt.ItemIsEditable)

            price_cell = QTableWidgetItem(f"{item['unit_price']:.2f}")
            price_cell.setFlags(price_cell.flags() | Qt.ItemIsEditable)

            qty_cell = QTableWidgetItem(str(item["qty"]))
            qty_cell.setFlags(qty_cell.flags() | Qt.ItemIsEditable)

            total_cell = QTableWidgetItem(f"${sub:.2f}")
            total_cell.setFlags(total_cell.flags() & ~Qt.ItemIsEditable)

            self.cart_table.setItem(idx, 0, name_cell)
            self.cart_table.setItem(idx, 1, price_cell)
            self.cart_table.setItem(idx, 2, qty_cell)
            self.cart_table.setItem(idx, 3, total_cell)

        self.running_total_lbl.setText(f"Total: ${accumulated_total:.2f}")
        self.cart_table.blockSignals(False)

    # ------------------------------------------------------------------
    # Checkout
    # ------------------------------------------------------------------

    def execute_cart_checkout(self, *args):
        if not self.active_cart:
            QMessageBox.warning(self, "Processing Halting", "Cart is empty. Operation aborted.")
            return

        grand_total = sum(
            Decimal(str(i["qty"])) * Decimal(str(i["unit_price"])) for i in self.active_cart
        )

        pmt_dialog = PaymentProcessingDialog(self, grand_total)
        if pmt_dialog.exec() != QDialog.Accepted:
            return

        c_id = self.cust_combo.currentData()

        try:
            receipt_obj = self.service.checkout_cart(
                current_user=self.current_user,
                customer_id=c_id,
                cart_items=self.active_cart,
                paid_amount=float(grand_total),
            )
            receipt_id = receipt_obj.id if hasattr(receipt_obj, "id") else receipt_obj

            for p_slice in pmt_dialog.payments_staged:
                payment_record = Payment(
                    receipt_id=receipt_id,
                    amount=p_slice["amount"],
                    balance=p_slice["balance"],
                    change_amount=p_slice["change"],
                    payment_method=p_slice["method"],
                    user_id=self.current_user.id,
                    payment_date=datetime.utcnow(),
                )
                self.db_session.add(payment_record)

            self.service.process_shift_aggregation(
                self.db_session, self.current_user.id, pmt_dialog.payments_staged
            )
            self.db_session.commit()

            QMessageBox.information(self, "Order Finalized",
                                    "All payments validated. Receipt completed successfully.")

            full_receipt_obj = self.db_session.query(type(receipt_obj)).filter_by(id=receipt_id).first()
            if full_receipt_obj:
                reply = QMessageBox.question(
                    self, "Print Receipt", "Would you like to print the receipt now?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
                )
                if reply == QMessageBox.Yes:
                    # Pass self.db_session here
                    print_thermal_receipt(self, full_receipt_obj, self.db_session)

            self.active_cart = []
            self.redraw_cart_table()
            self.reload_terminal_combos()
            self.barcode_scan_input.setFocus()

        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Database Constraint Fault", f"Execution error: {e}")

    # ------------------------------------------------------------------
    # Receipt registry
    # ------------------------------------------------------------------

    def refresh_receipts_register(self):
        self.receipt_table.setRowCount(0)
        query_str = self.receipt_search.text()
        page = self.receipt_pager.current_page
        try:
            records, total = self.service.get_receipts_ledger(query_str, page)
            self.receipt_pager.update_state(page, total)

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
                self.receipt_table.setItem(
                    r_idx, 4,
                    QTableWidgetItem(rec.status.value if hasattr(rec.status, "value") else str(rec.status)),
                )
                self.receipt_table.setItem(r_idx, 5, QTableWidgetItem(date_str))
        except Exception as e:
            self.db_session.rollback()
            print(f"Failed to load receipts: {e}")

    def inspect_selected_receipt(self, model_index):
        row = model_index.row()
        target_item = self.receipt_table.item(row, 0)
        receipt_id = target_item.data(Qt.UserRole)
        receipt_obj = self.service.get_receipt_details(receipt_id)
        if receipt_obj:
            # Pass self.db_session to the dialog
            dialog = ReceiptDetailsDialog(self, receipt_obj, self.db_session)
            dialog.exec()

    # ------------------------------------------------------------------
    # Sales history
    # ------------------------------------------------------------------

    def refresh_sales_history(self):
        self.sales_table.setRowCount(0)
        query_str = self.sales_search.text()
        page = self.sales_pager.current_page
        try:
            records, total = self.service.get_flat_sales_history(query_str, page)
            self.sales_pager.update_state(page, total)

            for idx, s in enumerate(records):
                self.sales_table.insertRow(idx)
                prod_str = s.product.name if s.product else "Unknown"
                cashier_str = s.user.name if s.user else "System"
                date_str = s.sale_date.strftime("%Y-%m-%d %H:%M") if s.sale_date else "N/A"

                self.sales_table.setItem(idx, 0, QTableWidgetItem(prod_str))
                self.sales_table.setItem(idx, 1, QTableWidgetItem(f"${s.price:.2f}"))
                self.sales_table.setItem(idx, 2, QTableWidgetItem(str(s.quantity)))
                self.sales_table.setItem(idx, 3, QTableWidgetItem(cashier_str))
                self.sales_table.setItem(idx, 4, QTableWidgetItem(date_str))
        except Exception as e:
            self.db_session.rollback()
            print(f"Failed to load sales history: {e}")

    # ------------------------------------------------------------------
    # Payments ledger
    # ------------------------------------------------------------------

    def refresh_payments_ledger(self):
        self.payments_table.setRowCount(0)
        page = self.payments_pager.current_page
        try:
            payments, total = self.service.get_payments_ledger(page)
            self.payments_pager.update_state(page, total)

            for idx, pmt in enumerate(payments):
                self.payments_table.insertRow(idx)
                rec_num = pmt.receipt.receipt_number if pmt.receipt else f"ID: {pmt.receipt_id}"
                method_name = (
                    pmt.payment_method.value
                    if hasattr(pmt.payment_method, "value")
                    else str(pmt.payment_method)
                )
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
            print(f"Error loading payments ledger: {e}")