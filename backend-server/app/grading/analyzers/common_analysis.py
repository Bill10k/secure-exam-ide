from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CommonAnalysis:
    syntax_valid: bool = True
    syntax_error: str | None = None

    functions: set[str] = field(default_factory=set)
    classes: set[str] = field(default_factory=set)

    calls: set[str] = field(default_factory=set)
    recursive_functions: set[str] = field(default_factory=set)

    imports: set[str] = field(default_factory=set)

    loop_count: int = 0
    for_loop_count: int = 0
    while_loop_count: int = 0
    maximum_loop_depth: int = 0

    condition_count: int = 0
    return_count: int = 0