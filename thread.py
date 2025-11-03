# -*- coding: utf-8 -*-
"""
CGRA Validation Thread
Provides a QThread wrapper for running CGRA validation without blocking the UI.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from validator import run_validation


class CGRAValidationThread(QThread):
    """
    Thread for running CGRA validation in the background.
    Emits signals for stdout, stderr, and completion.
    """
    stdout_signal = pyqtSignal(str)
    stderr_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)  # True if validation passed, False otherwise
    
    def __init__(self, task: str, input_dir: str = "./resource/input",
                 output_dir: str = "./resource/output"):
        super().__init__()
        self.task = task
        self.input_dir = input_dir
        self.output_dir = output_dir
        self._is_running = True
    
    def run(self):
        """Run the validation in a separate thread."""
        try:
            success = run_validation(
                self.task,
                self.input_dir,
                self.output_dir,
                stdout_callback=self.stdout_signal.emit,
                stderr_callback=self.stderr_signal.emit
            )
            self.finished_signal.emit(success)
        except Exception as e:
            self.stderr_signal.emit(f"Thread error: {str(e)}")
            self.finished_signal.emit(False)
    
    def stop(self):
        """Request the thread to stop (note: actual stopping depends on subprocess)."""
        self._is_running = False
        self.terminate()
