from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .common_analysis import CommonAnalysis


@dataclass
class JavaScriptAnalysis(CommonAnalysis):
    pass


ANALYZER_SCRIPT = Path(__file__).with_name(
    "javascript_analyzer.mjs"
)


def analyse_javascript(
    code: str,
) -> JavaScriptAnalysis:
    try:
        completed = subprocess.run(
            [
                "node",
                str(ANALYZER_SCRIPT),
            ],
            input=code,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
            shell=False,
        )

    except FileNotFoundError:
        return JavaScriptAnalysis(
            syntax_valid=False,
            syntax_error=(
                "Node.js is not installed or is not "
                "available on PATH."
            ),
        )

    except subprocess.TimeoutExpired:
        return JavaScriptAnalysis(
            syntax_valid=False,
            syntax_error=(
                "JavaScript static analysis timed out."
            ),
        )

    if completed.returncode != 0:
        return JavaScriptAnalysis(
            syntax_valid=False,
            syntax_error=(
                completed.stderr.strip()
                or "JavaScript analyser failed."
            ),
        )

    try:
        payload = json.loads(completed.stdout)

    except json.JSONDecodeError:
        return JavaScriptAnalysis(
            syntax_valid=False,
            syntax_error=(
                "JavaScript analyser returned invalid JSON."
            ),
        )

    if not payload.get("syntax_valid", False):
        return JavaScriptAnalysis(
            syntax_valid=False,
            syntax_error=payload.get(
                "syntax_error",
                "Invalid JavaScript syntax.",
            ),
        )

    return JavaScriptAnalysis(
        syntax_valid=True,
        syntax_error=None,

        functions=set(
            payload.get("functions", [])
        ),
        classes=set(
            payload.get("classes", [])
        ),
        calls=set(
            payload.get("calls", [])
        ),
        recursive_functions=set(
            payload.get(
                "recursive_functions",
                [],
            )
        ),
        imports=set(
            payload.get("imports", [])
        ),

        loop_count=int(
            payload.get("loop_count", 0)
        ),
        for_loop_count=int(
            payload.get("for_loop_count", 0)
        ),
        while_loop_count=int(
            payload.get("while_loop_count", 0)
        ),
        maximum_loop_depth=int(
            payload.get(
                "maximum_loop_depth",
                0,
            )
        ),

        condition_count=int(
            payload.get("condition_count", 0)
        ),
        return_count=int(
            payload.get("return_count", 0)
        ),
    )