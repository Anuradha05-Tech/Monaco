import ast
from app.models.finding import Finding, Severity

class ComplexityRules:

    def check_complex_functions(self, tree):

        findings = []

        for node in ast.walk(tree):

            if not isinstance(node, ast.FunctionDef):
                continue

            complexity = 1

            for child in ast.walk(node):

                if isinstance(
                    child,
                    (
                        ast.If,
                        ast.For,
                        ast.While,
                        ast.ExceptHandler,
                        ast.With,
                        ast.IfExp
                    )
                ):
                    complexity += 1

            if complexity > 5:

                findings.append(
                    Finding(
                        rule_id="COMP001",
                        category="complexity",
                        severity=Severity.MEDIUM,
                        confidence=1.0,
                        line=node.lineno,
                        message=(
                            f"Function '{node.name}' "
                            f"has a complexity score of "
                            f"{complexity}."
                        ),
                        explanation=(
                            f"Function '{node.name}' has a high cyclomatic complexity "
                            "indicating too many decision points."
                        ),
                        suggestion="Consider refactoring or splitting the function.",
                        source="static_analyzer",
                        sources=["static_analyzer"]
                    )
                )


        return findings