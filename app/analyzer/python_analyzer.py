import ast

from app.analyzer.rules.security_rules import SecurityRules
from app.analyzer.rules.quality_rules import QualityRules
from app.analyzer.rules.complexity_rules import ComplexityRules


class PythonAnalyzer:

    def __init__(self):

        self.security_rules = SecurityRules()
        self.quality_rules = QualityRules()
        self.complexity_rules = ComplexityRules()

    def analyze(self, code):

        tree = ast.parse(code)

        result = {
            "functions": [],
            "classes": [],
            "imports": [],
            "calls": [],
            "lines_of_code": len(code.splitlines()),
            "findings": []
        }

        # -------------------------
        # AST INFORMATION
        # -------------------------

        for node in ast.walk(tree):

            if isinstance(node, ast.FunctionDef):

                parameters = []

                for argument in node.args.args:
                    parameters.append(argument.arg)

                result["functions"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "parameters": parameters
                })

            elif isinstance(node, ast.ClassDef):

                methods = []

                for child in node.body:

                    if isinstance(child, ast.FunctionDef):

                        parameters = []

                        for argument in child.args.args:
                            parameters.append(argument.arg)

                        methods.append({
                            "name": child.name,
                            "line": child.lineno,
                            "parameters": parameters
                        })

                result["classes"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": methods
                })

            elif isinstance(node, ast.Import):

                for alias in node.names:
                    result["imports"].append(alias.name)

            elif isinstance(node, ast.ImportFrom):

                if node.module:
                    result["imports"].append(node.module)

            elif isinstance(node, ast.Call):

                function_name = self.get_call_name(node)

                if function_name:

                    result["calls"].append({
                        "name": function_name,
                        "line": node.lineno
                    })

        # -------------------------
        # RUN STATIC ANALYSIS RULES
        # -------------------------

        security_findings = (
            self.security_rules
            .check_dangerous_functions(tree)
        )

        quality_findings = (
            self.quality_rules
            .check_long_functions(tree)
        )

        complexity_findings = (
            self.complexity_rules
            .check_complex_functions(tree)
        )

        result["findings"].extend(
            security_findings
        )

        result["findings"].extend(
            quality_findings
        )

        result["findings"].extend(
            complexity_findings
        )

        return result

    # -------------------------
    # FUNCTION CALL NAME
    # -------------------------

    def get_call_name(self, node):

        if isinstance(node.func, ast.Name):

            return node.func.id

        if isinstance(node.func, ast.Attribute):

            parts = []

            current = node.func

            while isinstance(current, ast.Attribute):

                parts.append(current.attr)

                current = current.value

            if isinstance(current, ast.Name):

                parts.append(current.id)

                parts.reverse()

                return ".".join(parts)

        return None


# -------------------------
# TEST
# -------------------------

if __name__ == "__main__":

    code = """
import os

def dangerous_function(user_input):

    result = eval(user_input)

    if result:
        return True

    return False
"""

    analyzer = PythonAnalyzer()

    result = analyzer.analyze(code)

    print(result)