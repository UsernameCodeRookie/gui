# -*- coding: utf-8 -*-
"""
sim_runner.py
Encapsulates an external script runner
- Supports real-time stdout/stderr output via callbacks
- Supports finished callback
"""

import os
from PyQt6.QtCore import QProcess

class SimulationRunner:
    def __init__(self, script_dir="./sim_scripts"):
        """
        :param script_dir: Directory where external Python scripts are located
        """
        self.script_dir = script_dir
        self.process = None
        self.stdout_callback = None
        self.stderr_callback = None
        self.finished_callback = None

    def run(self, script_name, args=None,
            stdout_callback=None, stderr_callback=None, finished_callback=None):
        """
        Start running the script
        :param script_name: Name of the script, e.g., run_sim.py
        :param args: list of arguments to pass to the script, e.g., ["Conv2d W=224 H=224"]
        :param stdout_callback: callback(str), called on each stdout output
        :param stderr_callback: callback(str), called on each stderr output
        :param finished_callback: callback(), called when the script finishes
        """
        if args is None:
            args = []

        self.stdout_callback = stdout_callback
        self.stderr_callback = stderr_callback
        self.finished_callback = finished_callback

        self.process = QProcess()
        self.process.setWorkingDirectory(self.script_dir)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.handle_finished)

        # Start the process
        self.process.start("python3", [script_name] + args)

    def handle_stdout(self):
        if self.process:
            data = self.process.readAllStandardOutput().data().decode()
            if self.stdout_callback and data.strip():
                self.stdout_callback(data.strip())

    def handle_stderr(self):
        if self.process:
            data = self.process.readAllStandardError().data().decode()
            if self.stderr_callback and data.strip():
                self.stderr_callback(data.strip())

    def handle_finished(self):
        if self.finished_callback:
            self.finished_callback()
        self.process = None

    def terminate(self):
        """Terminate the currently running script"""
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.terminate()
            self.process = None
