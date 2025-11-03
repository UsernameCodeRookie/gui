# -*- coding: utf-8 -*-
"""
Resource Path Helper
Provides utility functions to get correct resource paths in both development and PyInstaller environments.
"""

import os
import sys


def get_resource_path(relative_path=""):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    
    In development: Returns path relative to project root
    In PyInstaller: Returns path relative to temporary _MEIPASS folder
    
    Args:
        relative_path: Path relative to project root (e.g., "config/architecture.json")
    
    Returns:
        Absolute path to the resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # In development, use the project root (parent of src/)
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if relative_path:
        return os.path.join(base_path, relative_path)
    return base_path


def get_project_root():
    """
    Get the project root directory.
    Works in both development and PyInstaller packaged environments.
    """
    return get_resource_path("")


def get_config_path(filename):
    """Get path to a config file."""
    return get_resource_path(os.path.join("config", filename))


def get_data_path(filename=""):
    """Get path to a data file or data directory."""
    if filename:
        return get_resource_path(os.path.join("data", filename))
    return get_resource_path("data")


def get_bin_path(filename):
    """Get path to a binary executable."""
    return get_resource_path(os.path.join("bin", filename))
