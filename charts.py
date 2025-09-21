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
    
    # Prepare data for better visualization - group by metrics instead of architecture
    x_positions = np.arange(len(metrics_keys))
    bar_width = 0.25
    
    # Plot bars for each architecture
    for arch_idx, arch in enumerate(archs):
        values = []
        for key in metrics_keys:
            v = perf_data[arch].get(key, 0)
            val = float(v) if v else 0.0
            # Handle latency differently (lower is better)
            if key == "latency" and val > 0:
                # For latency, use reciprocal for better visualization (higher bar = better performance)
                val = 1000.0 / val  # Convert to frequency-like metric
            elif val <= 0:
                val = 0.001  # Small positive value for log scale
            values.append(val)
        
        # Calculate position offset for this architecture
        offset = (arch_idx - len(archs)/2 + 0.5) * bar_width
        bars = bar_ax.bar(x_positions + offset, values, bar_width, 
                          label=arch, color=WARM_COLORS[arch_idx % len(WARM_COLORS)], 
                          alpha=0.8, edgecolor='white', linewidth=1)
        
        # Add value labels on bars
        for bar_idx, bar in enumerate(bars):
            height = bar.get_height()
            if height > 0:
                # Format the label based on the original value
                orig_key = metrics_keys[bar_idx]
                orig_val = perf_data[arch].get(orig_key, 0)
                if orig_key == "latency":
                    label_text = f"{orig_val:.0f}ns" if orig_val > 0 else "-"
                elif orig_key in ["throughput", "efficiency", "density"]:
                    label_text = f"{orig_val:.1f}" if orig_val > 0 else "-"
                else:  # power
                    label_text = f"{orig_val:.1f}W" if orig_val > 0 else "-"
                
                bar_ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                           label_text, ha='center', va='bottom', fontsize=8, 
                           color='#2c3e50', fontweight='bold', rotation=0)

    # Customize the chart
    bar_ax.set_xticks(x_positions)
    modified_labels = ["吞吐量\n(GOPS)", "延迟性能\n(1000/ns)", "功耗\n(W)", "能效\n(GOPS/W)", "算力密度\n(MOPS/mm²)"]
    bar_ax.set_xticklabels(modified_labels, fontweight='bold', color='#2c3e50', fontsize=9)
    bar_ax.set_ylabel("性能指标", fontweight='bold', color='#2c3e50')
    bar_ax.legend(fontsize=9, frameon=True, fancybox=True, shadow=True, loc='upper left')
    bar_ax.grid(True, alpha=0.3, color='#bdc3c7', axis='y')
    bar_ax.set_title("性能对比 (分组显示)", fontweight='bold', color='#e67e22', fontsize=14)
    bar_canvas.draw()


def update_radar_chart(radar_ax, radar_canvas, perf_data):
    """Update the radar chart with normalized performance data."""
    radar_ax.clear()
    metrics = ["吞吐量 (GOPS)", "延迟 (ns)", "功耗 (W)", "能效 (GOPS/W)", "有效算力密度 (MOPS/mm²)"]
    keys = ["throughput", "latency", "power", "efficiency", "density"]
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]
    
    # Collect all raw values for normalization
    all_values = {k: [] for k in keys}
    for arch in perf_data:
        for k in keys:
            v = perf_data[arch].get(k, 1)
            vv = float(v) if v else 1.0
            if vv <= 0: vv = 1e-3
            all_values[k].append(vv)
    
    # Calculate normalization factors (min-max scaling to 0-1)
    norm_factors = {}
    for k in keys:
        vals = all_values[k]
        if len(vals) > 1:
            min_val, max_val = min(vals), max(vals)
            if max_val > min_val:
                norm_factors[k] = (min_val, max_val)
            else:
                norm_factors[k] = (min_val, min_val + 1)  # Avoid division by zero
        else:
            norm_factors[k] = (vals[0] if vals else 1, (vals[0] if vals else 1) + 1)
    
    for idx, arch in enumerate(perf_data):
        raw_vals = []
        for k in keys:
            v = perf_data[arch].get(k, 1)
            vv = float(v) if v else 1.0
            if vv <= 0: vv = 1e-3
            # Normalize to 0-1 range
            min_val, max_val = norm_factors[k]
            if k == "latency":  # For latency, lower is better, so invert
                normalized = 1 - (vv - min_val) / (max_val - min_val)
            else:  # For other metrics, higher is better
                normalized = (vv - min_val) / (max_val - min_val)
            raw_vals.append(normalized)
        
        values = raw_vals + raw_vals[:1]  # Close the radar chart
        color = WARM_RADAR_COLORS[idx % len(WARM_RADAR_COLORS)]
        radar_ax.plot(angles, values, label=arch, color=color, linewidth=3, alpha=0.9, marker='o', markersize=6)
        # Remove fill to make it clearer

    radar_ax.set_xticks(angles[:-1])
    radar_ax.set_xticklabels(metrics, color='#2c3e50', fontweight='bold')
    radar_ax.set_ylim(0, 1)  # Set fixed scale for normalized values
    radar_ax.set_ylabel("归一化数值 (0-1)", labelpad=20, color='#2c3e50', fontweight='bold')
    radar_ax.legend(fontsize=8, loc='upper right', bbox_to_anchor=(1.2, 1.0), 
                    frameon=True, fancybox=True, shadow=True)
    radar_ax.grid(True, alpha=0.3, color='#bdc3c7')
    radar_ax.set_title("性能雷达图 (归一化)", fontweight='bold', color='#e67e22', 
                       fontsize=14, pad=20)
    radar_canvas.draw()


def setup_chart_style(fig, ax):
    """Apply consistent styling to chart figure and axes."""
    fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.set_facecolor(CHART_BACKGROUND_COLOR)