import ast

from app.models.finding import Finding


class ValidationResult:

    VALID = "valid"
    INVALID = "invalid"
    UNVERIFIED = "unverified"


class FindingValidator:

    def validate(
        self,
        code: str,
        finding: Finding
    ) -> str:

        finding_sources = set(finding.sources) if finding.sources else {finding.source}
        if "ai" not in finding_sources:
            return ValidationResult.VALID

        try:
            tree = ast.parse(code)

        except SyntaxError:
            return ValidationResult.INVALID

        message = finding.message.lower()

        # --------------------------------
        # eval
        # --------------------------------

        if "eval" in message:

            if self._contains_call(tree, "eval"):

                return ValidationResult.VALID

            return ValidationResult.INVALID

        # --------------------------------
        # exec
        # --------------------------------

        if "exec" in message:

            if self._contains_call(tree, "exec"):

                return ValidationResult.VALID

            return ValidationResult.INVALID

        # --------------------------------
        # subprocess
        # --------------------------------

        if "subprocess" in message:

            if self._contains_import(
                tree,
                "subprocess"
            ):

                return ValidationResult.VALID

            return ValidationResult.INVALID

        # --------------------------------
        # hardcoded secrets
        # --------------------------------

        if (
            "secret" in message
            or "api key" in message
            or "hardcoded" in message
        ):

            if self._contains_suspicious_variable(
                tree
            ):

                return ValidationResult.VALID

            return ValidationResult.INVALID

        # --------------------------------
        # Unknown finding
        # --------------------------------

        return ValidationResult.UNVERIFIED

    def _contains_call(
        self,
        tree,
        function_name
    ):

        for node in ast.walk(tree):

            if isinstance(node, ast.Call):

                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id == function_name
                ):

                    return True

        return False

    def _contains_import(
        self,
        tree,
        module_name
    ):

        for node in ast.walk(tree):

            if isinstance(node, ast.Import):

                for alias in node.names:

                    if alias.name == module_name:

                        return True

            if isinstance(node, ast.ImportFrom):

                if node.module == module_name:

                    return True

        return False

    def _contains_suspicious_variable(
        self,
        tree
    ):

        suspicious_names = {
            "API_KEY",
            "SECRET",
            "SECRET_KEY",
            "PASSWORD",
            "TOKEN",
            "API_TOKEN"
        }

        for node in ast.walk(tree):

            if isinstance(node, ast.Assign):

                for target in node.targets:

                    if isinstance(
                        target,
                        ast.Name
                    ):

                        if target.id.upper() in suspicious_names:

                            return True

        return False