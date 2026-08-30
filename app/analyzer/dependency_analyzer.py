import ast


class DependencyAnalyzer:
    """
    Analyzes Python source code to extract import dependencies using the AST.

    This class plays a crucial role in building the application's dependency graph.
    By parsing the Abstract Syntax Tree (AST) of a Python source file, it identifies
    all absolute and relative module imports. This list of imported module names
    will be used in future phases to map dependencies, detect circular imports,
    and analyze project structure.
    """

    def analyze(self, source_code: str) -> list[str]:
        """
        Parses the given Python source code and extracts all imported module/package names.

        Args:
            source_code: The Python source code string to analyze.

        Returns:
            A deduplicated, sorted list of imported module/package names as strings.
            If a syntax error occurs during parsing, an empty list is returned.

        Notes on relative imports:
            Relative imports are represented with leading dots indicating the level of
            relativity, followed by the module name or the imported names if no module is
            specified. For example:
              - `from .foo import bar` -> `.foo`
              - `from . import utils`  -> `.utils`
              - `from ..bar import baz` -> `..bar`
              - `from .. import config` -> `..config`
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return []

        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                # node.level: 0 for absolute imports, > 0 for relative imports
                if node.level > 0:
                    prefix = "." * node.level
                    if node.module is not None:
                        imports.add(prefix + node.module)
                    else:
                        for alias in node.names:
                            imports.add(prefix + alias.name)
                else:
                    if node.module is not None:
                        imports.add(node.module)

        return sorted(list(imports))
