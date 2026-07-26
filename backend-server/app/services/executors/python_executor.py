# executors/python_executor.py

from .base import LanguageExecutor


class PythonExecutor(LanguageExecutor):

    extension = ".py"

    def build_command(self):
        return [
            "python",
            "/app/main.py"
        ]