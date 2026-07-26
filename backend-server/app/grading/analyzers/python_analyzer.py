from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass
class PythonAnalysis:
    syntax_valid: bool = True
    syntax_error: str | None = None

    functions: set[str] = field(default_factory=set)
    async_functions: set[str] = field(default_factory=set)
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


class PythonVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.result = PythonAnalysis()

        # A stack is safer than a single current_function variable
        # because Python allows nested functions.
        self.function_stack: list[str] = []

        self.loop_depth = 0

    @property
    def current_function(self) -> str | None:
        if not self.function_stack:
            return None

        return self.function_stack[-1]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.result.functions.add(node.name)
        self.function_stack.append(node.name)

        self.generic_visit(node)

        self.function_stack.pop()

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ) -> None:
        self.result.functions.add(node.name)
        self.result.async_functions.add(node.name)
        self.function_stack.append(node.name)

        self.generic_visit(node)

        self.function_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.result.classes.add(node.name)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.result.for_loop_count += 1
        self._visit_loop(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.result.for_loop_count += 1
        self._visit_loop(node)

    def visit_While(self, node: ast.While) -> None:
        self.result.while_loop_count += 1
        self._visit_loop(node)

    def _visit_loop(self, node: ast.AST) -> None:
        self.result.loop_count += 1
        self.loop_depth += 1

        self.result.maximum_loop_depth = max(
            self.result.maximum_loop_depth,
            self.loop_depth,
        )

        self.generic_visit(node)

        self.loop_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        self.result.condition_count += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.result.condition_count += 1
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        self.result.return_count += 1
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.result.imports.add(alias.name)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self.result.imports.add(node.module)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = self._call_name(node.func)

        if call_name:
            self.result.calls.add(call_name)

            current_function = self.current_function

            if (
                current_function is not None
                and call_name == current_function
            ):
                self.result.recursive_functions.add(
                    current_function
                )

        self.generic_visit(node)

    @staticmethod
    def _call_name(node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):
            prefix = PythonVisitor._call_name(node.value)

            if prefix:
                return f"{prefix}.{node.attr}"

            return node.attr

        return ""


def analyse_python(code: str) -> PythonAnalysis:
    try:
        syntax_tree = ast.parse(
            code,
            mode="exec",
        )
    except SyntaxError as exc:
        line_number = exc.lineno or 0
        column_number = exc.offset or 0

        return PythonAnalysis(
            syntax_valid=False,
            syntax_error=(
                f"Syntax error on line {line_number}, "
                f"column {column_number}: {exc.msg}"
            ),
        )

    visitor = PythonVisitor()
    visitor.visit(syntax_tree)

    return visitor.result