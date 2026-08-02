from __future__ import annotations

from pathlib import Path
from typing import Any

from .common_analysis import CommonAnalysis


FUNCTION_KINDS = {
    "FunctionDecl",
    "CXXMethodDecl",
}

CALL_KINDS = {
    "CallExpr",
    "CXXMemberCallExpr",
    "CXXOperatorCallExpr",
}

FOR_LOOP_KINDS = {
    "ForStmt",
    "CXXForRangeStmt",
}

WHILE_LOOP_KINDS = {
    "WhileStmt",
    "DoStmt",
}

CONDITION_KINDS = {
    "IfStmt",
    "ConditionalOperator",
}


class ClangVisitor:
    def __init__(
        self,
        source_path: str | Path,
    ) -> None:
        self.source_path = Path(source_path).resolve()

        self.result = CommonAnalysis()

        self.function_stack: list[str] = []
        self.loop_depth = 0

    @property
    def current_function(self) -> str | None:
        if not self.function_stack:
            return None

        return self.function_stack[-1]

    def visit(
        self,
        node: dict[str, Any],
        inherited_file: str | None = None,
    ) -> None:
        if not isinstance(node, dict):
            return

        kind = node.get("kind", "")
        node_file = self._node_file(node) or inherited_file

        entered_function = False
        entered_loop = False

        if (
            kind in FUNCTION_KINDS
            and self._is_function_definition(node)
            and self._is_user_node(node_file)
        ):
            function_name = str(node.get("name") or "").strip()

            if function_name:
                self.result.functions.add(function_name)
                self.function_stack.append(function_name)
                entered_function = True

        if (
            kind == "CXXRecordDecl"
            and node.get("completeDefinition") is True
            and not node.get("isImplicit", False)
            and self._is_user_node(node_file)
        ):
            class_name = str(node.get("name") or "").strip()

            if class_name:
                self.result.classes.add(class_name)

        if kind in FOR_LOOP_KINDS:
            self.result.for_loop_count += 1
            self._enter_loop()
            entered_loop = True

        elif kind in WHILE_LOOP_KINDS:
            self.result.while_loop_count += 1
            self._enter_loop()
            entered_loop = True

        if kind in CONDITION_KINDS:
            self.result.condition_count += 1

        if kind == "ReturnStmt":
            self.result.return_count += 1

        if kind in CALL_KINDS:
            call_name = self._extract_call_name(node)

            if call_name:
                self.result.calls.add(call_name)

                current_function = self.current_function

                if (
                    current_function
                    and self._is_recursive_call(
                        call_name,
                        current_function,
                    )
                ):
                    self.result.recursive_functions.add(
                        current_function
                    )

        for child in node.get("inner", []):
            if isinstance(child, dict):
                self.visit(
                    child,
                    inherited_file=node_file,
                )

        if entered_loop:
            self.loop_depth -= 1

        if entered_function:
            self.function_stack.pop()

    def _enter_loop(self) -> None:
        self.result.loop_count += 1
        self.loop_depth += 1

        self.result.maximum_loop_depth = max(
            self.result.maximum_loop_depth,
            self.loop_depth,
        )

    def _is_user_node(
        self,
        node_file: str | None,
    ) -> bool:
        """
        Avoid counting declarations originating from included
        system or library headers.
        """
        if node_file is None:
            # Some child nodes inherit their source location from
            # their enclosing declaration.
            return True

        try:
            return Path(node_file).resolve() == self.source_path
        except (OSError, RuntimeError):
            return False

    @staticmethod
    def _is_function_definition(
        node: dict[str, Any],
    ) -> bool:
        """
        A declaration is treated as a function definition only when
        it contains a body.
        """
        body_kinds = {
            "CompoundStmt",
            "CXXTryStmt",
        }

        return any(
            isinstance(child, dict)
            and child.get("kind") in body_kinds
            for child in node.get("inner", [])
        )

    @staticmethod
    def _node_file(
        node: dict[str, Any],
    ) -> str | None:
        loc = node.get("loc", {})

        if isinstance(loc, dict) and loc.get("file"):
            return str(loc["file"])

        node_range = node.get("range", {})

        if isinstance(node_range, dict):
            begin = node_range.get("begin", {})

            if isinstance(begin, dict) and begin.get("file"):
                return str(begin["file"])

            end = node_range.get("end", {})

            if isinstance(end, dict) and end.get("file"):
                return str(end["file"])

        return None

    def _extract_call_name(
        self,
        call_node: dict[str, Any],
    ) -> str:
        """
        The first child of a call expression normally represents
        the function or method being called.
        """
        children = call_node.get("inner", [])

        if not children:
            return ""

        first_child = children[0]

        if not isinstance(first_child, dict):
            return ""

        return self._expression_name(first_child)

    def _expression_name(
        self,
        node: dict[str, Any],
    ) -> str:
        kind = node.get("kind", "")

        if kind == "DeclRefExpr":
            referenced = node.get("referencedDecl", {})

            if isinstance(referenced, dict):
                name = referenced.get("name")

                if name:
                    return str(name)

            return str(node.get("name") or "")

        if kind in {
            "MemberExpr",
            "UnresolvedMemberExpr",
            "CXXDependentScopeMemberExpr",
        }:
            member_name = str(
                node.get("name")
                or node.get("member")
                or ""
            )

            children = node.get("inner", [])

            if children and isinstance(children[0], dict):
                object_name = self._expression_name(
                    children[0]
                )

                if object_name and member_name:
                    return f"{object_name}.{member_name}"

            return member_name

        if kind in {
            "UnresolvedLookupExpr",
            "DependentScopeDeclRefExpr",
        }:
            return str(
                node.get("name")
                or node.get("lookups", [{}])[0].get(
                    "name",
                    "",
                )
            )

        # Wrapper expressions such as ImplicitCastExpr,
        # ParenExpr and UnaryOperator generally contain the
        # actual declaration reference as a child.
        for child in node.get("inner", []):
            if not isinstance(child, dict):
                continue

            name = self._expression_name(child)

            if name:
                return name

        return ""

    @staticmethod
    def _is_recursive_call(
        call_name: str,
        current_function: str,
    ) -> bool:
        return (
            call_name == current_function
            or call_name.endswith(
                f".{current_function}"
            )
            or call_name.endswith(
                f"::{current_function}"
            )
        )


def ast_to_analysis(
    ast: dict[str, Any],
    source_path: str | Path,
) -> CommonAnalysis:
    visitor = ClangVisitor(source_path)
    visitor.visit(ast)

    return visitor.result