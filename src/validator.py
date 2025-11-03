# -*- coding: utf-8 -*-
"""
CGRA Validator Module
Provides functions to run CGRA simulation and validation without spawning a separate process.
"""

import os
import sys
import subprocess
import stat
from typing import Callable, Optional

# Get the project root directory (parent of src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXEC_PATH = os.path.join(PROJECT_ROOT, "bin", "CGRA_rebuild")
# Resource directory points to data folder
RESOURCE_DIR = os.path.join(PROJECT_ROOT, "data")


def get_executable_path():
    """Get the platform-specific executable path for CGRA simulator."""
    base_path = EXEC_PATH
    if sys.platform.startswith('win'):
        exe_path = base_path + ".exe"
    else:
        exe_path = base_path
        # Try to add execute permission on Linux/Unix
        if os.path.exists(exe_path):
            st = os.stat(exe_path)
            os.chmod(exe_path, st.st_mode | stat.S_IEXEC)
        else:
            print(f"Warning: Executable {exe_path} not found!")
    return exe_path


def run_simulator(exec_path: str, task: str, mem_file: str, 
                  resource_dir: str = None,
                  stdout_callback: Optional[Callable[[str], None]] = None):
    """
    Run the CGRA simulator with real-time output.
    
    :param exec_path: Path to the simulator executable.
    :param task: Task configuration for the simulation (task directory name).
    :param mem_file: Memory file to be used in the simulation.
    :param resource_dir: Resource directory path (defaults to PROJECT_ROOT/data).
    :param stdout_callback: Optional callback function to receive output lines in real-time.
    :return: Exit code of the simulation.
    """
    if resource_dir is None:
        resource_dir = RESOURCE_DIR
    
    # New command format: cgra_rebuild <task_dir> <memdata_file> <resource_dir>
    command = [exec_path, task, mem_file, resource_dir]
    msg = f"Running command: {' '.join(command)}\n"
    if stdout_callback:
        stdout_callback(msg)
    else:
        print(msg)

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    # Real-time output
    for line in process.stdout:
        if stdout_callback:
            stdout_callback(line.rstrip('\n'))
        else:
            print(line, end='')

    process.stdout.close()
    return_code = process.wait()

    if return_code != 0:
        error_msg = f"Simulation failed with exit code {return_code}."
        if stdout_callback:
            stdout_callback(error_msg)
        raise RuntimeError(error_msg)

    success_msg = "Simulation completed successfully."
    if stdout_callback:
        stdout_callback(success_msg)
    else:
        print(success_msg)
    
    return return_code


def run_golden_model(model_path: str, mem_file: str, golden_file: str,
                     stdout_callback: Optional[Callable[[str], None]] = None):
    """
    Run the golden model with the given parameters.
    
    :param model_path: Path to the golden model executable.
    :param mem_file: Memory file to be used in the golden model.
    :param golden_file: Output file for golden results.
    :param stdout_callback: Optional callback function to receive output in real-time.
    :return: The result of the golden model execution.
    """
    command = ["python", model_path, mem_file, golden_file]
    result = subprocess.run(command, capture_output=True, text=True)
    
    if result.returncode != 0:
        error_msg = f"Golden model execution failed: {result.stderr}"
        if stdout_callback:
            stdout_callback(error_msg)
        raise RuntimeError(error_msg)
    
    msg = f"Golden model executed successfully: {result.stdout}"
    if stdout_callback:
        stdout_callback(msg)
    else:
        print(msg)
    
    return result.stdout


def compare_results(golden_file: str, mem_file: str, tolerance: float = 1e-4,
                   stdout_callback: Optional[Callable[[str], None]] = None):
    """
    Compare the results of the golden model and the simulator using relative error.
    Each line in both files represents a memory address with a float32 number.
    
    :param golden_file: Path to golden results file.
    :param mem_file: Path to simulator output file.
    :param tolerance: Relative error tolerance threshold.
    :param stdout_callback: Optional callback function to receive output in real-time.
    :return: True if all values match within tolerance, False otherwise.
    """
    def output(msg: str):
        if stdout_callback:
            stdout_callback(msg)
        else:
            print(msg)
    
    with open(golden_file, 'r') as f1, open(mem_file, 'r') as f2:
        golden_lines = f1.readlines()
        mem_lines = f2.readlines()

    if len(golden_lines) != len(mem_lines):
        output(f"Line count mismatch: {len(golden_lines)} vs {len(mem_lines)}")
        return False

    total = len(golden_lines)
    mismatches = 0
    max_rel_error = 0.0
    sum_rel_error = 0.0
    all_match = True

    for i, (g_line, m_line) in enumerate(zip(golden_lines, mem_lines)):
        try:
            g_val = float(g_line.strip())
            m_val = float(m_line.strip())
        except ValueError:
            output(f"Line {i}: Invalid float format -> '{g_line.strip()}' or '{m_line.strip()}'")
            mismatches += 1
            all_match = False
            continue

        denom = max(abs(g_val), 1e-8)
        rel_error = abs(g_val - m_val) / denom
        sum_rel_error += rel_error
        max_rel_error = max(max_rel_error, rel_error)

        if rel_error > tolerance:
            output(f"Line {i}: Relative mismatch! "
                  f"Golden={g_val:.7f}, Sim={m_val:.7f}, RelErr={rel_error:.7f}")
            mismatches += 1
            all_match = False

    matched = total - mismatches
    mean_rel_error = sum_rel_error / total if total > 0 else 0.0

    output("\nComparison Summary:")
    output(f"  Mismatched points : {mismatches}")
    output(f"  Max Rel Error     : {max_rel_error:.7f}")
    output(f"  Mean Rel Error    : {mean_rel_error:.7f}")

    if all_match:
        output(f"\nAll values match within relative error tolerance {tolerance}.")
    else:
        output(f"\nSome values differ beyond relative error tolerance {tolerance}.")

    return all_match


def run_validation(task: str, 
                  input_dir: str = None,
                  output_dir: str = None,
                  resource_dir: str = None,
                  stdout_callback: Optional[Callable[[str], None]] = None,
                  stderr_callback: Optional[Callable[[str], None]] = None):
    """
    Run the complete validation workflow: golden model, simulator, and comparison.
    
    :param task: Task name (e.g., "gemm_fp32_slice16")
    :param input_dir: Directory containing input files (defaults to RESOURCE_DIR/input)
    :param output_dir: Directory for output files (defaults to RESOURCE_DIR/output)
    :param resource_dir: Resource directory path (defaults to PROJECT_ROOT/data)
    :param stdout_callback: Optional callback for stdout messages
    :param stderr_callback: Optional callback for stderr messages
    :return: True if validation passes, False otherwise
    """
    def output(msg: str):
        if stdout_callback:
            stdout_callback(msg)
        else:
            print(msg)
    
    try:
        # Set default directories
        if resource_dir is None:
            resource_dir = RESOURCE_DIR
        if input_dir is None:
            input_dir = os.path.join(resource_dir, "input")
        if output_dir is None:
            output_dir = os.path.join(resource_dir, "output")
        
        input_memdata_filename = task + "_memdata.txt"
        golden_memdata_filename = "golden_memdata.txt"
        
        # Save current directory
        original_dir = os.getcwd()
        
        # Get the executable path BEFORE changing directory (to resolve relative paths correctly)
        exe_path = get_executable_path()
        if not os.path.isabs(exe_path):
            # Convert to absolute path if it's relative
            exe_path = os.path.abspath(exe_path)
        
        # Convert input_dir and output_dir to absolute paths
        if not os.path.isabs(input_dir):
            input_dir = os.path.abspath(input_dir)
        if not os.path.isabs(output_dir):
            output_dir = os.path.abspath(output_dir)
        if not os.path.isabs(resource_dir):
            resource_dir = os.path.abspath(resource_dir)
        
        output(f"CGRA executable path: {exe_path}")
        output(f"Resource directory: {resource_dir}")
        output(f"Input directory: {input_dir}")
        output(f"Output directory: {output_dir}")
        
        try:
            # Change to input directory
            os.chdir(input_dir)
            
            output(f"Starting validation for task: {task}")
            output(f"Working directory: {os.getcwd()}")
            
            # Run golden model first
            output("\n=== Running Golden Model ===")
            run_golden_model(
                os.path.join(task, "golden.py"), 
                input_memdata_filename, 
                golden_memdata_filename,
                stdout_callback=stdout_callback
            )
            
            # Run the simulator
            output("\n=== Running CGRA Simulator ===")
            run_simulator(
                exe_path, 
                task, 
                input_memdata_filename,
                resource_dir=resource_dir,
                stdout_callback=stdout_callback
            )
            
            # Compare results
            output("\n=== Comparing Results ===")
            sim_output_path = os.path.join(output_dir, "memorywrite.txt")
            result = compare_results(
                golden_memdata_filename, 
                sim_output_path, 
                tolerance=1e-3,
                stdout_callback=stdout_callback
            )
            
            return result
            
        finally:
            # Always restore original directory
            os.chdir(original_dir)
            
    except Exception as e:
        error_msg = f"Validation error: {str(e)}"
        if stderr_callback:
            stderr_callback(error_msg)
        elif stdout_callback:
            stdout_callback(error_msg)
        else:
            print(error_msg, file=sys.stderr)
        return False


if __name__ == "__main__":
    # Test the module standalone
    task = "gemm_fp32_slice16"
    success = run_validation(task)
    sys.exit(0 if success else 1)
