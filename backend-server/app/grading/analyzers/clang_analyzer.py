from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
import shutil

from .clang_visitor import ast_to_analysis
from .common_analysis import CommonAnalysis


@dataclass
class ClangAnalysis(CommonAnalysis):
    pass


SUPPORTED_CLANG_LANGUAGES = {
    "c",
    "cpp",
}

def find_compiler(language: str) -> str | None:
    executable = "clang.exe" if language == "c" else "clang++.exe"

    # First try PATH.
    compiler_path = shutil.which(executable)

    if compiler_path:
        return compiler_path

    # Standard LLVM installation location on Windows.
    default_path = Path(
        "C:/Program Files/LLVM/bin"
    ) / executable

    if default_path.exists():
        return str(default_path)

    return None

def analyse_clang(
    code: str,
    language: str,
) -> ClangAnalysis:
    normalized_language = language.strip().lower()

    if normalized_language not in SUPPORTED_CLANG_LANGUAGES:
        return ClangAnalysis(
            syntax_valid=False,
            syntax_error=(
                f"Unsupported Clang language: "
                f"{normalized_language}"
            ),
        )

    suffix = (
        ".c"
        if normalized_language == "c"
        else ".cpp"
    )

    compiler = find_compiler(normalized_language)

    if compiler is None:
        return ClangAnalysis(
            syntax_valid=False,
            syntax_error=(
                "LLVM/Clang could not be located. "
                "Expected clang.exe or clang++.exe on PATH "
                "or under C:/Program Files/LLVM/bin."
            ),
        )
    source_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=suffix,
            delete=False,
            encoding="utf-8",
        ) as source_file:
            source_file.write(code)
            source_path = source_file.name

        command = [
            compiler,
            "-Xclang",
            "-ast-dump=json",
            "-fsyntax-only",
            source_path,
        ]

        # Select a predictable language standard.
        if normalized_language == "c":
            command.insert(-1, "-std=c17")
        else:
            command.insert(-1, "-std=c++17")

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                shell=False,
            )

        except FileNotFoundError:
            return ClangAnalysis(
                syntax_valid=False,
                syntax_error=(
                    f"{compiler} is not installed or is "
                    "not available on PATH."
                ),
            )

        except subprocess.TimeoutExpired:
            return ClangAnalysis(
                syntax_valid=False,
                syntax_error=(
                    f"{normalized_language.upper()} static "
                    "analysis timed out."
                ),
            )

        if completed.returncode != 0:
            return ClangAnalysis(
                syntax_valid=False,
                syntax_error=(
                    completed.stderr.strip()
                    or "Clang could not parse the source code."
                ),
            )

        try:
            ast = json.loads(completed.stdout)

        except json.JSONDecodeError:
            return ClangAnalysis(
                syntax_valid=False,
                syntax_error=(
                    "Clang returned invalid AST JSON."
                ),
            )

        common_result = ast_to_analysis(
            ast=ast,
            source_path=source_path,
        )

        return ClangAnalysis(
            syntax_valid=True,
            syntax_error=None,
            functions=common_result.functions,
            classes=common_result.classes,
            calls=common_result.calls,
            recursive_functions=(
                common_result.recursive_functions
            ),
            imports=common_result.imports,
            loop_count=common_result.loop_count,
            for_loop_count=(
                common_result.for_loop_count
            ),
            while_loop_count=(
                common_result.while_loop_count
            ),
            maximum_loop_depth=(
                common_result.maximum_loop_depth
            ),
            condition_count=(
                common_result.condition_count
            ),
            return_count=common_result.return_count,
        )

    finally:
        if source_path and os.path.exists(source_path):
            os.remove(source_path)