import ast
from app.models.finding import Finding, Severity

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

                findings.append(
    Finding(
        rule_id="QUAL001",
        category="code_quality",
        severity=Severity.MEDIUM,
        confidence=1.0,
        line=node.lineno,
        message=(
            f"Function '{node.name}' "
            f"is {function_length} lines long."
        ),
        explanation=(
            "Large functions are generally harder "
            "to understand, test, and maintain."
        ),
        suggestion=(
            "Consider breaking the function "
            "into smaller functions."
        )
    )
)

        return findings

    def check_too_many_parameters(self, tree):

        findings = []

        for node in ast.walk(tree):

            if not isinstance(node, ast.FunctionDef):
                continue

            parameter_count = len(node.args.args)

            if parameter_count > 5:

                findings.append(
    Finding(
        rule_id="QUAL002",
        category="code_quality",
        severity=Severity.LOW,
        confidence=0.9,
        line=node.lineno,
        message=(
            f"Function '{node.name}' has "
            f"{parameter_count} parameters."
        ),
        explanation=(
            "Functions with many parameters can "
            "become difficult to use and maintain."
        ),
        suggestion=(
            "Consider grouping related parameters "
            "into an object or data structure."
        )
    )
)

        return findings