import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { parse } = require("@babel/parser");


function emptyResult() {
    return {
        syntax_valid: true,
        syntax_error: null,

        functions: [],
        classes: [],
        calls: [],
        recursive_functions: [],
        imports: [],

        loop_count: 0,
        for_loop_count: 0,
        while_loop_count: 0,
        maximum_loop_depth: 0,

        condition_count: 0,
        return_count: 0,
    };
}


function readStdin() {
    return new Promise((resolve, reject) => {
        let source = "";

        process.stdin.setEncoding("utf8");

        process.stdin.on("data", (chunk) => {
            source += chunk;
        });

        process.stdin.on("end", () => {
            resolve(source);
        });

        process.stdin.on("error", reject);
    });
}


function propertyName(node) {
    if (!node) {
        return "";
    }

    if (node.type === "Identifier") {
        return node.name;
    }

    if (
        node.type === "StringLiteral" ||
        node.type === "NumericLiteral"
    ) {
        return String(node.value);
    }

    if (node.type === "PrivateName") {
        return propertyName(node.id);
    }

    return "";
}


function expressionName(node) {
    if (!node) {
        return "";
    }

    if (node.type === "Identifier") {
        return node.name;
    }

    if (node.type === "ThisExpression") {
        return "this";
    }

    if (node.type === "Super") {
        return "super";
    }

    if (
        node.type === "MemberExpression" ||
        node.type === "OptionalMemberExpression"
    ) {
        const objectName = expressionName(node.object);

        const memberName = node.computed
            ? propertyName(node.property)
            : propertyName(node.property);

        if (objectName && memberName) {
            return `${objectName}.${memberName}`;
        }

        return memberName || objectName;
    }

    return "";
}


function functionName(node, parent) {
    if (
        node.type === "FunctionDeclaration" &&
        node.id?.name
    ) {
        return node.id.name;
    }

    if (
        node.type === "FunctionExpression" ||
        node.type === "ArrowFunctionExpression"
    ) {
        if (node.id?.name) {
            return node.id.name;
        }

        if (
            parent?.type === "VariableDeclarator" &&
            parent.id?.type === "Identifier"
        ) {
            return parent.id.name;
        }

        if (
            parent?.type === "AssignmentExpression"
        ) {
            return expressionName(parent.left);
        }

        if (
            parent?.type === "ObjectProperty" ||
            parent?.type === "ClassProperty"
        ) {
            return propertyName(parent.key);
        }
    }

    if (
        node.type === "ClassMethod" ||
        node.type === "ClassPrivateMethod" ||
        node.type === "ObjectMethod"
    ) {
        return propertyName(node.key);
    }

    return "";
}


function className(node, parent) {
    if (node.id?.name) {
        return node.id.name;
    }

    if (
        parent?.type === "VariableDeclarator" &&
        parent.id?.type === "Identifier"
    ) {
        return parent.id.name;
    }

    return "";
}


function isFunctionNode(node) {
    return [
        "FunctionDeclaration",
        "FunctionExpression",
        "ArrowFunctionExpression",
        "ClassMethod",
        "ClassPrivateMethod",
        "ObjectMethod",
    ].includes(node.type);
}


function isForLoop(node) {
    return [
        "ForStatement",
        "ForInStatement",
        "ForOfStatement",
    ].includes(node.type);
}


function isWhileLoop(node) {
    return [
        "WhileStatement",
        "DoWhileStatement",
    ].includes(node.type);
}


function isLoop(node) {
    return isForLoop(node) || isWhileLoop(node);
}


function analyseAst(ast) {
    const result = emptyResult();

    const functions = new Set();
    const classes = new Set();
    const calls = new Set();
    const recursiveFunctions = new Set();
    const imports = new Set();

    const functionStack = [];
    let loopDepth = 0;

    function walk(node, parent = null) {
        if (!node || typeof node !== "object") {
            return;
        }

        if (Array.isArray(node)) {
            for (const child of node) {
                walk(child, parent);
            }
            return;
        }

        if (typeof node.type !== "string") {
            return;
        }

        let enteredFunction = false;
        let enteredLoop = false;

        if (isFunctionNode(node)) {
            const name = functionName(node, parent);

            if (name) {
                functions.add(name);
                functionStack.push(name);
                enteredFunction = true;
            }
        }

        if (
            node.type === "ClassDeclaration" ||
            node.type === "ClassExpression"
        ) {
            const name = className(node, parent);

            if (name) {
                classes.add(name);
            }
        }

        if (isLoop(node)) {
            result.loop_count += 1;
            loopDepth += 1;
            enteredLoop = true;

            result.maximum_loop_depth = Math.max(
                result.maximum_loop_depth,
                loopDepth
            );

            if (isForLoop(node)) {
                result.for_loop_count += 1;
            }

            if (isWhileLoop(node)) {
                result.while_loop_count += 1;
            }
        }

        if (
            node.type === "IfStatement" ||
            node.type === "ConditionalExpression"
        ) {
            result.condition_count += 1;
        }

        if (node.type === "ReturnStatement") {
            result.return_count += 1;
        }

        if (node.type === "ImportDeclaration") {
            if (node.source?.value) {
                imports.add(String(node.source.value));
            }
        }

        if (node.type === "CallExpression") {
            const callName = expressionName(node.callee);

            if (callName) {
                calls.add(callName);

                const currentFunction =
                    functionStack.length > 0
                        ? functionStack[
                            functionStack.length - 1
                        ]
                        : null;

                if (
                    currentFunction &&
                    (
                        callName === currentFunction ||
                        callName.endsWith(
                            `.${currentFunction}`
                        )
                    )
                ) {
                    recursiveFunctions.add(
                        currentFunction
                    );
                }
            }

            // Treat require("module") as an import.
            if (
                node.callee?.type === "Identifier" &&
                node.callee.name === "require" &&
                node.arguments?.[0]?.type ===
                    "StringLiteral"
            ) {
                imports.add(
                    String(node.arguments[0].value)
                );
            }
        }

        for (const [key, value] of Object.entries(node)) {
            if (
                key === "loc" ||
                key === "start" ||
                key === "end" ||
                key === "extra" ||
                key === "errors" ||
                key === "tokens"
            ) {
                continue;
            }

            if (Array.isArray(value)) {
                for (const child of value) {
                    if (
                        child &&
                        typeof child === "object" &&
                        typeof child.type === "string"
                    ) {
                        walk(child, node);
                    }
                }
            } else if (
                value &&
                typeof value === "object" &&
                typeof value.type === "string"
            ) {
                walk(value, node);
            }
        }

        if (enteredLoop) {
            loopDepth -= 1;
        }

        if (enteredFunction) {
            functionStack.pop();
        }
    }

    walk(ast);

    result.functions = [...functions].sort();
    result.classes = [...classes].sort();
    result.calls = [...calls].sort();

    result.recursive_functions = [
        ...recursiveFunctions,
    ].sort();

    result.imports = [...imports].sort();

    return result;
}


async function main() {
    const source = await readStdin();

    try {
        const ast = parse(source, {
            sourceType: "unambiguous",
            errorRecovery: false,
            attachComment: false,
            plugins: [
                "jsx",
            ],
        });

        const result = analyseAst(ast);

        process.stdout.write(
            JSON.stringify(result)
        );
    } catch (error) {
        const line = error.loc?.line ?? 0;
        const column = error.loc?.column ?? 0;

        const result = emptyResult();

        result.syntax_valid = false;
        result.syntax_error =
            `Syntax error on line ${line}, ` +
            `column ${column}: ${error.message}`;

        process.stdout.write(
            JSON.stringify(result)
        );
    }
}


main().catch((error) => {
    process.stderr.write(
        error instanceof Error
            ? error.message
            : String(error)
    );

    process.exitCode = 1;
});