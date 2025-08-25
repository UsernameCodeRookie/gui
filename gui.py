# -*- coding: utf-8 -*-
"""
PerfSimGUI
- Left panel shows operator XML config
- Right panel has performance tables and charts
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
# Load JSON
# -------------------------------
with open("architecture.json", "r", encoding="utf-8") as f:
    ARCH_DATA = json.load(f)

with open("operators.json", "r", encoding="utf-8") as f:
    OP_DATA = json.load(f)


class PerfSimGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Architecture Performance Comparison")
        self.setGeometry(200, 100, 1400, 800)

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        # -------------------------------
        # Left panel
        # -------------------------------
        operator_group = QGroupBox("Select Operator")
        operator_layout = QVBoxLayout(operator_group)

        self.operator_combo = QComboBox()
        for op_name in OP_DATA.keys():
            self.operator_combo.addItem(op_name)
        operator_layout.addWidget(self.operator_combo)

        self.op_xml_view = QTextEdit()
        self.op_xml_view.setReadOnly(True)
        self.op_xml_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        mono = QFont("Courier New")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.op_xml_view.setFont(mono)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        left_layout = QVBoxLayout()
        left_layout.addWidget(operator_group)
        left_layout.addWidget(QLabel("Operator Config Word (XML)"))
        left_layout.addWidget(self.op_xml_view, stretch=1)
        left_layout.addWidget(QLabel("Simulation Log"))
        left_layout.addWidget(self.log_output, stretch=1)

        self.run_btn = QPushButton("Run Simulation")
        self.clear_btn = QPushButton("Clear")
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.clear_btn)
        left_layout.addLayout(btn_layout)

        # -------------------------------
        # Right panel tabs
        # -------------------------------
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_table_tab(), "Performance Table")
        self.tabs.addTab(self.create_bar_chart_tab(), "Bar Chart")
        self.tabs.addTab(self.create_radar_chart_tab(), "Radar Chart")

        main_layout.addLayout(left_layout, 3)
        main_layout.addWidget(self.tabs, 5)
        self.setCentralWidget(main_widget)

        # -------------------------------
        # Connections
        # -------------------------------
        self.run_btn.clicked.connect(self.run_simulation)
        self.clear_btn.clicked.connect(self.clear_all)
        self.operator_combo.currentTextChanged.connect(self.load_selected_operator_xml)

        self.load_selected_operator_xml()

    # -------------------------------
    # Table tabs
    # -------------------------------
    def create_table_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        splitter = QSplitter(Qt.Orientation.Vertical)

        self.top_table = QTableWidget(3, 6)
        self.top_table.setHorizontalHeaderLabels([
            "Architecture", "Cycles", "Throughput (GOPS)", "Latency (ns)",
            "Power (W)", "Energy Efficiency (GOPS/W)"
        ])
        self.top_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.bottom_table = QTableWidget(len(ARCH_DATA), 8)
        self.bottom_table.setHorizontalHeaderLabels([
            "Architecture", "Process Node (nm)", "Clock Rate (MHz)", "Cores",
            "ALU/core", "FPU/core", "L1_size", "L2_size"
        ])
        self.bottom_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        splitter.addWidget(self.top_table)
        splitter.addWidget(self.bottom_table)
        splitter.setSizes([260, 220])
        layout.addWidget(splitter)
        return widget

    def create_bar_chart_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.bar_fig, self.bar_ax = plt.subplots()
        self.bar_canvas = FigureCanvas(self.bar_fig)
        layout.addWidget(self.bar_canvas)
        return widget

    def create_radar_chart_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.radar_fig = plt.figure()
        self.radar_ax = self.radar_fig.add_subplot(111, polar=True)
        self.radar_canvas = FigureCanvas(self.radar_fig)
        layout.addWidget(self.radar_canvas)
        return widget

    # -------------------------------
    # XML loader
    # -------------------------------
    def load_selected_operator_xml(self):
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
            xml_text = (
                f"<!-- XML not found for operator: {selected_op} -->\n"
                f"<!-- Tried paths:\n{tried}\n-->\n"
            )

        self.op_xml_view.setPlainText(xml_text)

    # -------------------------------
    # Run simulation
    # -------------------------------
    def run_simulation(self):
        self.log_output.clear()

        selected_op = self.operator_combo.currentText()
        perf_data = OP_DATA[selected_op]
        arch_data = ARCH_DATA

        # --- Update top performance table
        self.top_table.setRowCount(len(perf_data))
        for i, arch in enumerate(perf_data.keys()):
            metrics = perf_data[arch]
            self.top_table.setItem(i, 0, QTableWidgetItem(arch))
            self.top_table.setItem(i, 1, QTableWidgetItem(str(metrics.get("cycle", "-"))))
            self.top_table.setItem(i, 2, QTableWidgetItem(str(metrics.get("throughput", "-"))))
            self.top_table.setItem(i, 3, QTableWidgetItem(str(metrics.get("latency", "-"))))
            self.top_table.setItem(i, 4, QTableWidgetItem(str(metrics.get("power", "-"))))
            self.top_table.setItem(i, 5, QTableWidgetItem(str(metrics.get("efficiency", "-"))))

        # --- Update bottom architecture table
        self.bottom_table.setRowCount(len(arch_data))
        for i, arch in enumerate(arch_data.keys()):
            params = arch_data[arch]
            self.bottom_table.setItem(i, 0, QTableWidgetItem(params.get("name", arch)))
            self.bottom_table.setItem(i, 1, QTableWidgetItem(str(params.get("process", "-"))))
            self.bottom_table.setItem(i, 2, QTableWidgetItem(str(params.get("clock_rate", "-"))))
            self.bottom_table.setItem(i, 3, QTableWidgetItem(str(params.get("cores", "-"))))
            self.bottom_table.setItem(i, 4, QTableWidgetItem(str(params.get("ALU_per_core", "-"))))
            self.bottom_table.setItem(i, 5, QTableWidgetItem(str(params.get("FPU_per_core", "-"))))
            self.bottom_table.setItem(i, 6, QTableWidgetItem(str(params.get("L1_size", "-"))))
            self.bottom_table.setItem(i, 7, QTableWidgetItem(str(params.get("L2_size", "-"))))

        # --- Update bar chart (多指标对比，采用对数纵坐标)
        self.bar_ax.clear()
        archs = list(perf_data.keys())
        metrics_keys = ["cycle", "throughput", "latency", "power", "efficiency"]
        metrics_labels = ["Cycles", "Throughput (GOPS)", "Latency (ns)", "Power (W)", "Efficiency (GOPS/W)"]

        num_metrics = len(metrics_keys)
        x = np.arange(len(archs))
        width = 0.15

        for idx, key in enumerate(metrics_keys):
            values = [perf_data[a].get(key, 1) for a in archs]  # 避免取 0
            self.bar_ax.bar(x + (idx - num_metrics/2)*width + width/2, values, width, label=metrics_labels[idx])

        self.bar_ax.set_xticks(x)
        self.bar_ax.set_xticklabels(archs)
        self.bar_ax.set_ylabel("Metric Values (log scale)")
        self.bar_ax.set_yscale("log")
        self.bar_ax.legend(fontsize=8)
        self.bar_canvas.draw()

        # --- Update radar chart (log10 转换)
        self.radar_ax.clear()
        metrics = ["Throughput", "Latency", "Power", "Energy Efficiency"]
        keys = ["throughput", "latency", "power", "efficiency"]

        angles = np.linspace(0, 2*np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]

        for arch in perf_data:
            raw_vals = [perf_data[arch].get(k, 1) for k in keys]
            values = [math.log10(v + 1) for v in raw_vals]  # log10 转换
            values += values[:1]
            self.radar_ax.plot(angles, values, label=arch)
            self.radar_ax.fill(angles, values, alpha=0.25)

        self.radar_ax.set_xticks(angles[:-1])
        self.radar_ax.set_xticklabels(metrics)
        self.radar_ax.set_ylabel("log10 scale", labelpad=20)
        self.radar_ax.legend(fontsize=8)
        self.radar_canvas.draw()

        # --- Log summary
        self.log_output.append(f"Running simulation for: {selected_op}\n")

        self.sim_runner = SimulationRunner(script_dir="../CGRA_rebuild")

        def stdout_callback(line):
            self.log_output.append(line)
            self.log_output.verticalScrollBar().setValue(
                self.log_output.verticalScrollBar().maximum()
            )

        def stderr_callback(line):
            self.log_output.append(f"[ERR] {line}")
            self.log_output.verticalScrollBar().setValue(
                self.log_output.verticalScrollBar().maximum()
            )

        def finished_callback():
            self.log_output.append("\nSimulation finished ✅\n")
            self.log_output.verticalScrollBar().setValue(
                self.log_output.verticalScrollBar().maximum()
            )

        cgra_entry = perf_data.get("CGRA", {})
        config_xml_path = cgra_entry.get("config_xml", "")
        script_name = "validation.py"
        args = [config_xml_path] if config_xml_path else []

        self.sim_runner.run(
            script_name,
            args=args,
            stdout_callback=stdout_callback,
            stderr_callback=stderr_callback,
            finished_callback=finished_callback
        )

    # -------------------------------
    # Clear all
    # -------------------------------
    def clear_all(self):
        self.log_output.clear()
        self.op_xml_view.clear()
        self.top_table.clearContents()
        self.bottom_table.clearContents()
        self.bar_ax.clear()
        self.bar_canvas.draw()
        self.radar_ax.clear()
        self.radar_canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = PerfSimGUI()
    gui.show()
    sys.exit(app.exec())
