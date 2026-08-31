import ast
from app.models.finding import Finding, Severity

class QualityAgent:
    """
    Checks code quality guidelines deterministically using Python AST parsing.
    """
    def analyze(self, file_path: str, code: str) -> list[Finding]:
        findings = []
        try:
            tree = ast.parse(code, filename=file_path)
        except Exception:
            # Return empty if code doesn't parse
            return findings

        for node in ast.walk(tree):
            # Check functions/methods length, nesting, and docstrings
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                func_line = node.lineno
                
                # Check func length (QUAL001)
                if node.end_lineno and (node.end_lineno - node.lineno + 1) > 50:
                    findings.append(Finding(
                        rule_id="QUAL001",
                        category="quality",
                        severity=Severity.MEDIUM,
                        confidence=0.95,
                        file=file_path,
                        line=func_line,
                        message=f"Function '{func_name}' is too long ({node.end_lineno - node.lineno + 1} lines).",
                        explanation="Functions exceeding 50 lines are harder to read, maintain, and test.",
                        suggestion="Refactor the function by extracting smaller helper functions.",
                        source="quality_agent",
                        sources=["quality_agent"]
                    ))

                # Check nesting depth (QUAL002)
                max_depth = self._get_max_nesting(node, 0)
                if max_depth > 4:
                    findings.append(Finding(
                        rule_id="QUAL002",
                        category="quality",
                        severity=Severity.HIGH,
                        confidence=0.95,
                        file=file_path,
                        line=func_line,
                        message=f"Function '{func_name}' has excessive nesting depth ({max_depth}).",
                        explanation="Deep nesting (greater than 4 levels of control flow) increases cognitive load and makes debugging difficult.",
                        suggestion="Flatten the function by using early returns/guards or helper functions.",
                        source="quality_agent",
                        sources=["quality_agent"]
                    ))

                # Check missing docstring (QUAL003)
                if node.end_lineno and (node.end_lineno - node.lineno + 1) > 5:
                    if ast.get_docstring(node) is None:
                        findings.append(Finding(
                            rule_id="QUAL003",
                            category="quality",
                            severity=Severity.LOW,
                            confidence=0.90,
                            file=file_path,
                            line=func_line,
                            message=f"Function '{func_name}' is missing a docstring.",
                            explanation="Non-trivial functions (over 5 lines) should document their purpose, parameters, and return value.",
                            suggestion="Add a docstring describing what the function does.",
                            source="quality_agent",
                            sources=["quality_agent"]
                        ))

            # Check bare except clauses (QUAL004)
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    findings.append(Finding(
                        rule_id="QUAL004",
                        category="quality",
                        severity=Severity.MEDIUM,
                        confidence=0.99,
                        file=file_path,
                        line=node.lineno,
                        message="Bare 'except:' clause used.",
                        explanation="Bare except clauses catch all exceptions, including SystemExit and KeyboardInterrupt, which can hide bugs.",
                        suggestion="Specify a concrete exception class (like Exception or ValueError) instead of a bare except.",
                        source="quality_agent",
                        sources=["quality_agent"]
                    ))

        return findings

    def _get_max_nesting(self, node, current_depth: int) -> int:
        nesting_types = (ast.If, ast.For, ast.While, ast.Try)
        is_nesting = isinstance(node, nesting_types)
        new_depth = current_depth + 1 if is_nesting else current_depth

        max_child = new_depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Do not recurse into inner functions or classes
                continue
            max_child = max(max_child, self._get_max_nesting(child, new_depth))
        return max_child
