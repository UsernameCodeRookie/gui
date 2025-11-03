# -*- coding: utf-8 -*-
"""
PerfSimGUI - Modularized Version
- Left panel: operator selector + operator XML + static architecture table (parameters, two rows)
- Right panel: simulation results (tabs)
    - Performance Table tab: performance table (top) + simulation log (bottom, with architecture selector)
    - Bar Chart tab: bar chart (matplotlib)
    - Radar Chart tab: radar chart (matplotlib)
"""

import sys
import json
import os

# Add current directory to Python path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QTextEdit, QTabWidget,
    QTableWidget, QTableWidgetItem, QLabel, QHeaderView,
    QComboBox, QGroupBox, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import matplotlib

# Import our custom modules
from ui.xml_highlighter import XmlSyntaxHighlighter
from ui.styles import APP_STYLESHEET, CHART_BACKGROUND_COLOR
from ui.charts import update_bar_chart, update_radar_chart, setup_chart_style
from utils import slugify, format_bytes, format_number_with_commas, format_float_precision, cache_key

# Configure matplotlib to support Chinese fonts and fix unicode issues
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans', 'Arial', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family'] = 'sans-serif'

# Use CGRAValidationThread for running CGRA validation in background
from thread import CGRAValidationThread
from resource_path import get_resource_path, get_project_root, get_config_path


# -------------------------------
# Load JSON configuration files
# -------------------------------
# Get the project root directory (works in both dev and packaged environments)
PROJECT_ROOT = get_project_root()

with open(get_config_path("architecture.json"), "r", encoding="utf-8") as f:
    ARCH_DATA = json.load(f)

with open(get_config_path("operators.json"), "r", encoding="utf-8") as f:
    OP_DATA = json.load(f)


class PerfSimGUI(QMainWindow):
    """Main GUI window for architecture performance simulation."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("架构性能对比")
        self.setGeometry(200, 100, 1400, 800)
        
        # Apply modular stylesheet
        self.setStyleSheet(APP_STYLESHEET)

        # Cache for logs keyed by "<operator>::<arch>"
        # value: string containing entire log (we append lines)
        self.log_cache = {}

        # Track running runners by key to avoid duplicate UI updates
        self.running_runners = set()
        
        # Track active validation threads
        self.validation_threads = {}

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
    def populate_arch_tables(self):
        """Fill static architecture parameter tables from ARCH_DATA."""
        for i, arch in enumerate(ARCH_DATA.keys()):
            params = ARCH_DATA[arch]
            self.arch_table_top.setItem(i, 0, QTableWidgetItem(params.get("name", arch)))
            
            # Format numerical values properly using utility functions
            process_val = params.get("process", "-")
            clock_rate_val = params.get("clock_rate", "-")
            area_val = params.get("area", "-")
            cores_val = params.get("cores", "-")
            alu_val = params.get("ALU_per_core", "-")
            fpu_val = params.get("FPU_per_core", "-")
            l1_val = params.get("L1_size", "-")
            l2_val = params.get("L2_size", "-")
            
            self.arch_table_top.setItem(i, 1, QTableWidgetItem(f"{process_val}" if process_val != "-" else "-"))
            self.arch_table_top.setItem(i, 2, QTableWidgetItem(format_number_with_commas(clock_rate_val) if isinstance(clock_rate_val, (int, float)) else str(clock_rate_val)))
            self.arch_table_top.setItem(i, 3, QTableWidgetItem(f"{area_val}" if area_val != "-" else "-"))
            self.arch_table_bottom.setItem(i, 0, QTableWidgetItem(f"{cores_val}" if cores_val != "-" else "-"))
            self.arch_table_bottom.setItem(i, 1, QTableWidgetItem(f"{alu_val}" if alu_val != "-" else "-"))
            self.arch_table_bottom.setItem(i, 2, QTableWidgetItem(f"{fpu_val}" if fpu_val != "-" else "-"))
            self.arch_table_bottom.setItem(i, 3, QTableWidgetItem(format_bytes(l1_val)))
            self.arch_table_bottom.setItem(i, 4, QTableWidgetItem(format_bytes(l2_val)))
            
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
    # Helper: append a line to log cache
    # -------------------------------
    def _append_to_log_cache(self, key: str, line: str):
        """Append a line (with newline) to the cache for the given key."""
        if key in self.log_cache:
            self.log_cache[key] += line + "\n"
        else:
            self.log_cache[key] = line + "\n"
    
    def _get_task_name_from_operator(self, operator_name: str) -> str:
        """
        Map operator name to task name for CGRA validation.
        Extracts the operator type from names like "GEMM M=64 N=64 K=64" -> "gemm_fp32_slice16"
        """
        # Extract the base operator type (first word before space or the whole name)
        base_op = operator_name.split()[0] if ' ' in operator_name else operator_name
        
        # Mapping from operator type to task directory name
        task_mapping = {
            "Conv2d": "conv_fp32_slice16",
            "GEMM": "gemm_fp32_slice16",
            "FFT": "fft_slice16",
            # Add more mappings as needed
        }
        
        return task_mapping.get(base_op, base_op.lower() + "_fp32_slice16")

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

        key = cache_key(selected_op, arch_name)

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
        setup_chart_style(self.bar_fig, self.bar_ax)
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
        self.radar_fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
        self.radar_ax = self.radar_fig.add_subplot(111, polar=True)
        self.radar_ax.set_facecolor(CHART_BACKGROUND_COLOR)
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
            # Normalize path separators for cross-platform compatibility
            explicit_path = explicit_path.replace("/", os.sep).replace("\\", os.sep)
            
            # Handle both absolute and relative paths
            # If relative path starts with ./, resolve it relative to PROJECT_ROOT
            if explicit_path.startswith("." + os.sep):
                abs_path = os.path.normpath(os.path.join(PROJECT_ROOT, explicit_path[2:]))
                candidates.append(abs_path)
            else:
                candidates.append(os.path.normpath(explicit_path))
                # Also try relative to PROJECT_ROOT
                candidates.append(os.path.normpath(os.path.join(PROJECT_ROOT, explicit_path)))
        slug = slugify(selected_op)
        candidates.append(os.path.normpath(os.path.join(PROJECT_ROOT, "op_xml", f"{slug}.xml")))
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
            
            # Format numerical values properly using utility functions
            cycle_val = metrics.get("cycle", 0)
            throughput_val = metrics.get("throughput", 0)
            latency_val = metrics.get("latency", 0)
            power_val = metrics.get("power", 0)
            efficiency_val = metrics.get("efficiency", 0)
            density_val = metrics.get("density", 0)
            
            # Convert to proper formatted strings
            self.perf_table.setItem(i, 1, QTableWidgetItem(format_number_with_commas(cycle_val)))
            self.perf_table.setItem(i, 2, QTableWidgetItem(format_float_precision(throughput_val)))
            self.perf_table.setItem(i, 3, QTableWidgetItem(format_number_with_commas(latency_val)))
            self.perf_table.setItem(i, 4, QTableWidgetItem(format_float_precision(power_val)))
            self.perf_table.setItem(i, 5, QTableWidgetItem(format_float_precision(efficiency_val)))
            self.perf_table.setItem(i, 6, QTableWidgetItem(format_float_precision(density_val)))
            
            # Center align performance table content 
            for col in range(1, 7):
                if self.perf_table.item(i, col):
                    self.perf_table.item(i, col).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        # Update charts using modular functions
        update_bar_chart(self.bar_ax, self.bar_canvas, perf_data)
        update_radar_chart(self.radar_ax, self.radar_canvas, perf_data)

        # log and run simulation
        self.perf_log.append(f"正在运行仿真: {selected_op} (架构: {selected_arch})\n")
        metrics = perf_data[selected_arch]

        if selected_arch == "CGRA":
            # Start CGRA simulation via CGRAValidationThread.
            # Callbacks will append lines to cache and update UI only when current selection matches.
            key = cache_key(selected_op, selected_arch)

            # mark runner as running
            self.running_runners.add(key)

            # ensure cache entry exists so UI shows incremental logs
            if key not in self.log_cache:
                self.log_cache[key] = ""

            # Extract task name from config_xml path or use operator name
            config_xml_path = metrics.get("config_xml", "")
            # Assume task name is derived from operator (e.g., "Conv2d" -> "conv_fp32_slice16")
            # You may need to adjust this mapping based on your actual task names
            task_name = self._get_task_name_from_operator(selected_op)
            
            # Create validation thread
            # resource_dir parameter will point to data folder, and defaults will be used for input/output
            thread = CGRAValidationThread(
                task=task_name,
                resource_dir=os.path.join(PROJECT_ROOT, "data")
            )
            
            # define callbacks that append to cache and update UI only if still selected
            def stdout_callback(line: str, _op=selected_op, _arch=selected_arch):
                k = cache_key(_op, _arch)
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
                k = cache_key(_op, _arch)
                self._append_to_log_cache(k, out_line)
                if self.operator_combo.currentText() == _op and self.arch_combo.currentText() == _arch:
                    self.perf_log.clear()
                    self.perf_log.append(self.log_cache[k])
                    self.perf_log.verticalScrollBar().setValue(self.perf_log.verticalScrollBar().maximum())

            def finished_callback(success: bool, _op=selected_op, _arch=selected_arch):
                k = cache_key(_op, _arch)
                result_msg = "[Validation Passed]" if success else "[Validation Failed]"
                self._append_to_log_cache(k, result_msg)
                # remove running marker
                try:
                    self.running_runners.remove(k)
                    if k in self.validation_threads:
                        del self.validation_threads[k]
                except KeyError:
                    pass
                # update UI only if user still views this operator+arch
                if self.operator_combo.currentText() == _op and self.arch_combo.currentText() == _arch:
                    self.perf_log.clear()
                    self.perf_log.append(self.log_cache[k])
                    self.perf_log.verticalScrollBar().setValue(self.perf_log.verticalScrollBar().maximum())

            # Connect signals
            thread.stdout_signal.connect(stdout_callback)
            thread.stderr_signal.connect(stderr_callback)
            thread.finished_signal.connect(finished_callback)
            
            # Store thread reference and start
            self.validation_threads[key] = thread
            thread.start()
        else:
            # Non-CGRA: logs are handled immediately in update_log_view when arch selection changes.
            # Here we simply ensure the log for the selected arch is loaded into cache and UI.
            key = cache_key(selected_op, selected_arch)
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
        # Stop and clear any running validation threads
        for thread in self.validation_threads.values():
            if thread.isRunning():
                thread.stop()
                thread.wait(1000)  # Wait up to 1 second for thread to finish
        self.validation_threads.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = PerfSimGUI()
    gui.show()
    sys.exit(app.exec())