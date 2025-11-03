# -*- coding: utf-8 -*-
"""
GUI Styles Module
Contains all CSS styling definitions for the application.
"""

# Application-wide CSS styles with warm color scheme
APP_STYLESHEET = """
    QMainWindow {
        background-color: #f5f5f5;
        color: #333333;
    }
    QGroupBox {
        font-weight: bold;
        border: 2px solid #cccccc;
        border-radius: 8px;
        margin-top: 1ex;
        padding-top: 10px;
        background-color: #ffffff;
        color: #2c3e50;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px 0 5px;
        color: #e67e22;
        font-size: 14px;
    }
    QPushButton {
        background-color: #e67e22;
        border: none;
        color: white;
        padding: 10px 20px;
        text-align: center;
        font-size: 14px;
        font-weight: bold;
        border-radius: 6px;
        min-width: 100px;
    }
    QPushButton:hover {
        background-color: #d35400;
    }
    QPushButton:pressed {
        background-color: #a0522d;
    }
    QComboBox {
        border: 2px solid #bdc3c7;
        border-radius: 4px;
        padding: 6px;
        background-color: white;
        color: #2c3e50;
        font-size: 12px;
    }
    QComboBox:hover {
        border-color: #e67e22;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border-left: 2px solid #bdc3c7;
        background-color: #ecf0f1;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid #7f8c8d;
    }
    QComboBox QAbstractItemView {
        border: 2px solid #e67e22;
        border-radius: 4px;
        background-color: #fefefe;
        color: #2c3e50;
        selection-background-color: #e67e22;
        selection-color: white;
        outline: none;
    }
    QComboBox QAbstractItemView::item {
        background-color: #fefefe;
        color: #2c3e50;
        padding: 8px;
        border: none;
        min-height: 20px;
    }
    QComboBox QAbstractItemView::item:selected {
        background-color: #e67e22;
        color: white;
    }
    QComboBox QAbstractItemView::item:hover {
        background-color: #f39c12;
        color: white;
    }
    QTableWidget {
        gridline-color: #bdc3c7;
        background-color: white;
        alternate-background-color: #f8f9fa;
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        color: #2c3e50;
    }
    QTableWidget::item {
        padding: 8px;
        border-bottom: 1px solid #ecf0f1;
        color: #2c3e50;
    }
    QTableWidget::item:selected {
        background-color: #e67e22;
        color: white;
    }
    QHeaderView::section {
        background-color: #34495e;
        color: white;
        padding: 8px;
        border: none;
        font-weight: bold;
    }
    QTextEdit {
        border: 2px solid #bdc3c7;
        border-radius: 4px;
        background-color: #fefefe;
        color: #2c3e50;
        font-family: 'Courier New', monospace;
    }
    QTextEdit:focus {
        border-color: #e67e22;
    }
    QTabWidget::pane {
        border: 2px solid #bdc3c7;
        border-radius: 4px;
        background-color: white;
    }
    QTabBar::tab {
        background-color: #ecf0f1;
        color: #2c3e50;
        padding: 10px 25px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        font-weight: bold;
        min-width: 100px;
    }
    QTabBar::tab:selected {
        background-color: #e67e22;
        color: white;
    }
    QTabBar::tab:hover {
        background-color: #d35400;
        color: white;
    }
    QLabel {
        color: #2c3e50;
        font-weight: bold;
        font-size: 12px;
    }
    QSplitter::handle {
        background-color: #bdc3c7;
    }
    QSplitter::handle:horizontal {
        width: 3px;
    }
    QSplitter::handle:vertical {
        height: 3px;
    }
"""

# Color palettes for charts
WARM_COLORS = ['#e67e22', '#d35400', '#f39c12', '#e74c3c', '#c0392b']
WARM_RADAR_COLORS = ['#e67e22', '#d35400', '#f39c12', '#e74c3c', '#c0392b']

# Chart background colors
CHART_BACKGROUND_COLOR = '#fefefe'