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
    metrics_labels = ["吞吐量 (GOPS)", "延迟 (ns)", "功耗 (W)", "能效 (GOPS/W)", "有效算力密度 (MOPS/mm$^2$)"]
    num_archs = len(archs)
    x = np.arange(len(metrics_keys))  # Now x-axis represents metrics
    width = 0.8 / num_archs  # Adjust width based on number of architectures

    for idx, arch in enumerate(archs):
        values = []
        for key in metrics_keys:
            v = perf_data[arch].get(key, 1)
            val = float(v) if v else 1.0
            if val <= 0: val = 1e-3
            values.append(val)
        # Position bars for each architecture within each metric group
        bar_ax.bar(x + (idx - num_archs/2) * width + width/2, values, width, 
                   label=arch, color=WARM_COLORS[idx % len(WARM_COLORS)], 
                   alpha=0.8, edgecolor='white', linewidth=1)

    bar_ax.set_xticks(x)
    bar_ax.set_xticklabels(metrics_labels, fontweight='bold', color='#2c3e50', rotation=15, ha='right')
    bar_ax.set_ylabel("指标数值 (对数刻度)", fontweight='bold', color='#2c3e50')
    bar_ax.set_yscale("log")
    bar_ax.legend(fontsize=8, frameon=True, fancybox=True, shadow=True, title='架构')
    bar_ax.grid(True, alpha=0.3, color='#bdc3c7')
    bar_ax.set_title("性能对比 - 按指标分组", fontweight='bold', color='#e67e22', fontsize=14)
    bar_canvas.draw()


def update_radar_chart(radar_ax, radar_canvas, perf_data):
    """Update the radar chart with performance data."""
    radar_ax.clear()
    metrics = ["吞吐量 (GOPS)", "延迟 (ns)", "功耗 (W)", "能效 (GOPS/W)", "有效算力密度 (MOPS/mm$^2$)"]
    keys = ["throughput", "latency", "power", "efficiency", "density"]
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]
    
    # Collect all raw values for normalization
    all_raw_values = {key: [] for key in keys}
    for arch in perf_data:
        for k in keys:
            v = perf_data[arch].get(k, 1)
            vv = float(v) if v else 1.0
            if vv <= 0: vv = 1e-3
            all_raw_values[k].append(vv)
    
    # Calculate normalization parameters for each metric
    norm_params = {}
    for k in keys:
        values = all_raw_values[k]
        min_val = min(values)
        max_val = max(values)
        
        # Add some padding to avoid clustering
        range_val = max_val - min_val
        if range_val == 0:  # Handle case where all values are the same
            norm_params[k] = {'min': min_val - 0.1, 'max': max_val + 0.1, 'range': 0.2}
        else:
            # Add 20% padding on both sides for better visualization
            padding = range_val * 0.2
            norm_params[k] = {
                'min': min_val - padding,
                'max': max_val + padding,
                'range': range_val + 2 * padding
            }
    
    # Special handling for latency (lower is better, so we need to invert)
    latency_values = all_raw_values['latency']
    if latency_values:
        max_latency = max(latency_values)
        # For latency, we'll use (max_latency + padding - current_value) for normalization
        
    for idx, arch in enumerate(perf_data):
        normalized_vals = []
        for i, k in enumerate(keys):
            v = perf_data[arch].get(k, 1)
            vv = float(v) if v else 1.0
            if vv <= 0: vv = 1e-3
            
            # Normalize to 0-1 range with improved scaling
            if k == 'latency':
                # For latency, lower is better - invert the scale
                max_latency_with_padding = norm_params[k]['max']
                normalized_val = (max_latency_with_padding - vv) / norm_params[k]['range']
            else:
                # For other metrics, higher is better
                normalized_val = (vv - norm_params[k]['min']) / norm_params[k]['range']
            
            # Scale to 0.1-1.0 range to avoid center clustering and ensure visibility
            scaled_val = 0.1 + normalized_val * 0.9
            normalized_vals.append(scaled_val)
        
        normalized_vals += normalized_vals[:1]  # Close the polygon
        
        color = WARM_RADAR_COLORS[idx % len(WARM_RADAR_COLORS)]
        radar_ax.plot(angles, normalized_vals, label=arch, color=color, linewidth=2.5, alpha=0.8)
        radar_ax.fill(angles, normalized_vals, alpha=0.15, color=color)

    # Set consistent radial limits
    radar_ax.set_ylim(0, 1)
    radar_ax.set_xticks(angles[:-1])
    radar_ax.set_xticklabels(metrics, color='#2c3e50', fontweight='bold', fontsize=9)
    
    # Add radial grid lines
    radar_ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    radar_ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], fontsize=8, alpha=0.7)
    radar_ax.grid(True, alpha=0.3, color='#bdc3c7')
    
    # Improve legend positioning
    radar_ax.legend(fontsize=9, loc='upper right', bbox_to_anchor=(1.15, 1.0), 
                    frameon=True, fancybox=True, shadow=True, title='架构')
    radar_ax.set_title("性能雷达图 (标准化)", fontweight='bold', color='#e67e22', 
                       fontsize=14, pad=20)
    radar_canvas.draw()


def setup_chart_style(fig, ax):
    """Apply consistent styling to chart figure and axes."""
    fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.set_facecolor(CHART_BACKGROUND_COLOR)