from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class StaticRuleResult:
    rule_id: int | None
    rule_type: str
    expected_value: str | None
    passed: bool
    earned: float
    maximum: float
    required: bool
    feedback: str


def evaluate_rules(
    analysis: Any,
    rules: list[Any],
    handlers: dict,
) -> dict:
    results: list[StaticRuleResult] = []

    total_earned = 0.0
    total_maximum = 0.0

    for rule in rules:
        weight = float(rule.weight or 0.0)
        total_maximum += weight

        handler = handlers.get(rule.rule_type)

        if handler is None:
            results.append(
                StaticRuleResult(
                    rule_id=getattr(rule, "rule_id", None),
                    rule_type=rule.rule_type,
                    expected_value=rule.expected_value,
                    passed=False,
                    earned=0.0,
                    maximum=weight,
                    required=rule.required,
                    feedback=(
                        "This static-analysis rule is not "
                        "supported by the selected analyser."
                    ),
                )
            )
            continue

        try:
            passed, feedback = handler(
                analysis,
                rule.expected_value,
            )
        except (TypeError, ValueError) as exc:
            passed = False
            feedback = f"Invalid rule configuration: {exc}"

        earned = weight if passed else 0.0
        total_earned += earned

        results.append(
            StaticRuleResult(
                rule_id=getattr(rule, "rule_id", None),
                rule_type=rule.rule_type,
                expected_value=rule.expected_value,
                passed=passed,
                earned=earned,
                maximum=weight,
                required=rule.required,
                feedback=feedback,
            )
        )

    if total_maximum > 0:
        percentage = (
            total_earned / total_maximum
        ) * 100
    else:
        percentage = 100.0

    return {
        "score": round(percentage, 2),
        "earned": round(total_earned, 2),
        "maximum": round(total_maximum, 2),
        "results": [
            asdict(result)
            for result in results
        ],
    }