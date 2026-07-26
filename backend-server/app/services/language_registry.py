# language_registry.py

from .executors.python_executor import PythonExecutor
from .executors.js_executor import JavaScriptExecutor
from .executors.c_executor import CExecutor
from .executors.cpp_executor import CPPExecutor

LANGUAGE_REGISTRY = {
    "python": PythonExecutor(),
    "javascript": JavaScriptExecutor(),
    "c": CExecutor(),
    "cpp": CPPExecutor(),
}