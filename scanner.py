
import ast
from pathlib import Path


IGNORED_DIRS = {
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build"
}


def get_call_name(node):
    """Extract a readable function or method call name."""

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = get_call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return None


class CodeAnalyzer(ast.NodeVisitor):

    def __init__(self, source, filename):
        self.source = source
        self.filename = filename

        self.functions = []
        self.imports = []

        self.function_stack = []
        self.class_stack = []

    def visit_ClassDef(self, node):
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node):
        self.analyze_function(node)

    def visit_AsyncFunctionDef(self, node):
        self.analyze_function(node)

    def analyze_function(self, node):

        qualified_name = ".".join(
            self.class_stack + self.function_stack + [node.name]
        )

        function_info = {
            "name": node.name,
            "qualified_name": qualified_name,
            "file": self.filename,
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", None),
            "arguments": [
                arg.arg for arg in node.args.args
            ],
            "docstring": ast.get_docstring(node) or "",
            "calls": [],
            "returns_value": False
        }

        self.functions.append(function_info)
        self.function_stack.append(node.name)

        # Inspect the function's body.
        for child in node.body:
            self.visit(child)

        self.function_stack.pop()

    def visit_Call(self, node):

        if self.function_stack:
            call_name = get_call_name(node.func)

            if call_name:
                current_function = self.functions[-1]

                if call_name not in current_function["calls"]:
                    current_function["calls"].append(call_name)

        self.generic_visit(node)

    def visit_Return(self, node):

        if self.function_stack and node.value is not None:
            self.functions[-1]["returns_value"] = True

        self.generic_visit(node)

    def visit_Import(self, node):

        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node):

        module = node.module or ""

        for alias in node.names:
            self.imports.append(
                f"{module}.{alias.name}"
            )


def scan_project(project_path):

    root = Path(project_path).expanduser().resolve()

    if not root.exists() or not root.is_dir():
        raise ValueError("Please provide a valid project directory.")

    all_functions = []
    all_imports = set()
    scanned_files = []
    errors = []

    for file_path in root.rglob("*.py"):

        if any(part in IGNORED_DIRS for part in file_path.parts):
            continue

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))

            relative_path = str(file_path.relative_to(root))

            analyzer = CodeAnalyzer(source, relative_path)
            analyzer.visit(tree)

            all_functions.extend(analyzer.functions)
            all_imports.update(analyzer.imports)
            scanned_files.append(relative_path)

        except (SyntaxError, UnicodeDecodeError, OSError) as error:
            errors.append({
                "file": str(file_path),
                "error": str(error)
            })

    return {
        "project": root.name,
        "files_scanned": scanned_files,
        "total_files": len(scanned_files),
        "total_functions": len(all_functions),
        "functions": all_functions,
        "imports": sorted(all_imports),
        "errors": errors
    }
