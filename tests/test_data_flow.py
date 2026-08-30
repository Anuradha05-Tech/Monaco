from app.analyzer.data_flow_analyzer import DataFlowAnalyzer


def test_input_to_eval_is_detected():

    code = """
user_input = input("Enter something")

result = eval(user_input)
"""

    analyzer = DataFlowAnalyzer()

    findings = analyzer.analyze(code)

    assert len(findings) == 1

    assert findings[0].rule_id == "FLOW001"


def test_safe_eval_is_not_detected():

    code = """
value = 10

result = eval(value)
"""

    analyzer = DataFlowAnalyzer()

    findings = analyzer.analyze(code)

    assert len(findings) == 0


def test_taint_is_propagated_between_variables():

    code = """
user_input = input("Enter something")

command = user_input

result = eval(command)
"""

    analyzer = DataFlowAnalyzer()

    findings = analyzer.analyze(code)

    assert len(findings) == 1

    assert findings[0].rule_id == "FLOW001"


def test_tainted_input_to_subprocess_is_detected():

    code = """
import subprocess

command = input("Enter command")

subprocess.run(
    command,
    shell=True
)
"""

    analyzer = DataFlowAnalyzer()

    findings = analyzer.analyze(code)

    assert len(findings) == 1

    assert findings[0].rule_id == "FLOW002"


def test_safe_subprocess_is_not_detected():

    code = """
import subprocess

subprocess.run(["ls", "-la"])
"""

    analyzer = DataFlowAnalyzer()

    findings = analyzer.analyze(code)

    assert len(findings) == 0


def test_subprocess_without_shell_is_not_detected():

    code = """
import subprocess

command = input("Enter command")

subprocess.run(command)
"""

    analyzer = DataFlowAnalyzer()

    findings = analyzer.analyze(code)

    assert len(findings) == 0


def test_taint_propagation_to_subprocess_is_detected():

    code = """
import subprocess

user_input = input("Enter command")

command = user_input

subprocess.run(
    command,
    shell=True
)
"""

    analyzer = DataFlowAnalyzer()

    findings = analyzer.analyze(code)

    assert len(findings) == 1

    assert findings[0].rule_id == "FLOW002"


def test_eval_before_input_is_not_detected():

    code = """
result = eval(command)

command = input("Enter command")
"""

    analyzer = DataFlowAnalyzer()

    findings = analyzer.analyze(code)

    assert len(findings) == 0


def test_tainted_variable_can_be_overwritten():

    code = """
command = input("Enter command")

command = "safe"

result = eval(command)
"""

    analyzer = DataFlowAnalyzer()

    findings = analyzer.analyze(code)

    assert len(findings) == 0


def test_tainted_variable_stays_tainted_until_overwritten():

    code = """
command = input("Enter command")

result = eval(command)
"""

    analyzer = DataFlowAnalyzer()

    findings = analyzer.analyze(code)

    assert len(findings) == 1

    assert findings[0].rule_id == "FLOW001"