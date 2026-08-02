from __future__ import annotations

from typing import Any

from .analyzers.common_analysis import CommonAnalysis
from .analyzers.common_rules import COMMON_RULE_HANDLERS
from .analyzers.javascript_analyzer import (
    analyse_javascript,
)
from .analyzers.clang_analyzer import analyse_clang
from .analyzers.python_analyzer import analyse_python
from .evaluator import evaluate_rules


def _maximum_rule_score(
    rules: list[Any],
) -> float:
    return sum(
        float(rule.weight or 0.0)
        for rule in rules
    )


def _analysis_metrics(
    analysis: CommonAnalysis,
) -> dict:
    return {
        "functions": sorted(analysis.functions),
        "classes": sorted(analysis.classes),
        "calls": sorted(analysis.calls),
        "imports": sorted(analysis.imports),
        "recursive_functions": sorted(
            analysis.recursive_functions
        ),

        "loop_count": analysis.loop_count,
        "for_loop_count": (
            analysis.for_loop_count
        ),
        "while_loop_count": (
            analysis.while_loop_count
        ),
        "maximum_loop_depth": (
            analysis.maximum_loop_depth
        ),

        "condition_count": (
            analysis.condition_count
        ),
        "return_count": analysis.return_count,
    }


def _unsupported_result(
    language: str,
    rules: list[Any],
) -> dict:
    return {
        "language": language,
        "syntax_valid": False,
        "score": 0.0,
        "earned": 0.0,
        "maximum": _maximum_rule_score(rules),
        "results": [],
        "error": (
            f"Static analysis for '{language}' "
            "has not been implemented yet."
        ),
        "metrics": {},
    }


def _syntax_error_result(
    language: str,
    rules: list[Any],
    error: str | None,
) -> dict:
    return {
        "language": language,
        "syntax_valid": False,
        "score": 0.0,
        "earned": 0.0,
        "maximum": _maximum_rule_score(rules),
        "results": [],
        "error": error or "Invalid source code.",
        "metrics": {},
    }


def run_static_analysis(
    code: str,
    language: str,
    rules: list[Any],
) -> dict:
    normalized_language = (
        language.strip().lower()
    )

    if normalized_language == "python":
        analysis = analyse_python(code)

    elif normalized_language == "javascript":
        analysis = analyse_javascript(code)

    elif normalized_language in {"c", "cpp"}:
        analysis = analyse_clang(
            code=code,
            language=normalized_language,
        )

    else:
        return _unsupported_result(
            normalized_language,
            rules,
        )

    if not analysis.syntax_valid:
        return _syntax_error_result(
            normalized_language,
            rules,
            analysis.syntax_error,
        )

    evaluation = evaluate_rules(
        analysis=analysis,
        rules=rules,
        handlers=COMMON_RULE_HANDLERS,
    )

    return {
        "language": normalized_language,
        "syntax_valid": True,

        "score": evaluation["score"],
        "earned": evaluation["earned"],
        "maximum": evaluation["maximum"],
        "results": evaluation["results"],

        "error": None,
        "metrics": _analysis_metrics(analysis),
    }