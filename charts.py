# -*- coding: utf-8 -*-
"""
Charts Module
Contains functions for creating and updating bar charts and radar charts.
"""

import math
import numpy as np
import matplotlib.pyplot as plt
from styles import WARM_COLORS, WARM_RADAR_COLORS, CHART_BACKGROUND_COLOR


def update_bar_chart(bar_ax, bar_canvas, perf_data):
    """Update the bar chart with performance data."""
    bar_ax.clear()
    archs = list(perf_data.keys())
    metrics_keys = ["throughput", "latency", "power", "efficiency", "density"]
    metrics_labels = ["吞吐量 (GOPS)", "延迟 (ns)", "功耗 (W)", "能效 (GOPS/W)", "有效算力密度 (MOPS/mm²)"]
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
        bar_ax.bar(x + (idx - num_metrics/2) * width + width/2, values, width, 
                   label=metrics_labels[idx], color=WARM_COLORS[idx % len(WARM_COLORS)], 
                   alpha=0.8, edgecolor='white', linewidth=1)

    bar_ax.set_xticks(x)
    bar_ax.set_xticklabels(archs, fontweight='bold', color='#2c3e50')
    bar_ax.set_ylabel("指标数值 (对数刻度)", fontweight='bold', color='#2c3e50')
    bar_ax.set_yscale("log")
    bar_ax.legend(fontsize=8, frameon=True, fancybox=True, shadow=True)
    bar_ax.grid(True, alpha=0.3, color='#bdc3c7')
    bar_ax.set_title("性能对比", fontweight='bold', color='#e67e22', fontsize=14)
    bar_canvas.draw()


def update_radar_chart(radar_ax, radar_canvas, perf_data):
    """Update the radar chart with performance data."""
    radar_ax.clear()
    metrics = ["吞吐量 (GOPS)", "延迟 (ns)", "功耗 (W)", "能效 (GOPS/W)", "有效算力密度 (MOPS/mm²)"]
    keys = ["throughput", "latency", "power", "efficiency", "density"]
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]
    
    for idx, arch in enumerate(perf_data):
        raw_vals = []
        for k in keys:
            v = perf_data[arch].get(k, 1)
            vv = float(v) if v else 1.0
            if vv <= 0: vv = 1e-3
            raw_vals.append(vv)
        values = [math.log10(v + 1) for v in raw_vals]
        values += values[:1]
        color = WARM_RADAR_COLORS[idx % len(WARM_RADAR_COLORS)]
        radar_ax.plot(angles, values, label=arch, color=color, linewidth=2, alpha=0.8)
        radar_ax.fill(angles, values, alpha=0.2, color=color)

    radar_ax.set_xticks(angles[:-1])
    radar_ax.set_xticklabels(metrics, color='#2c3e50', fontweight='bold')
    radar_ax.set_ylabel("对数刻度", labelpad=20, color='#2c3e50', fontweight='bold')
    radar_ax.legend(fontsize=8, loc='upper right', bbox_to_anchor=(1.2, 1.0), 
                    frameon=True, fancybox=True, shadow=True)
    radar_ax.grid(True, alpha=0.3, color='#bdc3c7')
    radar_ax.set_title("性能雷达图", fontweight='bold', color='#e67e22', 
                       fontsize=14, pad=20)
    radar_canvas.draw()


def setup_chart_style(fig, ax):
    """Apply consistent styling to chart figure and axes."""
    fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.set_facecolor(CHART_BACKGROUND_COLOR)