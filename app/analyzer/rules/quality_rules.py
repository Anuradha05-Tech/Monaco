import ast


class QualityRules:

    def check_long_functions(self, tree):

        findings = []

        for node in ast.walk(tree):

            if not isinstance(node, ast.FunctionDef):
                continue

            function_length = (
                node.end_lineno - node.lineno + 1
            )

            if function_length > 20:

                findings.append({
                    "rule_id": "QUAL001",
                    "category": "code_quality",
                    "severity": "MEDIUM",
                    "line": node.lineno,
                    "message": (
                        f"Function '{node.name}' "
                        f"is {function_length} lines long. "
                        "Consider breaking it into smaller functions."
                    )
                })

        return findings