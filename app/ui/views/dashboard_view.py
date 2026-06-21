from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QGraphicsDropShadowEffect, QToolTip,
)
from PySide6.QtCore import Qt, QTimer, QMargins
from PySide6.QtCharts import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
from PySide6.QtGui import QPainter, QColor, QCursor
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from app.models.schema import Sale, Product, BillReceipt, ReceiptStatus


def format_currency(value):
    """KES amount with thousands separators, e.g. KES 12,345.00"""
    return f"KES {float(value):,.2f}"


class KPICard(QFrame):
    """
    A modern stat card: a coloured accent strip, an uppercase label, and a
    large value — with a soft drop shadow instead of a flat border for
    visual depth.
    """

    def __init__(self, title, value, color):
        super().__init__()
        self.setObjectName("KPICard")
        self.setStyleSheet(f"""
            QFrame#KPICard {{
                background-color: #ffffff;
                border-radius: 14px;
                border: 1px solid #eef0f3;
            }}
            QLabel#Title {{
                color: #8a8f98;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            QLabel#Value {{
                color: #1f2430;
                font-size: 25px;
                font-weight: 800;
            }}
        """)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        accent = QFrame()
        accent.setFixedWidth(5)
        accent.setStyleSheet(
            f"background-color: {color}; border-top-left-radius: 14px; border-bottom-left-radius: 14px;"
        )
        outer.addWidget(accent)

        body = QVBoxLayout()
        body.setContentsMargins(18, 16, 18, 16)
        body.setSpacing(6)

        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setObjectName("Title")
        self.val_lbl = QLabel(value)
        self.val_lbl.setObjectName("Value")

        body.addWidget(self.title_lbl)
        body.addWidget(self.val_lbl)
        outer.addLayout(body)

        _apply_card_shadow(self)

    def update_value(self, value):
        self.val_lbl.setText(value)


def _apply_card_shadow(widget):
    """Soft, consistent drop shadow used on every card-style surface."""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(20)
    shadow.setOffset(0, 6)
    shadow.setColor(QColor(31, 36, 48, 28))
    widget.setGraphicsEffect(shadow)


class DashboardView(QWidget):
    def __init__(self, user, db_session):
        super().__init__()
        self.user = user
        self.db = db_session
        self._trend_values = []
        self.init_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_dashboard)
        self.timer.start(30000)

    def init_ui(self):
        self.setStyleSheet("QWidget { background-color: #f4f6f8; font-family: 'Segoe UI', Arial, sans-serif; }")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(20)

        # 0. Page header
        header_row = QHBoxLayout()
        page_title = QLabel("Dashboard")
        page_title.setStyleSheet("color: #1f2430; font-size: 22px; font-weight: 800;")
        self.updated_lbl = QLabel("")
        self.updated_lbl.setStyleSheet("color: #8a8f98; font-size: 12px;")
        header_row.addWidget(page_title)
        header_row.addStretch()
        header_row.addWidget(self.updated_lbl)
        self.main_layout.addLayout(header_row)

        # 1. KPI Header
        self.kpi_row = QHBoxLayout()
        self.kpi_row.setSpacing(18)
        stats = self.get_kpi_stats()
        self.card_sales = KPICard("Today's Sales", format_currency(stats["sales"]), "#00adb5")
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
        self.tables_container.setSpacing(18)

        self.body_layout.addLayout(self.chart_container, stretch=1)
        self.body_layout.addLayout(self.tables_container, stretch=1)
        self.main_layout.addLayout(self.body_layout)

        self.refresh_dashboard()

    def refresh_dashboard(self):
        self.db.expire_all()
        stats = self.get_kpi_stats()
        self.card_sales.update_value(format_currency(stats["sales"]))
        self.card_pending.update_value(f"{stats['pending']:,}")
        self.card_low.update_value(f"{stats['low_stock']:,}")
        self.updated_lbl.setText(f"Updated {datetime.now().strftime('%H:%M:%S')}")

        self.update_chart()
        self.update_tables()

    # ------------------------------------------------------------------
    # Chart
    # ------------------------------------------------------------------

    def update_chart(self):
        while self.chart_container.count():
            item = self.chart_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        frame = QFrame()
        frame.setObjectName("ChartCard")
        frame.setStyleSheet("""
            QFrame#ChartCard { background-color: #ffffff; border-radius: 14px; border: 1px solid #eef0f3; }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 14)
        layout.setSpacing(10)

        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        title_lbl = QLabel("Sales Trend")
        title_lbl.setStyleSheet("color: #1f2430; font-size: 14px; font-weight: 700;")
        subtitle_lbl = QLabel("Last 7 days revenue — hover a bar for the exact amount")
        subtitle_lbl.setStyleSheet("color: #8a8f98; font-size: 11px;")
        header_box.addWidget(title_lbl)
        header_box.addWidget(subtitle_lbl)
        layout.addLayout(header_box)

        data = self.get_trend_data()
        self._trend_values = [float(total) for _, total in data]
        categories = [date_obj.strftime("%a %d") for date_obj, _ in data]

        if not self._trend_values:
            empty_lbl = QLabel("No sales recorded in the last 7 days")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #8a8f98; font-size: 12px; padding: 50px 0;")
            layout.addWidget(empty_lbl)
            self.chart_container.addWidget(frame)
            _apply_card_shadow(frame)
            return

        series = QBarSeries()
        series.setBarWidth(0.55)
        bar_set = QBarSet("Revenue")
        bar_set.setColor(QColor("#00adb5"))
        bar_set.setBorderColor(QColor("#00adb5"))
        for value in self._trend_values:
            bar_set.append(value)
        series.append(bar_set)
        # Show the exact comma-formatted amount as a tooltip when a bar is
        # hovered, since the axis itself can only render plain numbers.
        series.hovered.connect(self._on_bar_hovered)

        chart = QChart()
        chart.addSeries(series)
        chart.setBackgroundBrush(QColor("transparent"))
        chart.setMargins(QMargins(0, 0, 0, 0))
        chart.legend().setVisible(False)
        chart.setAnimationOptions(QChart.SeriesAnimations)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsColor(QColor("#8a8f98"))
        axis_x.setGridLineVisible(False)
        axis_x.setLinePenColor(QColor("#e7eaee"))
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.0f")
        axis_y.setLabelsColor(QColor("#8a8f98"))
        axis_y.setGridLineColor(QColor("#f0f2f5"))
        axis_y.setLinePenColor(QColor("transparent"))
        top_value = max(self._trend_values) if self._trend_values else 0
        axis_y.setRange(0, top_value * 1.2 if top_value > 0 else 10)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setStyleSheet("background-color: transparent;")
        chart_view.setMinimumHeight(260)
        layout.addWidget(chart_view)

        self.chart_container.addWidget(frame)
        _apply_card_shadow(frame)

    def _on_bar_hovered(self, status, index, bar_set=None):
        if status and 0 <= index < len(self._trend_values):
            QToolTip.showText(QCursor.pos(), format_currency(self._trend_values[index]))
        else:
            QToolTip.hideText()

    # ------------------------------------------------------------------
    # Tables
    # ------------------------------------------------------------------

    def update_tables(self):
        while self.tables_container.count():
            item = self.tables_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.tables_container.addWidget(
            self.create_modern_table(
                "Top Fast Moving", "Best sellers by quantity",
                ["Product", "Qty"], self.get_top_products(),
                empty_text="No sales recorded yet",
            )
        )
        self.tables_container.addWidget(
            self.create_modern_table(
                "Low Stock Alert", "Below 10 units on hand",
                ["Product", "Qty"], self.get_low_stock(),
                empty_text="Nothing is currently low on stock",
            )
        )

    def create_modern_table(self, title, subtitle, headers, data, empty_text="No data available"):
        container = QFrame()
        container.setObjectName("TableCard")
        container.setStyleSheet("""
            QFrame#TableCard { background-color: #ffffff; border-radius: 14px; border: 1px solid #eef0f3; }
        """)
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(20, 18, 20, 18)
        vbox.setSpacing(10)

        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #1f2430; font-size: 14px; font-weight: 700;")
        subtitle_lbl = QLabel(subtitle)
        subtitle_lbl.setStyleSheet("color: #8a8f98; font-size: 11px;")
        header_box.addWidget(title_lbl)
        header_box.addWidget(subtitle_lbl)
        vbox.addLayout(header_box)

        if not data:
            empty_lbl = QLabel(empty_text)
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #8a8f98; font-size: 12px; padding: 30px 0;")
            vbox.addWidget(empty_lbl)
            _apply_card_shadow(container)
            return container

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)

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

        table.setStyleSheet("""
            QTableWidget { border: none; font-size: 13px; background: transparent; }
            QTableWidget::item { padding: 9px 4px; border-bottom: 1px solid #f0f2f5; }
            QTableWidget::item:alternate { background-color: #fafbfc; }
            QTableWidget::item:hover { background-color: #f3f9fa; }
            QHeaderView::section {
                background: white; border: none; border-bottom: 2px solid #edf2f7;
                padding: 8px 4px; color: #8a8f98; font-weight: 700; font-size: 11px;
            }
        """)

        table.setRowCount(len(data))
        for r, (name, val) in enumerate(data):
            # Column 0: Product Name (Left Aligned)
            item_name = QTableWidgetItem(str(name))
            item_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            table.setItem(r, 0, item_name)

            # Column 1: Qty (Right Aligned, thousands separated)
            val_item = QTableWidgetItem(f"{val:,}")
            val_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(r, 1, val_item)

        vbox.addWidget(table)
        _apply_card_shadow(container)
        return container

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

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