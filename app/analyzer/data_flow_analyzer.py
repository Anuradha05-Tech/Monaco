import ast

from app.models.finding import Finding, Severity


class DataFlowAnalyzer:

    def __init__(self):

        self.tainted_variables = set()
        self.findings = []

    def analyze(self, code):

        self.tainted_variables = set()
        self.findings = []

        tree = ast.parse(code)

        # Process statements in execution order.
        for statement in tree.body:

            self._process_statement(statement)

        return self.findings

    def _process_statement(self, statement):

        # --------------------------------
        # Assignment
        # --------------------------------

        if isinstance(statement, ast.Assign):

            self._process_assignment(statement)

            # The assignment itself may contain
            # a dangerous function call.
            self._process_calls(statement.value)

            return

        # --------------------------------
        # Expression
        # --------------------------------

        if isinstance(statement, ast.Expr):

            self._process_calls(statement.value)

            return

        # --------------------------------
        # Other statements
        # --------------------------------

        self._process_calls(statement)

    def _process_assignment(self, node):

        # --------------------------------
        # SOURCE: input()
        # --------------------------------

        if self._is_input_call(node.value):

            for target in node.targets:

                if isinstance(target, ast.Name):

                    self.tainted_variables.add(
                        target.id
                    )

            return

        # --------------------------------
        # TAINT PROPAGATION
        # --------------------------------

        if isinstance(node.value, ast.Name):

            if node.value.id in self.tainted_variables:

                for target in node.targets:

                    if isinstance(target, ast.Name):

                        self.tainted_variables.add(
                            target.id
                        )

            else:

                # The source variable is not tainted,
                # so the target should not be tainted.

                for target in node.targets:

                    if isinstance(target, ast.Name):

                        self.tainted_variables.discard(
                            target.id
                        )

            return

        # --------------------------------
        # NON-TAINTED VALUE
        # --------------------------------

        # If a previously tainted variable is
        # overwritten by a normal value such as:
        #
        # command = "safe"
        #
        # remove it from the tainted state.

        for target in node.targets:

            if isinstance(target, ast.Name):

                self.tainted_variables.discard(
                    target.id
                )

    def _process_calls(self, node):

        # Walk inside this statement only.
        for child in ast.walk(node):

            if not isinstance(child, ast.Call):
                continue

            # --------------------------------
            # SINK: eval()
            # --------------------------------

            if self._is_eval_call(child):

                if self._has_tainted_argument(child):

                    self.findings.append(
                        Finding(
                            rule_id="FLOW001",
                            category="security",
                            severity=Severity.CRITICAL,
                            confidence=1.0,
                            line=child.lineno,
                            message=(
                                "Untrusted input flows "
                                "into eval()."
                            ),
                            explanation=(
                                "User-controlled input reaches "
                                "eval(), which can execute "
                                "arbitrary Python code."
                            ),
                            suggestion=(
                                "Avoid eval() on untrusted input. "
                                "Use explicit parsing or validation "
                                "instead."
                            ),
                            source="data_flow"
                        )
                    )

            # --------------------------------
            # SINK: subprocess.run()
            # --------------------------------

            if self._is_subprocess_run(child):

                has_tainted_argument = (
                    self._has_tainted_argument(child)
                )

                uses_shell = (
                    self._uses_shell_true(child)
                )

                if (
                    has_tainted_argument
                    and uses_shell
                ):

                    self.findings.append(
                        Finding(
                            rule_id="FLOW002",
                            category="security",
                            severity=Severity.CRITICAL,
                            confidence=1.0,
                            line=child.lineno,
                            message=(
                                "Untrusted input flows into "
                                "subprocess.run() with shell=True."
                            ),
                            explanation=(
                                "User-controlled input reaches "
                                "a shell command execution sink."
                            ),
                            suggestion=(
                                "Avoid shell=True with untrusted "
                                "input. Prefer passing a list of "
                                "validated arguments."
                            ),
                            source="data_flow"
                        )
                    )

    def _is_input_call(self, node):

        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "input"
        )

    def _is_eval_call(self, node):

        return (
            isinstance(node.func, ast.Name)
            and node.func.id == "eval"
        )

    def _is_subprocess_run(self, node):

        if not isinstance(node.func, ast.Attribute):
            return False

        if node.func.attr != "run":
            return False

        if not isinstance(
            node.func.value,
            ast.Name
        ):
            return False

        return node.func.value.id == "subprocess"

    def _has_tainted_argument(self, node):

        for argument in node.args:

            if (
                isinstance(argument, ast.Name)
                and argument.id in self.tainted_variables
            ):

                return True

        return False

    def _uses_shell_true(self, node):

        for keyword in node.keywords:

            if keyword.arg == "shell":

                return (
                    isinstance(
                        keyword.value,
                        ast.Constant
                    )
                    and keyword.value.value is True
                )

        return False