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
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import numpy as np

# SimulationRunner is expected to provide run(script_name, args, stdout_callback, stderr_callback, finished_callback)
from runner import SimulationRunner

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
        self.setWindowTitle("Architecture Performance Comparison")
        self.setGeometry(200, 100, 1400, 800)

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
        operator_group = QGroupBox("Select Operator")
        operator_layout = QVBoxLayout(operator_group)

        self.operator_combo = QComboBox()
        for op_name in OP_DATA.keys():
            self.operator_combo.addItem(op_name)
        operator_layout.addWidget(self.operator_combo)

        # Operator XML viewer
        self.op_xml_view = QTextEdit()
        self.op_xml_view.setReadOnly(True)
        self.op_xml_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        mono = QFont("Courier New")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.op_xml_view.setFont(mono)

        # -------------------------------
        # Architecture tables (split into two rows)
        # -------------------------------
        self.arch_table_top = QTableWidget(len(ARCH_DATA), 4)
        self.arch_table_top.setHorizontalHeaderLabels([
            "Architecture", "Process Node (nm)", "Clock Rate (MHz)", "Area (mm^2)"
        ])
        self.arch_table_top.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.arch_table_top.setEditTriggers(self.arch_table_top.EditTrigger.NoEditTriggers)

        self.arch_table_bottom = QTableWidget(len(ARCH_DATA), 5)
        self.arch_table_bottom.setHorizontalHeaderLabels([
            "Cores", "ALU/core", "FPU/core", "L1_size", "L2_size"
        ])
        self.arch_table_bottom.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.arch_table_bottom.setEditTriggers(self.arch_table_bottom.EditTrigger.NoEditTriggers)

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
        left_layout.addWidget(QLabel("Operator Config Word (XML)"))
        left_layout.addWidget(left_splitter, stretch=1)

        self.run_btn = QPushButton("Run Simulation")
        self.clear_btn = QPushButton("Clear")
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.clear_btn)
        left_layout.addLayout(btn_layout)

        # -------------------------------
        # Right panel: tabs
        # -------------------------------
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_table_tab(), "Performance Table")
        self.tabs.addTab(self.create_bar_chart_tab(), "Bar Chart")
        self.tabs.addTab(self.create_radar_chart_tab(), "Radar Chart")

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
            self.arch_table_top.setItem(i, 1, QTableWidgetItem(str(params.get("process", "-"))))
            self.arch_table_top.setItem(i, 2, QTableWidgetItem(str(params.get("clock_rate", "-"))))
            self.arch_table_top.setItem(i, 3, QTableWidgetItem(str(params.get("area", "-"))))
            self.arch_table_bottom.setItem(i, 0, QTableWidgetItem(str(params.get("cores", "-"))))
            self.arch_table_bottom.setItem(i, 1, QTableWidgetItem(str(params.get("ALU_per_core", "-"))))
            self.arch_table_bottom.setItem(i, 2, QTableWidgetItem(str(params.get("FPU_per_core", "-"))))
            self.arch_table_bottom.setItem(i, 3, QTableWidgetItem(str(params.get("L1_size", "-"))))
            self.arch_table_bottom.setItem(i, 4, QTableWidgetItem(str(params.get("L2_size", "-"))))

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
            "Architecture", "Cycles", "Throughput (GOPS)", "Latency (ns)",
            "Power (W)", "Efficiency (GOPS/W)", "Compute Density (MOPS/mm^2)"
        ])
        self.perf_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)

        self.arch_combo = QComboBox()
        log_layout.addWidget(QLabel("Select Architecture for Logs"))
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
        self.radar_ax = self.radar_fig.add_subplot(111, polar=True)
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
            self.perf_log.append("Please select operator and architecture first.\n")
            return

        perf_data = OP_DATA[selected_op]

        # update perf table
        self.perf_table.setRowCount(len(perf_data))
        for i, arch in enumerate(perf_data.keys()):
            metrics = perf_data[arch]
            self.perf_table.setItem(i, 0, QTableWidgetItem(arch))
            self.perf_table.setItem(i, 1, QTableWidgetItem(str(metrics.get("cycle", "-"))))
            self.perf_table.setItem(i, 2, QTableWidgetItem(str(metrics.get("throughput", "-"))))
            self.perf_table.setItem(i, 3, QTableWidgetItem(str(metrics.get("latency", "-"))))
            self.perf_table.setItem(i, 4, QTableWidgetItem(str(metrics.get("power", "-"))))
            self.perf_table.setItem(i, 5, QTableWidgetItem(str(metrics.get("efficiency", "-"))))
            self.perf_table.setItem(i, 6, QTableWidgetItem(str(metrics.get("density", "-"))))

        self.bar_ax.clear()
        archs = list(perf_data.keys())
        metrics_keys = ["throughput", "latency", "power", "efficiency", "density"]
        metrics_labels = ["Throughput (GOPS)", "Latency (ns)", "Power (W)", "Efficiency (GOPS/W)", "Compute Density (MOPS/mm^2)"]
        num_metrics = len(metrics_keys)
        x = np.arange(len(archs))
        width = 0.15

        for idx, key in enumerate(metrics_keys):
            values = []
            for a in archs:
                v = perf_data[a].get(key, 1)
                val = float(v) if v else 1.0
                if val <= 0: val = 1e-3
                values.append(val)
            self.bar_ax.bar(x + (idx - num_metrics/2) * width + width/2, values, width, label=metrics_labels[idx])

        self.bar_ax.set_xticks(x)
        self.bar_ax.set_xticklabels(archs)
        self.bar_ax.set_ylabel("Metric Values (log scale)")
        self.bar_ax.set_yscale("log")
        self.bar_ax.legend(fontsize=8)
        self.bar_canvas.draw()

        # Update radar chart
        self.radar_ax.clear()
        metrics = ["Throughput (GOPS)", "Latency (ns)", "Power (W)", "Energy Efficiency (GOPS/W)", "Compute Density (MOPS/mm^2)"]
        keys = ["throughput", "latency", "power", "efficiency", "density"]
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]

        for arch in perf_data:
            raw_vals = []
            for k in keys:
                v = perf_data[arch].get(k, 1)
                vv = float(v) if v else 1.0
                if vv <= 0: vv = 1e-3
                raw_vals.append(vv)
            values = [math.log10(v + 1) for v in raw_vals]
            values += values[:1]
            self.radar_ax.plot(angles, values, label=arch)
            self.radar_ax.fill(angles, values, alpha=0.25)

        self.radar_ax.set_xticks(angles[:-1])
        self.radar_ax.set_xticklabels(metrics)
        self.radar_ax.set_ylabel("log10 scale", labelpad=20)
        self.radar_ax.legend(fontsize=8)
        self.radar_canvas.draw()

        # log and run
        self.perf_log.append(f"Running simulation for: {selected_op} (Arch: {selected_arch})\n")
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
