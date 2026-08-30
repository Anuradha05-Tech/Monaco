import ast
import logging
from pathlib import Path
from app.scanner.repository_scanner import RepositoryScanner
from app.analyzer.dependency_analyzer import DependencyAnalyzer

logger = logging.getLogger(__name__)


class DependencyGraphBuilder:
    """
    Builds a dependency graph of Python files within a repository.

    It scans the repository for Python files, extracts their imports using the AST-based
    DependencyAnalyzer, and resolves the imports to local file paths relative to the repository root.
    """

    def __init__(self):
        self.analyzer = DependencyAnalyzer()

    def build(self, repo_root: str) -> dict[str, list[str]]:
        """
        Scans the repository and builds the dependency graph.

        Args:
            repo_root: Absolute path to the repository root.

        Returns:
            A dictionary representing the dependency graph. Keys and values
            are file paths relative to the repo_root.
        """
        repo_path = Path(repo_root).resolve()
        scanner = RepositoryScanner(str(repo_path))

        # Scan all files in the repository
        all_files = scanner.scan()

        # Collect all Python files as relative path strings (using forward slashes)
        python_files = set()
        for f in all_files:
            if f["language"] == "Python" or f["extension"] == ".py":
                f_path = Path(f["path"])
                try:
                    rel_path = f_path.resolve().relative_to(repo_path)
                except ValueError:
                    rel_path = f_path.relative_to(repo_path)
                python_files.add(rel_path.as_posix())

        graph = {}

        for rel_file_path in python_files:
            abs_file_path = repo_path / rel_file_path
            code = scanner.read_file(str(abs_file_path))

            if code is None:
                continue

            # Verify for syntax errors to log warning and skip resolution gracefully
            try:
                ast.parse(code)
            except SyntaxError as e:
                logger.warning(f"Syntax error in file {rel_file_path}: {e}")
                continue

            # Get raw import strings
            raw_imports = self.analyzer.analyze(code)

            resolved_imports = []
            for imp in raw_imports:
                resolved = self._resolve_import(rel_file_path, imp, python_files)
                if resolved:
                    resolved_imports.append(resolved)

            # Deduplicate and sort resolved imports
            graph[rel_file_path] = sorted(list(set(resolved_imports)))

        return graph

    def _resolve_import(self, current_file: str, imp: str, python_files: set[str]) -> str | None:
        """
        Resolves a raw import name to a local Python file path relative to repo root.

        Args:
            current_file: The relative path of the file containing the import.
            imp: The raw import string to resolve.
            python_files: Set of all Python file relative paths in the repository.

        Returns:
            The resolved relative file path of the imported module, or None if it cannot be resolved.
        """
        # 1. Relative import
        if imp.startswith("."):
            num_dots = len(imp) - len(imp.lstrip("."))
            module_part = imp[num_dots:]

            curr_path = Path(current_file)
            base_dir = curr_path.parent

            # Go up num_dots - 1 times
            for _ in range(num_dots - 1):
                if base_dir == Path(".") or base_dir == Path(""):
                    return None
                base_dir = base_dir.parent

            if module_part:
                module_subpath = module_part.replace(".", "/")
                target_path = base_dir / module_subpath
            else:
                target_path = base_dir
        else:
            # 2. Absolute import
            module_subpath = imp.replace(".", "/")
            target_path = Path(module_subpath)

        # Check for target_path as module (.py) or package (__init__.py)
        py_module_norm = target_path.with_suffix(".py").as_posix()
        py_package_norm = (target_path / "__init__.py").as_posix()

        # Remove leading './' if any
        if py_module_norm.startswith("./"):
            py_module_norm = py_module_norm[2:]
        if py_package_norm.startswith("./"):
            py_package_norm = py_package_norm[2:]

        if py_module_norm in python_files:
            return py_module_norm
        if py_package_norm in python_files:
            return py_package_norm

        # Fallback check for absolute imports under subdirectories (e.g. src/)
        if not imp.startswith("."):
            suffix_module = "/" + py_module_norm
            suffix_package = "/" + py_package_norm
            for f in python_files:
                if f.endswith(suffix_module) or f == py_module_norm:
                    return f
                if f.endswith(suffix_package) or f == py_package_norm:
                    return f

        return None
