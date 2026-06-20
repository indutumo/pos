from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QTimer, QMargins
from PySide6.QtCharts import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
from PySide6.QtGui import QPainter, QColor
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from app.models.schema import Sale, Product, BillReceipt, ReceiptStatus

class KPICard(QFrame):
    def __init__(self, title, value, color):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{ background-color: #ffffff; border-radius: 10px; border: 1px solid #e1e4e8; }}
            QLabel#Title {{ color: #718096; font-size: 12px; font-weight: 600; padding: 10px 15px 0 15px; }}
            QLabel#Value {{ color: #2b2d42; font-size: 22px; font-weight: bold; padding: 5px 15px 15px 15px; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.title_lbl = QLabel(title); self.title_lbl.setObjectName("Title")
        self.val_lbl = QLabel(value); self.val_lbl.setObjectName("Value")
        layout.addWidget(self.title_lbl); layout.addWidget(self.val_lbl)

    def update_value(self, value):
        self.val_lbl.setText(value)

class DashboardView(QWidget):
    def __init__(self, user, db_session):
        super().__init__()
        self.user = user
        self.db = db_session
        self.init_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_dashboard)
        self.timer.start(30000)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(20)

        # 1. KPI Header
        self.kpi_row = QHBoxLayout()
        stats = self.get_kpi_stats()
        self.card_sales = KPICard("Today's Sales", f"KES {stats['sales']:,.2f}", "#00adb5")
        self.card_pending = KPICard("Pending Receipts", f"{stats['pending']:,}", "#f39c12")
        self.card_low = KPICard("Low Stock Items", f"{stats['low_stock']:,}", "#e74c3c")
        
        self.kpi_row.addWidget(self.card_sales)
        self.kpi_row.addWidget(self.card_pending)
        self.kpi_row.addWidget(self.card_low)
        self.main_layout.addLayout(self.kpi_row)

        # 2. Main Content
        self.body_layout = QHBoxLayout()
        self.body_layout.setSpacing(20)
        
        self.chart_container = QVBoxLayout()
        self.tables_container = QVBoxLayout()
        self.tables_container.setSpacing(15)
        
        self.body_layout.addLayout(self.chart_container, stretch=1)
        self.body_layout.addLayout(self.tables_container, stretch=1)
        self.main_layout.addLayout(self.body_layout)
        
        self.refresh_dashboard()

    def refresh_dashboard(self):
        self.db.expire_all()
        stats = self.get_kpi_stats()
        self.card_sales.update_value(f"KES {stats['sales']:,.2f}")
        self.card_pending.update_value(f"{stats['pending']:,}")
        self.card_low.update_value(f"{stats['low_stock']:,}")
        
        self.update_chart()
        self.update_tables()

    def update_chart(self):
        while self.chart_container.count():
            item = self.chart_container.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        frame = QFrame()
        frame.setStyleSheet("background-color: white; border-radius: 10px; border: 1px solid #e1e4e8;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.addWidget(QLabel("<b>Sales Trend (Last 7 Days)</b>"))
        
        series = QBarSeries()
        bar_set = QBarSet("Revenue")
        bar_set.setColor(QColor("#00adb5"))
        
        data = self.get_trend_data()
        categories = []
        for date_obj, total in data:
            bar_set.append(float(total))
            categories.append(date_obj.strftime("%d/%m"))
        
        series.append(bar_set)
        chart = QChart()
        chart.addSeries(series)
        chart.setBackgroundBrush(QColor("transparent"))
        chart.setMargins(QMargins(0, 0, 0, 0))
        
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.0f") # Numeric clean formatting
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setStyleSheet("background-color: transparent;")
        layout.addWidget(chart_view)
        
        self.chart_container.addWidget(frame)

    def update_tables(self):
        while self.tables_container.count():
            item = self.tables_container.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        self.tables_container.addWidget(self.create_modern_table("Top Fast Moving", ["Product", "Qty"], self.get_top_products()))
        self.tables_container.addWidget(self.create_modern_table("Low Stock Alert", ["Product", "Qty"], self.get_low_stock()))

    def create_modern_table(self, title, headers, data):
        container = QFrame()
        container.setStyleSheet("background-color: white; border-radius: 10px; border: 1px solid #e1e4e8;")
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(15, 15, 15, 15)
        vbox.addWidget(QLabel(f"<b>{title}</b>"))
        
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(headers)
        
        # Explicit Header Alignment
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        table.setColumnWidth(1, 80)
        
        # Set alignment on individual header items
        for i in range(2):
            item = table.horizontalHeaderItem(i)
            if i == 0:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        table.setShowGrid(False)
        table.setStyleSheet("""
            QTableWidget { border: none; font-size: 13px; }
            QHeaderView::section { background: white; border: none; border-bottom: 2px solid #edf2f7; padding: 8px; color: #718096; font-weight: bold; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #edf2f7; }
        """)
        
        table.setRowCount(len(data))
        for r, (name, val) in enumerate(data):
            # Column 0: Product Name (Left Aligned)
            item_name = QTableWidgetItem(str(name))
            item_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            table.setItem(r, 0, item_name)
            
            # Column 1: Qty (Right Aligned)
            val_item = QTableWidgetItem(f"{val:,}") 
            val_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(r, 1, val_item)
            
        vbox.addWidget(table)
        return container

    def get_kpi_stats(self):
        today = datetime.utcnow().date()
        sales = self.db.query(func.sum(Sale.quantity * Sale.price)).filter(func.date(Sale.sale_date) == today).scalar() or 0
        pending = self.db.query(BillReceipt).filter(BillReceipt.status == ReceiptStatus.PENDING).count()
        low_stock = self.db.query(Product).filter(Product.quantity < 10).count()
        return {"sales": sales, "pending": pending, "low_stock": low_stock}

    def get_trend_data(self):
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        return self.db.query(func.date(Sale.sale_date), func.sum(Sale.quantity * Sale.price))\
                      .filter(Sale.sale_date >= seven_days_ago)\
                      .group_by(func.date(Sale.sale_date))\
                      .order_by(func.date(Sale.sale_date)).all()

    def get_top_products(self):
        return self.db.query(Product.name, func.sum(Sale.quantity)).join(Sale).group_by(Product.id).order_by(desc(func.sum(Sale.quantity))).limit(5).all()

    def get_low_stock(self):
        return self.db.query(Product.name, Product.quantity).filter(Product.quantity < 10).limit(5).all()