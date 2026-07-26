from .base import LanguageExecutor


class JavaScriptExecutor(LanguageExecutor):

    extension = ".js"

    def build_command(self):
        return [
            "node",
            "/app/main.js"
        ]