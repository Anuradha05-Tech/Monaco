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

    def check_too_many_parameters(self, tree):

        findings = []

        for node in ast.walk(tree):

            if not isinstance(node, ast.FunctionDef):
                continue

            parameter_count = len(node.args.args)

            if parameter_count > 5:

                findings.append({
                    "rule_id": "QUAL002",
                    "category": "code_quality",
                    "severity": "LOW",
                    "line": node.lineno,
                    "message": (
                        f"Function '{node.name}' has "
                        f"{parameter_count} parameters. "
                        "Consider grouping related parameters."
                    )
                })

        return findings