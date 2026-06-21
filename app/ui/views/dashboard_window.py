import os
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QPushButton, QLabel, QStackedWidget, QStatusBar
)
from PySide6.QtCore import Qt

# Import all View Classes
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.user_management_view import UserManagementView
from app.ui.views.product_management_view import ProductManagementView
from app.ui.views.customer_management_view import CustomerManagementView
from app.ui.views.stocktake_management_view import StockTakeManagementView 
from app.ui.views.sales_terminal_management_view import SalesTerminalManagementView 
from app.ui.views.shift_management_view import ShiftManagementView
from app.ui.views.analytics_reports_view import AnalyticsReportsView
from app.ui.views.org_settings_view import OrganizationSettingsView

from app.core.database import SessionLocal

class DashboardWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        
        base_dir = os.getcwd()
        icon_path = os.path.join(base_dir, "assets", "logo.ico")
        
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.db_session = SessionLocal() 
        self.setWindowTitle(f"Zola POS Core Enterprise Suite: {self.user.username}")
        self.resize(1150, 750)
        self.init_ui()

    def init_ui(self):
        # Base Layout Theme Config
        self.setStyleSheet("""
            QMainWindow { background-color: #f8f9fa; }
            QWidget#sidebar { background-color: #ffffff; border-right: 1px solid #e1e4e8; min-width: 220px; max-width: 220px; }
            QLabel#logoLabel { color: #00adb5; font-size: 20px; font-weight: bold; padding: 20px 10px; }
            QWidget#mainContent { background-color: #f8f9fa; }
            QLabel#viewTitle { color: #2b2d42; font-size: 24px; font-weight: bold; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar Assembly
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setAlignment(Qt.AlignTop)

        logo = QLabel("Zola POS")
        logo.setObjectName("logoLabel")
        logo.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(logo)

        self.menu_buttons = {}
        
        # Navigation Routing
        navigation_schema = [
            ("Dashboard", ["ADMIN", "CASHIER", "MANAGE_STOCK"]),
            ("Sales Terminal", ["ADMIN", "CASHIER"]),
            ("Shift Ledger", ["ADMIN", "CASHIER", "MANAGE_STOCK"]),
            ("Inventory Manager", ["ADMIN", "CASHIER", "MANAGE_STOCK"]), 
            ("Customer Manager", ["ADMIN", "CASHIER", "MANAGE_STOCK"]),  
            ("Stock Take Audit", ["ADMIN", "MANAGE_STOCK"]),
            ("Analytics & Reports", ["ADMIN"]),
            ("System Users", ["ADMIN"]),
            ("Organization Settings", ["ADMIN"]), 
        ]

        user_role_str = self.user.role.role_name
        
        # Generate Sidebar Buttons
        for view_name, allowed_roles in navigation_schema:
            if user_role_str in allowed_roles or view_name == "Sales Terminal":
                btn = QPushButton(view_name)
                btn.setCheckable(True)
                btn.setAutoExclusive(True)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton { background-color: transparent; color: #4a5568; border: none; text-align: left; padding: 12px 20px; font-size: 14px; margin: 2px 10px; }
                    QPushButton:hover { background-color: #edf2f7; color: #1a202c; border-radius: 4px; }
                    QPushButton:checked { background-color: #00adb5; color: white; font-weight: bold; border-radius: 4px; }
                """)
                sidebar_layout.addWidget(btn)
                self.menu_buttons[view_name] = btn

        sidebar_layout.addStretch()
        
        self.logout_btn = QPushButton("Sign Out")
        self.logout_btn.setStyleSheet("color: #e53e3e; border: 1px solid #e53e3e; background-color: transparent; margin: 15px; padding: 8px; border-radius: 4px; font-weight: bold;")
        sidebar_layout.addWidget(self.logout_btn)
        main_layout.addWidget(sidebar)

        # Content Workspace Engine
        content_area = QWidget()
        content_area.setObjectName("mainContent")
        content_layout = QVBoxLayout(content_area)
        
        self.view_stack = QStackedWidget()

        # Dynamic View Loading
        for view_title in self.menu_buttons.keys():
            if view_title == "Dashboard":
                workspace_page = DashboardView(self.user, self.db_session)
            elif view_title == "System Users":
                workspace_page = UserManagementView(self.user, self.db_session)
            elif view_title == "Inventory Manager":
                workspace_page = ProductManagementView(self.user, self.db_session)
            elif view_title == "Customer Manager":
                workspace_page = CustomerManagementView(self.user, self.db_session)
            elif view_title == "Stock Take Audit":
                workspace_page = StockTakeManagementView(self.user, self.db_session)
            elif view_title == "Sales Terminal":
                workspace_page = SalesTerminalManagementView(self.user, self.db_session)
            elif view_title == "Shift Ledger":
                workspace_page = ShiftManagementView(self.user, self.db_session)
            elif view_title == "Analytics & Reports":
                workspace_page = AnalyticsReportsView(self.user, self.db_session)
            elif view_title == "Organization Settings":
                # FIXED: Passed self.user so the Admin check works!
                workspace_page = OrganizationSettingsView(self.user, self.db_session)
            else:
                workspace_page = QWidget()
                lbl_layout = QVBoxLayout(workspace_page)
                lbl = QLabel(f"Welcome to {view_title} System Space Workspace")
                lbl.setObjectName("viewTitle")
                lbl.setAlignment(Qt.AlignCenter)
                lbl_layout.addWidget(lbl)

            self.view_stack.addWidget(workspace_page)
            self.menu_buttons[view_title].clicked.connect(self.make_switch_callback(view_title, self.view_stack.count() - 1))

        content_layout.addWidget(self.view_stack)
        main_layout.addWidget(content_area)

        # Status Footer
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background-color: #ffffff; border-top: 1px solid #e1e4e8; padding: 2px 10px;")
        self.setStatusBar(self.status_bar)

        operator_info = QLabel(f"User: {self.user.name} | User Role: [{user_role_str}]")
        operator_info.setStyleSheet("color: #4a5568; font-weight: bold; font-size: 12px;")
        self.status_bar.addWidget(operator_info)

        branding_label = QLabel("Design and developed by Zola Technologies Limited | +254735296707")
        branding_label.setStyleSheet("color: #0018F9; font-size: 12px; font-weight: bold; padding-right: 10px;")
        self.status_bar.addPermanentWidget(branding_label)

        if self.menu_buttons:
            list(self.menu_buttons.values())[0].setChecked(True)

    def make_switch_callback(self, name, index):
        return lambda: self.view_stack.setCurrentIndex(index)

    def closeEvent(self, event):
        self.db_session.close()
        event.accept()