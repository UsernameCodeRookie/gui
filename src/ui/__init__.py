# -*- coding: utf-8 -*-
"""
UI Components Module
Contains all UI-related components including styles, charts, and syntax highlighters.
"""

from .styles import APP_STYLESHEET, CHART_BACKGROUND_COLOR
from .charts import update_bar_chart, update_radar_chart, setup_chart_style
from .xml_highlighter import XmlSyntaxHighlighter

__all__ = [
    'APP_STYLESHEET',
    'CHART_BACKGROUND_COLOR',
    'update_bar_chart',
    'update_radar_chart',
    'setup_chart_style',
    'XmlSyntaxHighlighter'
]
