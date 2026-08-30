from app.engine.validator import (
    FindingValidator,
    ValidationResult
)

from app.models.finding import (
    Finding,
    Severity
)


def test_eval_finding_is_validated():

    code = """
user_input = input("Enter input")
result = eval(user_input)
"""

    finding = Finding(
        category="security",
        severity=Severity.HIGH,
        confidence=0.95,
        line=3,
        message="Use of eval on untrusted user input",
        source="ai"
    )

    validator = FindingValidator()

    assert validator.validate(
        code,
        finding
    ) == ValidationResult.VALID


def test_eval_finding_is_rejected_when_eval_missing():

    code = """
user_input = input("Enter input")
result = int(user_input)
"""

    finding = Finding(
        category="security",
        severity=Severity.HIGH,
        confidence=0.95,
        line=3,
        message="Use of eval on untrusted user input",
        source="ai"
    )

    validator = FindingValidator()

    assert validator.validate(
        code,
        finding
    ) == ValidationResult.INVALID


def test_subprocess_finding_is_validated():

    code = """
import subprocess

subprocess.run(command)
"""

    finding = Finding(
        category="security",
        severity=Severity.HIGH,
        confidence=0.95,
        line=4,
        message="Command injection via subprocess.run",
        source="ai"
    )

    validator = FindingValidator()

    assert validator.validate(
        code,
        finding
    ) == ValidationResult.VALID


def test_secret_finding_is_validated():

    code = """
API_KEY = "secret-value"
"""

    finding = Finding(
        category="security",
        severity=Severity.HIGH,
        confidence=0.95,
        line=2,
        message="Hardcoded API key",
        source="ai"
    )

    validator = FindingValidator()

    assert validator.validate(
        code,
        finding
    ) == ValidationResult.VALID


def test_unknown_finding_is_unverified():

    code = """
x = 10
"""

    finding = Finding(
        category="bug",
        severity=Severity.MEDIUM,
        confidence=0.9,
        line=2,
        message="Potential runtime exception",
        source="ai"
    )

    validator = FindingValidator()

    assert validator.validate(
        code,
        finding
    ) == ValidationResult.UNVERIFIED


def test_deterministic_finding_is_always_valid():

    code = """
x = 10
"""

    finding = Finding(
        category="bug",
        severity=Severity.MEDIUM,
        confidence=0.9,
        line=2,
        message="Potential runtime exception",
        source="static_analyzer"
    )

    validator = FindingValidator()

    assert validator.validate(
        code,
        finding
    ) == ValidationResult.VALID