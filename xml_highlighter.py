# -*- coding: utf-8 -*-
"""
XML Syntax Highlighter Module
Provides syntax highlighting for XML files with warm color scheme.
"""

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor


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