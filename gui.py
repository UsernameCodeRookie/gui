# -*- coding: utf-8 -*-
"""
PerfSimGUI
- Left panel: operator selector + operator XML + static architecture table (parameters, two rows)
- Right panel: simulation results (tabs)
    - Performance Table tab: performance table (top) + simulation log (bottom, with architecture selector)
    - Bar Chart tab: bar chart (matplotlib)
    - Radar Chart tab: radar chart (matplotlib)
"""

import sys
import json
import os
import re
import math

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QTextEdit, QTabWidget,
    QTableWidget, QTableWidgetItem, QLabel, QHeaderView,
    QComboBox, QGroupBox, QSplitter
)
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QPalette

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

# Configure matplotlib to support Chinese fonts
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

# SimulationRunner is expected to provide run(script_name, args, stdout_callback, stderr_callback, finished_callback)
from runner import SimulationRunner

# -------------------------------
# XML Syntax Highlighter
# -------------------------------
class XmlSyntaxHighlighter(QSyntaxHighlighter):
    """XML Syntax Highlighter for CGRA operator configuration files."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []
        
        # XML tag format - warm orange-brown color
        xml_tag_format = QTextCharFormat()
        xml_tag_format.setForeground(QColor(184, 107, 56))  # Warm orange-brown
        xml_tag_format.setFontWeight(QFont.Weight.Bold)
        
        # XML attribute name format - warm deep orange color
        xml_attr_name_format = QTextCharFormat()
        xml_attr_name_format.setForeground(QColor(204, 120, 50))  # Warm deep orange
        xml_attr_name_format.setFontWeight(QFont.Weight.Bold)
        
        # XML attribute value format - warm golden yellow color
        xml_attr_value_format = QTextCharFormat()
        xml_attr_value_format.setForeground(QColor(181, 137, 0))  # Warm golden yellow
        
        # XML comment format - warm beige color
        xml_comment_format = QTextCharFormat()
        xml_comment_format.setForeground(QColor(158, 134, 120))  # Warm beige
        xml_comment_format.setFontItalic(True)
        
        # XML keyword format (for special XML declarations) - warm red-brown color
        xml_keyword_format = QTextCharFormat()
        xml_keyword_format.setForeground(QColor(166, 89, 78))  # Warm red-brown
        xml_keyword_format.setFontWeight(QFont.Weight.Bold)
        
        # Define highlighting rules
        # XML tags: <tag> and </tag>
        self.highlighting_rules.append((
            QRegularExpression(r'</?[!]?[A-Za-z]+[^>]*>'),
            xml_tag_format
        ))
        
        # XML attribute names: attribute=
        self.highlighting_rules.append((
            QRegularExpression(r'\b[A-Za-z_][A-Za-z0-9_]*(?=\s*=)'),
            xml_attr_name_format
        ))
        
        # XML attribute values: "value" or 'value'
        self.highlighting_rules.append((
            QRegularExpression(r'"[^"]*"'),
            xml_attr_value_format
        ))
        self.highlighting_rules.append((
            QRegularExpression(r"'[^']*'"),
            xml_attr_value_format
        ))
        
        # XML comments: <!-- comment -->
        self.highlighting_rules.append((
            QRegularExpression(r'<!--.*-->'),
            xml_comment_format
        ))
        
        # XML processing instructions: <?xml ... ?>
        self.highlighting_rules.append((
            QRegularExpression(r'<\?.*\?>'),
            xml_keyword_format
        ))
        
        # XML CDATA sections: <![CDATA[ ... ]]>
        self.highlighting_rules.append((
            QRegularExpression(r'<!\[CDATA\[.*\]\]>'),
            xml_keyword_format
        ))
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to the given text block."""
        # Apply each highlighting rule
        for pattern, format_obj in self.highlighting_rules:
            expression = pattern
            match_iterator = expression.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format_obj)

# -------------------------------
# Utility: slugify operator name
# -------------------------------
def slugify(op_name: str) -> str:
    s = op_name.lower()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = s.strip('_')
    return s

# -------------------------------
# Load JSON configuration files
# -------------------------------
with open("architecture.json", "r", encoding="utf-8") as f:
    ARCH_DATA = json.load(f)

with open("operators.json", "r", encoding="utf-8") as f:
    OP_DATA = json.load(f)


class PerfSimGUI(QMainWindow):
    """Main GUI window for architecture performance simulation."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("架构性能对比")
        self.setGeometry(200, 100, 1400, 800)
        
        # Set modern application style
        self.setStyleSheet("""
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
        """)

        # Cache for logs keyed by "<operator>::<arch>"
        # value: string containing entire log (we append lines)
        self.log_cache = {}

        # Track running runners by key to avoid duplicate UI updates
        self.running_runners = set()

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        # -------------------------------
        # Left panel: operator + XML + architecture tables
        # -------------------------------
        operator_group = QGroupBox("选择算子")
        operator_layout = QVBoxLayout(operator_group)

        self.operator_combo = QComboBox()
        for op_name in OP_DATA.keys():
            self.operator_combo.addItem(op_name)
        operator_layout.addWidget(self.operator_combo)

        # Operator XML viewer with enhanced styling
        self.op_xml_view = QTextEdit()
        self.op_xml_view.setReadOnly(True)
        self.op_xml_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        mono = QFont("Courier New")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.op_xml_view.setFont(mono)
        
        # Apply XML syntax highlighting
        self.xml_highlighter = XmlSyntaxHighlighter(self.op_xml_view.document())

        # -------------------------------
        # Architecture tables (split into two rows) with enhanced styling
        # -------------------------------
        self.arch_table_top = QTableWidget(len(ARCH_DATA), 4)
        self.arch_table_top.setHorizontalHeaderLabels([
            "架构", "制程工艺 (nm)", "时钟频率 (MHz)", "面积 (mm²)"
        ])
        self.arch_table_top.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.arch_table_top.setEditTriggers(self.arch_table_top.EditTrigger.NoEditTriggers)
        self.arch_table_top.setAlternatingRowColors(True)

        self.arch_table_bottom = QTableWidget(len(ARCH_DATA), 5)
        self.arch_table_bottom.setHorizontalHeaderLabels([
            "核心数", "ALU/核心", "FPU/核心", "L1缓存", "L2缓存"
        ])
        self.arch_table_bottom.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.arch_table_bottom.setEditTriggers(self.arch_table_bottom.EditTrigger.NoEditTriggers)
        self.arch_table_bottom.setAlternatingRowColors(True)

        arch_splitter = QSplitter(Qt.Orientation.Vertical)
        arch_splitter.addWidget(self.arch_table_top)
        arch_splitter.addWidget(self.arch_table_bottom)
        arch_splitter.setSizes([130, 130])

        left_splitter = QSplitter(Qt.Orientation.Vertical)
        left_splitter.addWidget(self.op_xml_view)
        left_splitter.addWidget(arch_splitter)
        left_splitter.setSizes([320, 300])

        left_layout = QVBoxLayout()
        left_layout.addWidget(operator_group)
        left_layout.addWidget(QLabel("算子配置文件 (XML)"))
        left_layout.addWidget(left_splitter, stretch=1)

        self.run_btn = QPushButton("运行仿真")
        self.clear_btn = QPushButton("清除")
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.clear_btn)
        left_layout.addLayout(btn_layout)

        # -------------------------------
        # Right panel: tabs with enhanced styling
        # -------------------------------
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_table_tab(), "📊 性能表格")
        self.tabs.addTab(self.create_bar_chart_tab(), "📈 柱状图")
        self.tabs.addTab(self.create_radar_chart_tab(), "🎯 雷达图")

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.tabs)
        right_container = QWidget()
        right_container.setLayout(right_layout)

        main_layout.addLayout(left_layout, 3)
        main_layout.addWidget(right_container, 5)
        self.setCentralWidget(main_widget)

        # -------------------------------
        # Connections
        # -------------------------------
        self.run_btn.clicked.connect(self.run_simulation)
        self.clear_btn.clicked.connect(self.clear_all)

        # When operator changes, load XML and repopulate arch selector
        self.operator_combo.currentTextChanged.connect(self.load_selected_operator_xml)
        self.operator_combo.currentTextChanged.connect(self.populate_arch_selector)

        # Populate static data
        self.populate_arch_tables()
        self.populate_arch_selector()

        # Load initial operator XML
        self.load_selected_operator_xml()

    # -------------------------------
    # Populate architecture tables
    # -------------------------------
    def format_bytes(self, bytes_val):
        """Format bytes values to human readable format (KB, MB, etc.)"""
        if not isinstance(bytes_val, (int, float)) or bytes_val == 0:
            return "-"
        
        if bytes_val >= 1024*1024:
            return f"{bytes_val/(1024*1024):.1f} MB"
        elif bytes_val >= 1024:
            return f"{bytes_val/1024:.0f} KB"
        else:
            return f"{bytes_val} B"
    
    def populate_arch_tables(self):
        """Fill static architecture parameter tables from ARCH_DATA."""
        for i, arch in enumerate(ARCH_DATA.keys()):
            params = ARCH_DATA[arch]
            self.arch_table_top.setItem(i, 0, QTableWidgetItem(params.get("name", arch)))
            
            # Format numerical values properly
            process_val = params.get("process", "-")
            clock_rate_val = params.get("clock_rate", "-")
            area_val = params.get("area", "-")
            cores_val = params.get("cores", "-")
            alu_val = params.get("ALU_per_core", "-")
            fpu_val = params.get("FPU_per_core", "-")
            l1_val = params.get("L1_size", "-")
            l2_val = params.get("L2_size", "-")
            
            self.arch_table_top.setItem(i, 1, QTableWidgetItem(f"{process_val}" if process_val != "-" else "-"))
            self.arch_table_top.setItem(i, 2, QTableWidgetItem(f"{clock_rate_val:,}" if isinstance(clock_rate_val, (int, float)) else str(clock_rate_val)))
            self.arch_table_top.setItem(i, 3, QTableWidgetItem(f"{area_val}" if area_val != "-" else "-"))
            self.arch_table_bottom.setItem(i, 0, QTableWidgetItem(f"{cores_val}" if cores_val != "-" else "-"))
            self.arch_table_bottom.setItem(i, 1, QTableWidgetItem(f"{alu_val}" if alu_val != "-" else "-"))
            self.arch_table_bottom.setItem(i, 2, QTableWidgetItem(f"{fpu_val}" if fpu_val != "-" else "-"))
            self.arch_table_bottom.setItem(i, 3, QTableWidgetItem(self.format_bytes(l1_val)))
            self.arch_table_bottom.setItem(i, 4, QTableWidgetItem(self.format_bytes(l2_val)))
            
            # Center align architecture table content (except first column)
            for col in range(1, 4):
                if self.arch_table_top.item(i, col):
                    self.arch_table_top.item(i, col).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Center align all content in bottom table
            for col in range(5):
                if self.arch_table_bottom.item(i, col):
                    self.arch_table_bottom.item(i, col).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    # -------------------------------
    # Populate architecture selector (instead of tags)
    # -------------------------------
    def populate_arch_selector(self):
        """
        Populate arch_combo with architectures from the currently selected operator.
        Preferred default selection: CGRA if present, otherwise first.
        Ensure we don't connect update_log_view multiple times.
        """
        self.arch_combo.clear()
        selected_op = self.operator_combo.currentText()
        if not selected_op or selected_op not in OP_DATA:
            return

        # Add all available architectures for the selected operator
        arch_list = list(OP_DATA[selected_op].keys())
        for arch in arch_list:
            self.arch_combo.addItem(arch)

        # Prevent duplicate connections: disconnect if already connected
        try:
            self.arch_combo.currentTextChanged.disconnect(self.update_log_view)
        except Exception:
            # no-op if not previously connected
            pass

        # Connect log update
        self.arch_combo.currentTextChanged.connect(self.update_log_view)

        # Default selection rule:
        # 1) If "CGRA" exists, select it by default
        # 2) Otherwise, select the first available architecture
        if "CGRA" in arch_list:
            idx = arch_list.index("CGRA")
            self.arch_combo.setCurrentIndex(idx)
            # Update view for CGRA selection (will show CGRA hint or cached CGRA log)
            self.update_log_view("CGRA")
        elif self.arch_combo.count() > 0:
            self.arch_combo.setCurrentIndex(0)
            self.update_log_view(self.arch_combo.currentText())

    # -------------------------------
    # Helper: cache key for operator+arch
    # -------------------------------
    def _cache_key(self, operator: str, arch: str) -> str:
        """Unique cache key combining operator and architecture."""
        return f"{operator}::{arch}"

    # -------------------------------
    # Helper: append a line to log cache
    # -------------------------------
    def _append_to_log_cache(self, key: str, line: str):
        """Append a line (with newline) to the cache for the given key."""
        if key in self.log_cache:
            self.log_cache[key] += line + "\n"
        else:
            self.log_cache[key] = line + "\n"

    # -------------------------------
    # Update log view immediately when selecting architecture
    # -------------------------------
    def update_log_view(self, arch_name: str):
        """
        Show cached log for (current operator, arch) if present.
        If not cached:
          - for non-CGRA: read log_path into cache and display
          - for CGRA: show message indicating to Run Simulation (or show cached CGRA log if present)
        """
        self.perf_log.clear()
        selected_op = self.operator_combo.currentText()
        if not selected_op or arch_name not in OP_DATA[selected_op]:
            return

        key = self._cache_key(selected_op, arch_name)

        # If cached, display cache immediately
        if key in self.log_cache:
            self.perf_log.append(self.log_cache[key])
            return

        # Not cached yet
        metrics = OP_DATA[selected_op][arch_name]

        if arch_name == "CGRA":
            # If CGRA already running, show interim message and let callbacks update cache/UI later
            if key in self.running_runners:
                self.perf_log.append("[CGRA] CGRA simulation is running... logs will appear when available.\n")
            else:
                # show user hint to start CGRA simulation
                self.perf_log.append("[CGRA] No cached CGRA log. Click 'Run Simulation' to execute CGRA validation.\n")
            return

        # For non-CGRA architectures, read the existing log file (if any), cache it and display
        log_path = metrics.get("log_path", "")
        if log_path and os.path.isfile(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as lf:
                    content = lf.read()
                # Cache and display
                self.log_cache[key] = content
                self.perf_log.append(content)
            except Exception as e:
                self.perf_log.append(f"[{arch_name}] Error reading log file: {e}\n")
        else:
            self.perf_log.append(f"[{arch_name}] No log file found.\n")

    # -------------------------------
    # Create Performance Table tab
    # -------------------------------
    def create_table_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        perf_splitter = QSplitter(Qt.Orientation.Vertical)

        self.perf_table = QTableWidget(3, 7)
        self.perf_table.setHorizontalHeaderLabels([
            "架构", "周期数", "吞吐量 (GOPS)", "延迟 (ns)",
            "功耗 (W)", "能效 (GOPS/W)", "有效算力密度 (MOPS/mm²)"
        ])
        # Set more evenly distributed column widths for better balance
        self.perf_table.setColumnWidth(0, 120)  # Architecture - balanced
        self.perf_table.setColumnWidth(1, 120)  # Cycles - balanced
        self.perf_table.setColumnWidth(2, 120)  # Throughput - balanced
        self.perf_table.setColumnWidth(3, 120)  # Latency - balanced
        self.perf_table.setColumnWidth(4, 120)  # Power - balanced
        self.perf_table.setColumnWidth(5, 120)  # Efficiency - balanced
        # Allow last column to stretch for remaining space
        self.perf_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.perf_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.perf_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.perf_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.perf_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.perf_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self.perf_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.perf_table.setAlternatingRowColors(True)

        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)

        self.arch_combo = QComboBox()
        log_layout.addWidget(QLabel("选择架构查看日志"))
        log_layout.addWidget(self.arch_combo)

        self.perf_log = QTextEdit()
        self.perf_log.setReadOnly(True)
        mono = QFont("Courier New")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.perf_log.setFont(mono)
        log_layout.addWidget(self.perf_log)

        perf_splitter.addWidget(self.perf_table)
        perf_splitter.addWidget(log_widget)
        perf_splitter.setSizes([200, 420])

        layout.addWidget(perf_splitter)
        return widget

    # -------------------------------
    # Create Bar Chart tab
    # -------------------------------
    def create_bar_chart_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.bar_fig, self.bar_ax = plt.subplots()
        # Set warm color scheme for matplotlib
        self.bar_fig.patch.set_facecolor('#fefefe')
        self.bar_ax.set_facecolor('#fefefe')
        self.bar_canvas = FigureCanvas(self.bar_fig)
        layout.addWidget(self.bar_canvas)
        return widget

    # -------------------------------
    # Create Radar Chart tab
    # -------------------------------
    def create_radar_chart_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.radar_fig = plt.figure()
        # Set warm color scheme for matplotlib
        self.radar_fig.patch.set_facecolor('#fefefe')
        self.radar_ax = self.radar_fig.add_subplot(111, polar=True)
        self.radar_ax.set_facecolor('#fefefe')
        self.radar_canvas = FigureCanvas(self.radar_fig)
        layout.addWidget(self.radar_canvas)
        return widget

    # -------------------------------
    # Load operator XML
    # -------------------------------
    def load_selected_operator_xml(self):
        """Load operator-specific XML into the XML viewer (if present)."""
        selected_op = self.operator_combo.currentText()
        if not selected_op:
            self.op_xml_view.setPlainText("")
            return
        op_entry = OP_DATA.get(selected_op, {})
        cgra_entry = op_entry.get("CGRA", {})
        explicit_path = cgra_entry.get("config_xml")
        xml_text = None
        candidates = []
        if explicit_path:
            candidates.append(explicit_path)
        slug = slugify(selected_op)
        candidates.append(os.path.join("op_xml", f"{slug}.xml"))
        for path in candidates:
            try:
                if os.path.isfile(path):
                    with open(path, "r", encoding="utf-8") as xf:
                        xml_text = xf.read()
                        break
            except Exception:
                xml_text = None
        if xml_text is None:
            tried = "\n".join(candidates)
            xml_text = f"<!-- XML not found for operator: {selected_op} -->\n<!-- Tried paths:\n{tried}\n-->\n"
        self.op_xml_view.setPlainText(xml_text)

    # -------------------------------
    # Run simulation
    # -------------------------------
    def run_simulation(self):
        """
        Update performance table and, if the currently selected arch is CGRA,
        start the SimulationRunner. Runner callbacks append to cache; UI is updated
        only if the user still has that operator+arch selected.
        """
        # Do not clear perf_log here because user may be viewing other arch; we preserve current view.
        selected_op = self.operator_combo.currentText()
        selected_arch = self.arch_combo.currentText()
        if not selected_op or not selected_arch:
            self.perf_log.append("请先选择算子和架构。\n")
            return

        perf_data = OP_DATA[selected_op]

        # update perf table
        self.perf_table.setRowCount(len(perf_data))
        for i, arch in enumerate(perf_data.keys()):
            metrics = perf_data[arch]
            self.perf_table.setItem(i, 0, QTableWidgetItem(arch))
            
            # Format numerical values properly
            cycle_val = metrics.get("cycle", 0)
            throughput_val = metrics.get("throughput", 0)
            latency_val = metrics.get("latency", 0)
            power_val = metrics.get("power", 0)
            efficiency_val = metrics.get("efficiency", 0)
            density_val = metrics.get("density", 0)
            
            # Convert to proper formatted strings
            self.perf_table.setItem(i, 1, QTableWidgetItem(f"{cycle_val:,}" if isinstance(cycle_val, (int, float)) and cycle_val != 0 else "-"))
            self.perf_table.setItem(i, 2, QTableWidgetItem(f"{throughput_val:.2f}" if isinstance(throughput_val, (int, float)) and throughput_val != 0 else "-"))
            self.perf_table.setItem(i, 3, QTableWidgetItem(f"{latency_val:,}" if isinstance(latency_val, (int, float)) and latency_val != 0 else "-"))
            self.perf_table.setItem(i, 4, QTableWidgetItem(f"{power_val:.2f}" if isinstance(power_val, (int, float)) and power_val != 0 else "-"))
            self.perf_table.setItem(i, 5, QTableWidgetItem(f"{efficiency_val:.2f}" if isinstance(efficiency_val, (int, float)) and efficiency_val != 0 else "-"))
            self.perf_table.setItem(i, 6, QTableWidgetItem(f"{density_val:.2f}" if isinstance(density_val, (int, float)) and density_val != 0 else "-"))
            
            # Center align performance table content 
            for col in range(1, 7):
                if self.perf_table.item(i, col):
                    self.perf_table.item(i, col).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.bar_ax.clear()
        archs = list(perf_data.keys())
        metrics_keys = ["throughput", "latency", "power", "efficiency", "density"]
        metrics_labels = ["吞吐量 (GOPS)", "延迟 (ns)", "功耗 (W)", "能效 (GOPS/W)", "有效算力密度 (MOPS/mm²)"]
        num_metrics = len(metrics_keys)
        x = np.arange(len(archs))
        width = 0.15

        # Warm color palette for bars
        warm_colors = ['#e67e22', '#d35400', '#f39c12', '#e74c3c', '#c0392b']

        for idx, key in enumerate(metrics_keys):
            values = []
            for a in archs:
                v = perf_data[a].get(key, 1)
                val = float(v) if v else 1.0
                if val <= 0: val = 1e-3
                values.append(val)
            self.bar_ax.bar(x + (idx - num_metrics/2) * width + width/2, values, width, 
                           label=metrics_labels[idx], color=warm_colors[idx % len(warm_colors)], 
                           alpha=0.8, edgecolor='white', linewidth=1)

        self.bar_ax.set_xticks(x)
        self.bar_ax.set_xticklabels(archs, fontweight='bold', color='#2c3e50')
        self.bar_ax.set_ylabel("指标数值 (对数刻度)", fontweight='bold', color='#2c3e50')
        self.bar_ax.set_yscale("log")
        self.bar_ax.legend(fontsize=8, frameon=True, fancybox=True, shadow=True)
        self.bar_ax.grid(True, alpha=0.3, color='#bdc3c7')
        self.bar_ax.set_title("性能对比", fontweight='bold', color='#e67e22', fontsize=14)
        self.bar_canvas.draw()

        # Update radar chart with warm colors
        self.radar_ax.clear()
        metrics = ["吞吐量 (GOPS)", "延迟 (ns)", "功耗 (W)", "能效 (GOPS/W)", "有效算力密度 (MOPS/mm²)"]
        keys = ["throughput", "latency", "power", "efficiency", "density"]
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]

        # Warm color palette for radar chart
        warm_radar_colors = ['#e67e22', '#d35400', '#f39c12', '#e74c3c', '#c0392b']
        
        for idx, arch in enumerate(perf_data):
            raw_vals = []
            for k in keys:
                v = perf_data[arch].get(k, 1)
                vv = float(v) if v else 1.0
                if vv <= 0: vv = 1e-3
                raw_vals.append(vv)
            values = [math.log10(v + 1) for v in raw_vals]
            values += values[:1]
            color = warm_radar_colors[idx % len(warm_radar_colors)]
            self.radar_ax.plot(angles, values, label=arch, color=color, linewidth=2, alpha=0.8)
            self.radar_ax.fill(angles, values, alpha=0.2, color=color)

        self.radar_ax.set_xticks(angles[:-1])
        self.radar_ax.set_xticklabels(metrics, color='#2c3e50', fontweight='bold')
        self.radar_ax.set_ylabel("对数刻度", labelpad=20, color='#2c3e50', fontweight='bold')
        self.radar_ax.legend(fontsize=8, loc='upper right', bbox_to_anchor=(1.2, 1.0), 
                            frameon=True, fancybox=True, shadow=True)
        self.radar_ax.grid(True, alpha=0.3, color='#bdc3c7')
        self.radar_ax.set_title("性能雷达图", fontweight='bold', color='#e67e22', 
                               fontsize=14, pad=20)
        self.radar_canvas.draw()

        # log and run simulation
        self.perf_log.append(f"正在运行仿真: {selected_op} (架构: {selected_arch})\n")
        metrics = perf_data[selected_arch]

        if selected_arch == "CGRA":
            # Start CGRA simulation via SimulationRunner.
            # Callbacks will append lines to cache and update UI only when current selection matches.
            key = self._cache_key(selected_op, selected_arch)

            # mark runner as running
            self.running_runners.add(key)

            # ensure cache entry exists so UI shows incremental logs
            if key not in self.log_cache:
                self.log_cache[key] = ""
                
        

            self.sim_runner = SimulationRunner(script_dir="../CGRA_rebuild")
            config_xml_path = metrics.get("config_xml", "")
            script_name = "validation.py"
            args = [config_xml_path] if config_xml_path else []

            # define callbacks that append to cache and update UI only if still selected
            def stdout_callback(line: str, _op=selected_op, _arch=selected_arch):
                k = self._cache_key(_op, _arch)
                # append to cache
                self._append_to_log_cache(k, line)
                # update UI only if user currently views this operator+arch
                if self.operator_combo.currentText() == _op and self.arch_combo.currentText() == _arch:
                    # replace entire text with cached content (keeps UI consistent)
                    self.perf_log.clear()
                    self.perf_log.append(self.log_cache[k])
                    self.perf_log.verticalScrollBar().setValue(self.perf_log.verticalScrollBar().maximum())

            def stderr_callback(line: str, _op=selected_op, _arch=selected_arch):
                # treat stderr similarly (prefix with [ERR])
                out_line = f"[ERR] {line}"
                k = self._cache_key(_op, _arch)
                self._append_to_log_cache(k, out_line)
                if self.operator_combo.currentText() == _op and self.arch_combo.currentText() == _arch:
                    self.perf_log.clear()
                    self.perf_log.append(self.log_cache[k])
                    self.perf_log.verticalScrollBar().setValue(self.perf_log.verticalScrollBar().maximum())

            def finished_callback(_op=selected_op, _arch=selected_arch):
                k = self._cache_key(_op, _arch)
                self._append_to_log_cache(k, "[Finished]")
                # remove running marker
                try:
                    self.running_runners.remove(k)
                except KeyError:
                    pass
                # update UI only if user still views this operator+arch
                if self.operator_combo.currentText() == _op and self.arch_combo.currentText() == _arch:
                    self.perf_log.clear()
                    self.perf_log.append(self.log_cache[k])
                    self.perf_log.verticalScrollBar().setValue(self.perf_log.verticalScrollBar().maximum())

            # start the runner
            self.sim_runner.run(
                script_name,
                args=args,
                stdout_callback=stdout_callback,
                stderr_callback=stderr_callback,
                finished_callback=finished_callback
            )
        else:
            # Non-CGRA: logs are handled immediately in update_log_view when arch selection changes.
            # Here we simply ensure the log for the selected arch is loaded into cache and UI.
            key = self._cache_key(selected_op, selected_arch)
            metrics = perf_data[selected_arch]
            log_path = metrics.get("log_path", "")
            if log_path and os.path.isfile(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8") as lf:
                        content = lf.read()
                    self.log_cache[key] = content
                    # Only update UI if user still viewing this operator+arch
                    if self.operator_combo.currentText() == selected_op and self.arch_combo.currentText() == selected_arch:
                        self.perf_log.clear()
                        self.perf_log.append(content)
                except Exception as e:
                    self.perf_log.append(f"[{selected_arch}] Error reading log file: {e}\n")
            else:
                self.perf_log.append(f"[{selected_arch}] No log file found.\n")

    # -------------------------------
    # Clear all runtime outputs
    # -------------------------------
    def clear_all(self):
        """Clear GUI runtime outputs and caches related to logs."""
        self.perf_log.clear()
        self.op_xml_view.clear()
        self.perf_table.clearContents()
        self.bar_ax.clear()
        self.bar_canvas.draw()
        self.radar_ax.clear()
        self.radar_canvas.draw()
        # Clear caches and running markers
        self.log_cache.clear()
        self.running_runners.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = PerfSimGUI()
    gui.show()
    sys.exit(app.exec())
