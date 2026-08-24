import ast


class SecurityRules:

    def check_dangerous_functions(self, tree):

        findings = []

        dangerous_functions = {
            "eval": "eval() can execute arbitrary code.",
            "exec": "exec() can execute arbitrary code.",
            "compile": "compile() can dynamically create executable code."
        }

        for node in ast.walk(tree):

            if not isinstance(node, ast.Call):
                continue

            if isinstance(node.func, ast.Name):

                function_name = node.func.id

                if function_name in dangerous_functions:

                    findings.append({
                        "rule_id": "SEC001",
                        "category": "security",
                        "severity": "HIGH",
                        "line": node.lineno,
                        "message": dangerous_functions[function_name]
                    })

        return findings