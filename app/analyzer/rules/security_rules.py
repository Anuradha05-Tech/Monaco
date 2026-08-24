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

    def check_hardcoded_secrets(self, tree):

        findings = []

        secret_keywords = {
            "password",
            "passwd",
            "api_key",
            "apikey",
            "secret",
            "token",
            "access_key"
        }

        for node in ast.walk(tree):

            if not isinstance(node, ast.Assign):
                continue

            if not isinstance(node.value, ast.Constant):
                continue

            if not isinstance(node.value.value, str):
                continue

            value = node.value.value

            # Ignore empty strings
            if not value:
                continue

            for target in node.targets:

                if not isinstance(target, ast.Name):
                    continue

                variable_name = target.id.lower()

                if any(
                    keyword in variable_name
                    for keyword in secret_keywords
                ):

                    findings.append({
                        "rule_id": "SEC002",
                        "category": "security",
                        "severity": "HIGH",
                        "line": node.lineno,
                        "message": (
                            f"Possible hardcoded secret in "
                            f"variable '{target.id}'."
                        )
                    })

        return findings

    def check_dangerous_subprocess(self, tree):

        findings = []

        dangerous_modules = {
            "subprocess",
            "os"
        }

        for node in ast.walk(tree):

            if isinstance(node, ast.Call):

                if isinstance(node.func, ast.Attribute):

                    if isinstance(node.func.value, ast.Name):

                        module_name = node.func.value.id
                        function_name = node.func.attr

                        if (
                            module_name in dangerous_modules
                            and function_name in {
                                "system",
                                "popen",
                                "run",
                                "call"
                            }
                        ):

                            findings.append({
                                "rule_id": "SEC003",
                                "category": "security",
                                "severity": "MEDIUM",
                                "line": node.lineno,
                                "message": (
                                    f"Potentially dangerous "
                                    f"{module_name}.{function_name}() "
                                    f"usage."
                                )
                            })

        return findings