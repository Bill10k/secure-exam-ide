from .base import LanguageExecutor


class CExecutor(LanguageExecutor):

    extension = ".c"

    def build_command(self):
        return [
            "sh",
            "-c",
            "gcc /app/main.c -o /tmp/program && /tmp/program"
        ]