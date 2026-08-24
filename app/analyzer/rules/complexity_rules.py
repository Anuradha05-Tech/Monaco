import ast


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
                        ast.ExceptHandler
                    )
                ):
                    complexity += 1

            if complexity > 5:

                findings.append({
                    "rule_id": "COMP001",
                    "category": "complexity",
                    "severity": "MEDIUM",
                    "line": node.lineno,
                    "message": (
                        f"Function '{node.name}' "
                        f"has a complexity score of "
                        f"{complexity}."
                    )
                })

        return findings