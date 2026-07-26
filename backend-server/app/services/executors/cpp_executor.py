from .base import LanguageExecutor


class CPPExecutor(LanguageExecutor):

    extension = ".cpp"

    def build_command(self):
        return [
            "sh",
            "-c",
            "g++ -std=c++20 /app/main.cpp -o /tmp/program && /tmp/program"
        ]