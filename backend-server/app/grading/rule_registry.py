from typing import Any


RULE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "required_function": {
        "label": "Required function name",
        "description": "The submitted program must define a function with this name.",
        "input_type": "text",
        "languages": ["python", "javascript", "c", "cpp"],
        "multiple": False,
        "default_weight": 1.0,
    },
    "require_loop": {
        "label": "Loop requirement",
        "description": "Require or forbid the use of iterative loops.",
        "input_type": "boolean",
        "languages": ["python", "javascript", "c", "cpp"],
        "multiple": False,
        "default_weight": 1.0,
    },
    "require_recursion": {
        "label": "Recursion requirement",
        "description": "Require or forbid recursive function calls.",
        "input_type": "boolean",
        "languages": ["python", "javascript", "c", "cpp"],
        "multiple": False,
        "default_weight": 1.0,
    },
    "forbidden_call": {
        "label": "Forbidden function or method",
        "description": "The submitted program must not call the specified function or method.",
        "input_type": "text",
        "languages": ["python", "javascript", "c", "cpp"],
        "multiple": True,
        "default_weight": 1.0,
    },
    "require_class": {
        "label": "Class requirement",
        "description": "Require or forbid the definition of a class.",
        "input_type": "boolean",
        "languages": ["python", "javascript", "cpp"],
        "multiple": False,
        "default_weight": 1.0,
    },
    "maximum_loop_depth": {
        "label": "Maximum nested-loop depth",
        "description": "The program must not exceed the specified loop nesting depth.",
        "input_type": "number",
        "languages": ["python", "javascript", "c", "cpp"],
        "multiple": False,
        "default_weight": 1.0,
    },
}


SUPPORTED_LANGUAGES = {
    "python",
    "javascript",
    "c",
    "cpp",
}


def get_rules_for_language(language: str) -> list[dict[str, Any]]:
    normalized_language = language.strip().lower()

    if normalized_language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")

    return [
        {
            "rule_type": rule_type,
            **definition,
        }
        for rule_type, definition in RULE_DEFINITIONS.items()
        if normalized_language in definition["languages"]
    ]


def get_rule_definition(rule_type: str) -> dict[str, Any] | None:
    return RULE_DEFINITIONS.get(rule_type)


def is_rule_supported_for_language(
    rule_type: str,
    language: str,
) -> bool:
    definition = get_rule_definition(rule_type)

    if definition is None:
        return False

    return language.strip().lower() in definition["languages"]