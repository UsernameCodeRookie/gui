# -*- coding: utf-8 -*-
"""
Utility Functions Module
Contains helper functions for data formatting and text processing.
"""

import re


def slugify(op_name: str) -> str:
    """Convert operator name to a slug format for file naming."""
    s = op_name.lower()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = s.strip('_')
    return s


def format_bytes(bytes_val):
    """Format bytes values to human readable format (KB, MB, etc.)"""
    if not isinstance(bytes_val, (int, float)) or bytes_val == 0:
        return "-"
    
    if bytes_val >= 1024*1024:
        return f"{bytes_val/(1024*1024):.1f} MB"
    elif bytes_val >= 1024:
        return f"{bytes_val/1024:.0f} KB"
    else:
        return f"{bytes_val} B"


def format_number_with_commas(value):
    """Format number with comma separators."""
    if isinstance(value, (int, float)) and value != 0:
        return f"{value:,}"
    return "-"


def format_float_precision(value, precision=2):
    """Format float with specified precision."""
    if isinstance(value, (int, float)) and value != 0:
        return f"{value:.{precision}f}"
    return "-"


def safe_float_conversion(value, default=0.0):
    """Safely convert value to float with fallback."""
    try:
        return float(value) if value else default
    except (ValueError, TypeError):
        return default


def cache_key(operator: str, arch: str) -> str:
    """Generate a unique cache key combining operator and architecture."""
    return f"{operator}::{arch}"