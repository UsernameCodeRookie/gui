# -*- coding: utf-8 -*-
"""
Golden Models Manager
Centralized management for all golden model implementations to support offline execution.
"""

import os
import sys
import importlib.util
from typing import Optional, Callable


class GoldenModelManager:
    """Manager for executing golden models in packaged environments."""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.input_dir = os.path.join(data_dir, "input")
    
    def run_golden_model(self, task: str, mem_file: str, golden_file: str,
                        stdout_callback: Optional[Callable[[str], None]] = None):
        """
        Execute a golden model for the specified task.
        
        :param task: Task name (e.g., "gemm_fp32_slice16")
        :param mem_file: Memory data file path
        :param golden_file: Golden output file path
        :param stdout_callback: Optional callback for output messages
        """
        def output(msg: str):
            if stdout_callback:
                stdout_callback(msg)
            else:
                print(msg)
        
        # Construct path to golden model
        golden_path = os.path.join(self.input_dir, task, "golden.py")
        
        if not os.path.exists(golden_path):
            raise FileNotFoundError(f"Golden model not found: {golden_path}")
        
        try:
            # Load and execute the golden model module
            spec = importlib.util.spec_from_file_location("golden_model", golden_path)
            golden_module = importlib.util.module_from_spec(spec)
            
            # Save current working directory and sys.path
            original_cwd = os.getcwd()
            original_path = sys.path.copy()
            original_argv = sys.argv.copy()
            
            try:
                # Set working directory to the golden model's directory
                model_dir = os.path.dirname(golden_path)
                os.chdir(model_dir)
                
                # Add model directory to Python path
                if model_dir not in sys.path:
                    sys.path.insert(0, model_dir)
                
                # Convert file paths to be relative to the model directory
                # mem_file and golden_file are relative to input_dir, but we're now in model_dir
                # So we need to go up one level to access files in input_dir
                mem_file_relative = os.path.join("..", mem_file) if not os.path.isabs(mem_file) else mem_file
                golden_file_relative = os.path.join("..", golden_file) if not os.path.isabs(golden_file) else golden_file
                
                # Set command line arguments
                sys.argv = ["golden.py", mem_file_relative, golden_file_relative]
                
                # Execute the module
                spec.loader.exec_module(golden_module)
                
                # Since __name__ is not "__main__" when using importlib, we need to manually
                # trigger the main execution logic. Check if the module has the expected functions.
                if hasattr(golden_module, 'gemm') and len(sys.argv) == 3:
                    # Call the main function directly since __name__ != "__main__"
                    golden_module.gemm(sys.argv[1], sys.argv[2])
                elif hasattr(golden_module, 'conv') and len(sys.argv) == 3:
                    # For conv models
                    golden_module.conv(sys.argv[1], sys.argv[2])
                elif hasattr(golden_module, 'fft') and len(sys.argv) == 3:
                    # For fft models
                    golden_module.fft(sys.argv[1], sys.argv[2])
                else:
                    # Try to find and call the main function dynamically
                    # Look for functions that take exactly 2 parameters (mem_file, golden_file)
                    import inspect
                    for name, obj in inspect.getmembers(golden_module):
                        if (inspect.isfunction(obj) and 
                            len(inspect.signature(obj).parameters) == 2 and
                            not name.startswith('_')):
                            obj(sys.argv[1], sys.argv[2])
                            break
                    else:
                        # If no suitable function found, raise an error
                        raise RuntimeError(f"No suitable main function found in golden model for task '{task}'")
                
                # If the module has a main function, call it directly
                # Otherwise, check if it defines functions we can call
                if hasattr(golden_module, '__main__') and callable(getattr(golden_module, '__main__')):
                    golden_module.__main__()
                elif hasattr(golden_module, 'main') and callable(getattr(golden_module, 'main')):
                    golden_module.main()
                else:
                    # Try to call a function with appropriate name
                    # Look for functions that match the task pattern
                    task_name_lower = task.split('_')[0].lower() if task else 'unknown'
                    possible_names = [task_name_lower, 'run', 'execute']
                    
                    function_called = False
                    for func_name in possible_names:
                        if hasattr(golden_module, func_name) and callable(getattr(golden_module, func_name)):
                            func = getattr(golden_module, func_name)
                            func(mem_file_relative, golden_file_relative)
                            function_called = True
                            break
                    
                    if not function_called:
                        # If no appropriate function found, re-execute with __name__ = "__main__"
                        # This is a fallback that should work for most cases
                        exec(spec.loader.get_data(golden_path).decode('utf-8'), 
                             {'__name__': '__main__', '__file__': golden_path})
                
                output(f"Golden model '{task}' executed successfully")
                
            finally:
                # Restore original state
                os.chdir(original_cwd)
                sys.path = original_path
                sys.argv = original_argv
                
        except Exception as e:
            error_msg = f"Failed to execute golden model '{task}': {str(e)}"
            output(error_msg)
            raise RuntimeError(error_msg)
    
    def list_available_models(self):
        """List all available golden models."""
        models = []
        if os.path.exists(self.input_dir):
            for task_dir in os.listdir(self.input_dir):
                task_path = os.path.join(self.input_dir, task_dir)
                if os.path.isdir(task_path):
                    golden_path = os.path.join(task_path, "golden.py")
                    if os.path.exists(golden_path):
                        models.append(task_dir)
        return models
    
    def validate_model(self, task: str):
        """Check if a golden model exists for the given task."""
        golden_path = os.path.join(self.input_dir, task, "golden.py")
        return os.path.exists(golden_path)


# Global instance (will be initialized by validator module)
_golden_manager = None


def get_golden_manager(data_dir: str = None):
    """Get or create the global golden model manager."""
    global _golden_manager
    if _golden_manager is None and data_dir:
        _golden_manager = GoldenModelManager(data_dir)
    return _golden_manager


def init_golden_manager(data_dir: str):
    """Initialize the global golden model manager."""
    global _golden_manager
    _golden_manager = GoldenModelManager(data_dir)
    return _golden_manager