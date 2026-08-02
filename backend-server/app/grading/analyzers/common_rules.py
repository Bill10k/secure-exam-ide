from __future__ import annotations

from collections.abc import Callable

from .common_analysis import CommonAnalysis


RuleHandler = Callable[
    [CommonAnalysis, str | None],
    tuple[bool, str],
]


def parse_boolean(value: str | None) -> bool:
    if value is None:
        return True

    normalized = value.strip().lower()

    if normalized in {"true", "1", "yes"}:
        return True

    if normalized in {"false", "0", "no"}:
        return False

    raise ValueError(
        f"Invalid boolean value: {value}"
    )


def required_function(
    analysis: CommonAnalysis,
    expected: str | None,
) -> tuple[bool, str]:
    function_name = (expected or "").strip()

    if not function_name:
        return False, "No required function name was configured."

    passed = function_name in analysis.functions

    if passed:
        return (
            True,
            f"Required function '{function_name}' was found.",
        )

    return (
        False,
        f"Required function '{function_name}' was not found.",
    )


def require_loop(
    analysis: CommonAnalysis,
    expected: str | None,
) -> tuple[bool, str]:
    required = parse_boolean(expected)
    loop_found = analysis.loop_count > 0
    passed = loop_found == required

    if required and passed:
        return True, "At least one loop was found."

    if required and not passed:
        return False, "A loop is required but none was found."

    if not required and passed:
        return True, "No loop was found, as required."

    return False, "Loops are forbidden for this question."


def require_recursion(
    analysis: CommonAnalysis,
    expected: str | None,
) -> tuple[bool, str]:
    required = parse_boolean(expected)
    recursion_found = bool(
        analysis.recursive_functions
    )
    passed = recursion_found == required

    if required and passed:
        functions = ", ".join(
            sorted(analysis.recursive_functions)
        )
        return (
            True,
            f"Recursion was detected in: {functions}.",
        )

    if required and not passed:
        return (
            False,
            "Recursion is required but was not detected.",
        )

    if not required and passed:
        return True, "No recursion was detected."

    functions = ", ".join(
        sorted(analysis.recursive_functions)
    )

    return (
        False,
        f"Recursion is forbidden but was detected in: {functions}.",
    )


def forbidden_call(
    analysis: CommonAnalysis,
    expected: str | None,
) -> tuple[bool, str]:
    forbidden_name = (expected or "").strip()

    if not forbidden_name:
        return False, "No forbidden call was configured."

    matching_calls = {
        call
        for call in analysis.calls
        if call == forbidden_name
        or call.endswith(f".{forbidden_name}")
    }

    if not matching_calls:
        return (
            True,
            f"Forbidden call '{forbidden_name}' was not used.",
        )

    detected = ", ".join(sorted(matching_calls))

    return (
        False,
        f"Forbidden call detected: {detected}.",
    )


def require_class(
    analysis: CommonAnalysis,
    expected: str | None,
) -> tuple[bool, str]:
    required = parse_boolean(expected)
    class_found = bool(analysis.classes)
    passed = class_found == required

    if required and passed:
        classes = ", ".join(
            sorted(analysis.classes)
        )
        return True, f"Class definition found: {classes}."

    if required and not passed:
        return (
            False,
            "A class definition is required but none was found.",
        )

    if not required and passed:
        return True, "No class definition was found."

    return (
        False,
        "Class definitions are forbidden for this question.",
    )


def maximum_loop_depth(
    analysis: CommonAnalysis,
    expected: str | None,
) -> tuple[bool, str]:
    try:
        maximum_allowed = int(expected or "")
    except ValueError:
        return (
            False,
            "Maximum loop depth must be a valid integer.",
        )

    if maximum_allowed < 0:
        return (
            False,
            "Maximum loop depth cannot be negative.",
        )

    actual_depth = analysis.maximum_loop_depth
    passed = actual_depth <= maximum_allowed

    if passed:
        return (
            True,
            (
                f"Loop depth is {actual_depth}; "
                f"maximum allowed is {maximum_allowed}."
            ),
        )

    return (
        False,
        (
            f"Loop depth is {actual_depth}; "
            f"maximum allowed is {maximum_allowed}."
        ),
    )


COMMON_RULE_HANDLERS: dict[str, RuleHandler] = {
    "required_function": required_function,
    "require_loop": require_loop,
    "require_recursion": require_recursion,
    "forbidden_call": forbidden_call,
    "require_class": require_class,
    "maximum_loop_depth": maximum_loop_depth,
}