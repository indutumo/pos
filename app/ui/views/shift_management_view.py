# app/ui/views/shift_management_view.py
from datetime import datetime
from decimal import Decimal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QDialog, QLabel, QComboBox, QMessageBox, 
                             QAbstractItemView, QDoubleSpinBox, QFormLayout, 
                             QDateEdit, QCheckBox)
from PySide6.QtCore import Qt, QDate
from sqlalchemy import func

# Ensure Payment is imported from your schema
from app.models.schema import Shift, User, Payment 

class PaymentDetailsDialog(QDialog):
    """Dialog to show individual payments for a selected shift."""
    def __init__(self, parent, shift_obj, db_session):
        super().__init__(parent)
        self.setWindowTitle(f"Payments for Shift #{shift_obj.id}")
        self.setMinimumSize(550, 350)
        self.setStyleSheet("""
            QTableWidget { background-color: #ffffff; border: 1px solid #e1e4e8; border-radius: 4px; }
            QHeaderView::section { background-color: #edf2f7; font-weight: bold; padding: 6px; }
        """)
        
        layout = QVBoxLayout(self)
        
        info_lbl = QLabel(f"<b>Showing Payments for Shift ID:</b> {shift_obj.id} | <b>Operator:</b> {shift_obj.user.name}")
        info_lbl.setStyleSheet("font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(info_lbl)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Payment ID", "Method", "Amount ($)", "Timestamp"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.table)
        
        # Query payments for this user on the shift's date
        payments = db_session.query(Payment).filter(
            Payment.user_id == shift_obj.user_id,
            func.date(Payment.payment_date) == func.date(shift_obj.shift_date)
        ).order_by(Payment.payment_date.asc()).all()
        
        for idx, p in enumerate(payments):
            self.table.insertRow(idx)
            self.table.setItem(idx, 0, QTableWidgetItem(str(p.id)))
            
            # Safely parse payment method enum/string
            method_str = getattr(p, 'payment_method', 'UNKNOWN')
            if hasattr(method_str, 'name'):
                method_str = method_str.name
            
            self.table.setItem(idx, 1, QTableWidgetItem(str(method_str)))
            self.table.setItem(idx, 2, QTableWidgetItem(f"${float(p.amount or 0):.2f}"))
            
            time_str = p.payment_date.strftime("%Y-%m-%d %H:%M:%S") if getattr(p, 'payment_date', None) else "N/A"
            self.table.setItem(idx, 3, QTableWidgetItem(time_str))

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)


class CloseShiftDialog(QDialog):
    """Dialog to input the actual cash drawer count and calculate shift discrepancies."""
    def __init__(self, parent, shift_obj):
        super().__init__(parent)
        self.shift = shift_obj
        self.setWindowTitle(f"Shift Closure: #{self.shift.id}")
        self.setMinimumSize(400, 250)
        
        self.system_expected = Decimal(str(self.shift.total_sales or 0.00))
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        shift_date_str = self.shift.shift_date.strftime('%Y-%m-%d %H:%M') if getattr(self.shift, 'shift_date', None) else "N/A"
        
        info_lbl = QLabel(
            f"<b>Operator:</b> {self.shift.user.name if self.shift.user else 'Unknown'}<br>"
            f"<b>Shift Started:</b> {shift_date_str}<br>"
            f"<b>System Expected Sales:</b> <font color='#2a9d8f'>${self.system_expected:.2f}</font>"
        )
        info_lbl.setStyleSheet("font-size: 14px; line-height: 150%;")
        layout.addWidget(info_lbl)

        form = QFormLayout()
        self.actual_sales_input = QDoubleSpinBox()
        self.actual_sales_input.setRange(0.00, 999999.99)
        self.actual_sales_input.setValue(float(self.system_expected))
        self.actual_sales_input.setPrefix("$ ")
        self.actual_sales_input.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        form.addRow("Actual Drawer Count:", self.actual_sales_input)
        layout.addLayout(form)

        self.diff_lbl = QLabel(f"<b>Difference:</b> $0.00")
        self.actual_sales_input.valueChanged.connect(self.update_difference)
        layout.addWidget(self.diff_lbl)

        btn_box = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        self.confirm_btn = QPushButton("Close Shift & Lock Ledger")
        self.confirm_btn.setStyleSheet("background: #e63946; color: white; font-weight: bold;")
        self.confirm_btn.clicked.connect(self.accept)
        
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(self.confirm_btn)
        layout.addLayout(btn_box)

    def update_difference(self):
        actual = Decimal(str(self.actual_sales_input.value()))
        diff = actual - self.system_expected
        color = "#e63946" if diff < 0 else "#2a9d8f"
        self.diff_lbl.setText(f"<b>Difference:</b> <font color='{color}'>${diff:.2f}</font>")

    def get_closure_data(self):
        actual = Decimal(str(self.actual_sales_input.value()))
        return {
            "actual_sales": actual,
            "difference": actual - self.system_expected
        }


class ShiftManagementView(QWidget):
    def __init__(self, user, db_session):
        super().__init__()
        self.current_user = user
        self.db_session = db_session
        self.init_ui()
        self.load_filters()
        self.refresh_shift_table()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8f9fa; font-family: 'Segoe UI', Arial; color: #2b2d42; }
            QTableWidget { background-color: #ffffff; border: 1px solid #e1e4e8; border-radius: 4px; }
            QHeaderView::section { background-color: #edf2f7; font-weight: bold; padding: 6px; }
            QPushButton { border-radius: 4px; font-weight: bold; padding: 6px 12px; }
            QComboBox, QDateEdit { border: 1px solid #ccd1d9; padding: 4px; border-radius: 4px; background: white; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        ## 1. Unified Top Control Bar
        top_bar_layout = QHBoxLayout()
        
        # --- Filters ---
        filter_layout = QHBoxLayout()
        self.use_date_cb = QCheckBox("Filter by Date:")
        self.use_date_cb.stateChanged.connect(self.refresh_shift_table)
        filter_layout.addWidget(self.use_date_cb)
        
        self.date_filter = QDateEdit()
        self.date_filter.setCalendarPopup(True)
        self.date_filter.setDate(QDate.currentDate())
        self.date_filter.setEnabled(False)
        self.use_date_cb.toggled.connect(self.date_filter.setEnabled)
        self.date_filter.dateChanged.connect(self.refresh_shift_table)
        filter_layout.addWidget(self.date_filter)

        filter_layout.addWidget(QLabel("User:"))
        self.user_combo = QComboBox()
        self.user_combo.currentIndexChanged.connect(self.refresh_shift_table)
        filter_layout.addWidget(self.user_combo)

        filter_layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["ALL", "OPEN", "CLOSED"])
        self.status_combo.currentIndexChanged.connect(self.refresh_shift_table)
        filter_layout.addWidget(self.status_combo)
        
        top_bar_layout.addLayout(filter_layout)
        top_bar_layout.addStretch()

        # --- Action Buttons ---
        actions_layout = QHBoxLayout()
        self.start_shift_btn = QPushButton("Start New Shift")
        self.start_shift_btn.setStyleSheet("background: #2a9d8f; color: white;")
        self.start_shift_btn.clicked.connect(self.execute_start_shift)
        actions_layout.addWidget(self.start_shift_btn)
        
        self.close_shift_btn = QPushButton("Close Shift (Admin Only)")
        self.close_shift_btn.setStyleSheet("background: #e63946; color: white;")
        self.close_shift_btn.clicked.connect(self.execute_shift_closure)
        actions_layout.addWidget(self.close_shift_btn)
        
        top_bar_layout.addLayout(actions_layout)
        layout.addLayout(top_bar_layout)

        ## 2. Shift Ledger Table
        self.shift_table = QTableWidget(0, 7)
        self.shift_table.setHorizontalHeaderLabels([
            "Shift ID", "Operator", "Shift Date", 
            "Status", "Total Sales ($)", "Actual Count ($)", "Difference ($)"
        ])
        self.shift_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.shift_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.shift_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # Connect double-click event to show shift details
        self.shift_table.doubleClicked.connect(self.show_payment_details)
        
        layout.addWidget(self.shift_table)
        
        info_footer = QLabel("<i>* Double-click a row to view payment details for that shift.</i>")
        info_footer.setStyleSheet("color: #6c757d;")
        layout.addWidget(info_footer)

    def load_filters(self):
        self.user_combo.blockSignals(True)
        self.user_combo.clear()
        self.user_combo.addItem("All Users", None)
        try:
            users = self.db_session.query(User).order_by(User.name.asc()).all()
            for u in users:
                self.user_combo.addItem(u.name, u.id)
        except Exception as e:
            print(f"Failed to load users: {e}")
        finally:
            self.user_combo.blockSignals(False)

    def refresh_shift_table(self):
        self.shift_table.setRowCount(0)
        query = self.db_session.query(Shift)

        if self.use_date_cb.isChecked():
            target_date = self.date_filter.date().toPython()
            query = query.filter(func.date(Shift.shift_date) == target_date)

        selected_user_id = self.user_combo.currentData()
        if selected_user_id:
            query = query.filter(Shift.user_id == selected_user_id)

        status = self.status_combo.currentText()
        if status != "ALL":
            query = query.filter(Shift.status == status)

        try:
            shifts = query.order_by(Shift.created_at.desc()).all()
            for idx, shift in enumerate(shifts):
                self.shift_table.insertRow(idx)
                
                id_item = QTableWidgetItem(str(shift.id))
                id_item.setData(Qt.UserRole, shift.id)
                
                user_str = shift.user.name if shift.user else "System"
                
                start_dt = getattr(shift, 'shift_date', None)
                start_str = start_dt.strftime("%Y-%m-%d %H:%M") if start_dt else "N/A"
                
                raw_status = getattr(shift, 'status', 'UNKNOWN')
                status_str = raw_status.name if hasattr(raw_status, 'name') else str(raw_status).replace('ShiftStatus.', '')
                
                expected_str = f"${float(shift.total_sales or 0):.2f}"
                actual_str = f"${float(shift.actual_sales):.2f}" if shift.actual_sales is not None else "Pending"
                diff_str = f"${float(shift.difference):.2f}" if shift.difference is not None else "Pending"
                
                self.shift_table.setItem(idx, 0, id_item)
                self.shift_table.setItem(idx, 1, QTableWidgetItem(user_str))
                self.shift_table.setItem(idx, 2, QTableWidgetItem(start_str))
                self.shift_table.setItem(idx, 3, QTableWidgetItem(status_str))
                self.shift_table.setItem(idx, 4, QTableWidgetItem(expected_str))
                self.shift_table.setItem(idx, 5, QTableWidgetItem(actual_str))
                self.shift_table.setItem(idx, 6, QTableWidgetItem(diff_str))

                if shift.difference is not None and shift.difference < 0:
                    self.shift_table.item(idx, 6).setForeground(Qt.red)

        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to load shift records:\n{str(e)}")

    def show_payment_details(self, index):
        row = index.row()
        shift_id = self.shift_table.item(row, 0).data(Qt.UserRole)
        shift_obj = self.db_session.query(Shift).filter(Shift.id == shift_id).first()
        if shift_obj:
            dlg = PaymentDetailsDialog(self, shift_obj, self.db_session)
            dlg.exec()

    def execute_start_shift(self):
        user_shifts = self.db_session.query(Shift).filter(Shift.user_id == self.current_user.id).all()
        existing_open_shift = next((s for s in user_shifts if (hasattr(s.status, 'name') and s.status.name == "OPEN") or str(s.status).endswith("OPEN")), None)

        if existing_open_shift:
            QMessageBox.warning(self, "Shift Already Open", 
                              "You already have an active open shift. Please close it before starting a new one.")
            return

        try:
            new_shift = Shift(user_id=self.current_user.id)
            self.db_session.add(new_shift)
            self.db_session.commit()
            
            QMessageBox.information(self, "Success", f"New shift started successfully!")
            self.status_combo.setCurrentText("OPEN")
            self.refresh_shift_table()

        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to start a new shift:\n{str(e)}")

    def execute_shift_closure(self):
        # ---------------------------------------------------------
        # SECURITY CHECK: Admin only (UPDATED FOR ROLE_NAME)
        # ---------------------------------------------------------
        is_admin = False
        
        # Check if the user has a role relationship, and if that role has a role_name
        if hasattr(self.current_user, 'role') and self.current_user.role:
            role_obj = self.current_user.role
            if hasattr(role_obj, 'role_name') and role_obj.role_name:
                role_str = str(role_obj.role_name).upper()
                if "ADMIN" in role_str or "SUPERUSER" in role_str:
                    is_admin = True

        if not is_admin:
            QMessageBox.critical(self, "Permission Denied", 
                                 "You do not have the necessary permissions to close a shift.\n"
                                 "Please ask a manager or admin to perform this action.")
            return
        # ---------------------------------------------------------

        selected_rows = self.shift_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selection Required", "Please select a shift from the table to close.")
            return

        row = selected_rows[0].row()
        shift_id = self.shift_table.item(row, 0).data(Qt.UserRole)
        
        try:
            shift_obj = self.db_session.query(Shift).filter(Shift.id == shift_id).first()
            if not shift_obj:
                return
            
            is_closed = (hasattr(shift_obj.status, 'name') and shift_obj.status.name == "CLOSED") or str(shift_obj.status).endswith("CLOSED")
            
            if is_closed:
                QMessageBox.information(self, "Shift Closed", "This shift has already been finalized.")
                return

            dialog = CloseShiftDialog(self, shift_obj)
            if dialog.exec() == QDialog.Accepted:
                closure_data = dialog.get_closure_data()
                
                shift_obj.actual_sales = closure_data["actual_sales"]
                shift_obj.difference = closure_data["difference"]
                shift_obj.status = "CLOSED" 
                
                self.db_session.commit()
                QMessageBox.information(self, "Success", f"Shift #{shift_obj.id} closed.")
                self.refresh_shift_table()

        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to close shift:\n{str(e)}")