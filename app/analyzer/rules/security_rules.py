import ast
from app.models.finding import Finding, Severity

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

                    findings.append(
    Finding(
        rule_id="SEC001",
        category="security",
        severity=Severity.HIGH,
        confidence=1.0,
        line=node.lineno,
        message=dangerous_functions[function_name],
        explanation=(
            f"The function '{function_name}' "
            "can execute dynamically supplied code."
        ),
        suggestion=(
            "Avoid dynamic code execution and use "
            "a safer alternative."
        )
    )
)
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

                    findings.append(
    Finding(
        rule_id="SEC002",
        category="security",
        severity=Severity.HIGH,
        confidence=0.85,
        line=node.lineno,
        variable_name=target.id,
        message=(
            f"Possible hardcoded secret in "
            f"variable '{target.id}'."
        ),
        explanation=(
            "Secrets stored directly in source code "
            "can accidentally be exposed."
        ),
        suggestion=(
            "Use environment variables or a "
            "dedicated secrets manager."
        )
    )
)

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

                           findings.append(
    Finding(
        rule_id="SEC003",
        category="security",
        severity=Severity.MEDIUM,
        confidence=0.75,
        line=node.lineno,
        message=(
            f"Potentially dangerous "
            f"{module_name}.{function_name}() usage."
        ),
        explanation=(
            "Command execution APIs can become dangerous "
            "when they receive untrusted input."
        ),
        suggestion=(
            "Validate input and avoid shell execution "
            "when possible."
        )
    )
)

        return findings 