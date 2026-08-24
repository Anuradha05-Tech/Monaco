from app.analyzer.python_analyzer import PythonAnalyzer


def test_eval_is_detected():

    code = """
user_input = input("Enter something")
result = eval(user_input)
"""

    analyzer = PythonAnalyzer()

    result = analyzer.analyze(code)

    findings = result["findings"]

    assert len(findings) == 1
    assert findings[0]["rule_id"] == "SEC001"
    assert findings[0]["severity"] == "HIGH"


def test_exec_is_detected():

    code = """
user_input = input("Enter something")
exec(user_input)
"""

    analyzer = PythonAnalyzer()

    result = analyzer.analyze(code)

    findings = result["findings"]

    assert len(findings) == 1
    assert findings[0]["rule_id"] == "SEC001"


def test_safe_code_has_no_security_issue():

    code = """
def add(a, b):
    return a + b
"""

    analyzer = PythonAnalyzer()

    result = analyzer.analyze(code)

    findings = result["findings"]

    assert len(findings) == 0


def test_multiple_dangerous_calls():

    code = """
eval(user_input)
exec(user_input)
"""

    analyzer = PythonAnalyzer()

    result = analyzer.analyze(code)

    findings = result["findings"]

    assert len(findings) == 2


def test_hardcoded_secret_is_detected():

    code = """
API_KEY = "secret-value"
"""

    analyzer = PythonAnalyzer()

    result = analyzer.analyze(code)

    findings = result["findings"]

    assert len(findings) == 1
    assert findings[0]["rule_id"] == "SEC002"


def test_safe_string_is_not_detected_as_secret():

    code = """
name = "Anuradha"
"""

    analyzer = PythonAnalyzer()

    result = analyzer.analyze(code)

    findings = result["findings"]

    assert len(findings) == 0


def test_subprocess_usage_is_detected():

    code = """
import subprocess

subprocess.run(command)
"""

    analyzer = PythonAnalyzer()

    result = analyzer.analyze(code)

    findings = result["findings"]

    assert len(findings) == 1
    assert findings[0]["rule_id"] == "SEC003"