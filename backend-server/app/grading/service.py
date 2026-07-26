from __future__ import annotations

from typing import Any

from .analyzers.python_analyzer import analyse_python
from .analyzers.python_rules import PYTHON_RULE_HANDLERS
from .evaluator import evaluate_rules


def run_static_analysis(
    code: str,
    language: str,
    rules: list[Any],
) -> dict:
    normalized_language = language.strip().lower()

    if normalized_language != "python":
        return {
            "language": normalized_language,
            "syntax_valid": False,
            "score": 0.0,
            "earned": 0.0,
            "maximum": sum(
                float(rule.weight or 0.0)
                for rule in rules
            ),
            "results": [],
            "error": (
                f"Static analysis for '{normalized_language}' "
                "has not been implemented yet."
            ),
            "metrics": {},
        }

    analysis = analyse_python(code)

    if not analysis.syntax_valid:
        return {
            "language": normalized_language,
            "syntax_valid": False,
            "score": 0.0,
            "earned": 0.0,
            "maximum": sum(
                float(rule.weight or 0.0)
                for rule in rules
            ),
            "results": [],
            "error": analysis.syntax_error,
            "metrics": {},
        }

    evaluation = evaluate_rules(
        analysis=analysis,
        rules=rules,
        handlers=PYTHON_RULE_HANDLERS,
    )

    return {
        "language": normalized_language,
        "syntax_valid": True,
        "score": evaluation["score"],
        "earned": evaluation["earned"],
        "maximum": evaluation["maximum"],
        "results": evaluation["results"],
        "error": None,
        "metrics": {
            "functions": sorted(analysis.functions),
            "classes": sorted(analysis.classes),
            "calls": sorted(analysis.calls),
            "imports": sorted(analysis.imports),
            "recursive_functions": sorted(
                analysis.recursive_functions
            ),
            "loop_count": analysis.loop_count,
            "for_loop_count": analysis.for_loop_count,
            "while_loop_count": analysis.while_loop_count,
            "maximum_loop_depth": (
                analysis.maximum_loop_depth
            ),
            "condition_count": analysis.condition_count,
            "return_count": analysis.return_count,
        },
    }