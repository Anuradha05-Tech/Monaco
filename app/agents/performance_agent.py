import ast
from app.models.finding import Finding, Severity

class PerformanceAgent:
    """
    Checks code performance guidelines deterministically using Python AST parsing.
    """
    def analyze(self, file_path: str, code: str) -> list[Finding]:
        findings = []
        try:
            tree = ast.parse(code, filename=file_path)
        except Exception:
            return findings

        # We will walk the tree to find loops and function calls
        # To handle PERF001, we want to know if we are inside a loop
        self._check_node(tree, False, set(), findings, file_path)
        return findings

    def _check_node(self, node, in_loop: bool, string_vars: set[str], findings: list[Finding], file_path: str):
        # If we enter a function definition, we scan for string variable initializations
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            local_string_vars = set()
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name):
                            if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                                local_string_vars.add(target.id)
            
            # Recursively check children within the function scope
            for child in ast.iter_child_nodes(node):
                self._check_node(child, in_loop, local_string_vars, findings, file_path)
            return

        # Check for loop entry
        is_loop = isinstance(node, (ast.For, ast.While))
        current_in_loop = in_loop or is_loop

        # PERF001: String concatenation via += inside a loop
        if current_in_loop and isinstance(node, ast.AugAssign):
            if isinstance(node.op, ast.Add):
                # Target is variable
                if isinstance(node.target, ast.Name):
                    var_name = node.target.id
                    is_str_constant = isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
                    if var_name in string_vars or is_str_constant:
                        findings.append(Finding(
                            rule_id="PERF001",
                            category="performance",
                            severity=Severity.LOW,
                            confidence=0.90,
                            file=file_path,
                            line=node.lineno,
                            message=f"String concatenation via '+=' on '{var_name}' inside a loop.",
                            explanation="Building strings inside loops using += is inefficient because strings are immutable, causing O(N^2) memory reallocations.",
                            suggestion="Use a list buffer to append elements and merge them using ''.join() after the loop.",
                            source="performance_agent",
                            sources=["performance_agent"]
                        ))

        # PERF002: passing list comprehension or list literal to sum/any/all/min/max
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {"sum", "any", "all", "min", "max"}:
                if len(node.args) >= 1:
                    arg = node.args[0]
                    if isinstance(arg, (ast.ListComp, ast.List)):
                        msg = f"Unnecessary list instantiation passed to '{node.func.id}()'."
                        suggestion = f"Remove the square brackets to pass a generator expression to '{node.func.id}()'."
                        findings.append(Finding(
                            rule_id="PERF002",
                            category="performance",
                            severity=Severity.LOW,
                            confidence=0.95,
                            file=file_path,
                            line=node.lineno,
                            message=msg,
                            explanation=f"Passing a list comprehension or list literal to '{node.func.id}()' forces python to construct the entire list in memory, whereas a generator expression evaluates lazily.",
                            suggestion=suggestion,
                            source="performance_agent",
                            sources=["performance_agent"]
                        ))

        # Recurse for all other nodes
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # This will be handled by the function entry branch above
                self._check_node(child, in_loop, string_vars, findings, file_path)
            else:
                self._check_node(child, current_in_loop, string_vars, findings, file_path)
