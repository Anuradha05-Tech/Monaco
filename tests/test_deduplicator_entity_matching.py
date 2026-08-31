import pytest
from app.models.finding import Finding, Severity
from app.engine.deduplicator import FindingDeduplicator

def test_different_named_secrets_do_not_merge():
    """
    Tests that two different hardcoded secrets on adjacent lines (e.g. API_KEY on line 7
    and SECRET_TOKEN on line 8) are NOT merged despite sharing category, rule_id (SEC002),
    and being within LINE_DISTANCE.
```
    API_KEY = "sk-secret-1"
    SECRET_TOKEN = "sk-secret-2"
```
    """
    deduplicator = FindingDeduplicator()

    # Static finding for API_KEY on line 7
    api_key_finding = Finding(
        rule_id="SEC002",
        category="security",
        severity=Severity.HIGH,
        confidence=0.85,
        file="app.py",
        line=7,
        variable_name="API_KEY",
        message="Possible hardcoded secret in variable 'API_KEY'.",
        source="static_analyzer"
    )

    # Static finding for SECRET_TOKEN on line 8
    secret_token_finding = Finding(
        rule_id="SEC002",
        category="security",
        severity=Severity.HIGH,
        confidence=0.85,
        file="app.py",
        line=8,
        variable_name="SECRET_TOKEN",
        message="Possible hardcoded secret in variable 'SECRET_TOKEN'.",
        source="static_analyzer"
    )

    # They should NOT be treated as duplicates because their variable names differ
    assert deduplicator.are_duplicates(api_key_finding, secret_token_finding) is False

    merged = deduplicator.deduplicate([api_key_finding, secret_token_finding])
    assert len(merged) == 2

def test_same_named_secret_merges_across_attribution_drift():
    """
    Tests that two findings about the SAME named secret (e.g. static analyzer flags it
    at line 7, AI flags the same variable but reports line 8 due to attribution drift)
    DO merge successfully.
    """
    deduplicator = FindingDeduplicator()

    static_finding = Finding(
        rule_id="SEC002",
        category="security",
        severity=Severity.HIGH,
        confidence=0.85,
        file="app.py",
        line=7,
        variable_name="API_KEY",
        message="Possible hardcoded secret in variable 'API_KEY'.",
        source="static_analyzer"
    )

    ai_finding = Finding(
        rule_id="AI_HARDCODED_SECRET",
        rule_category="hardcoded_secret",
        category="security",
        severity=Severity.HIGH,
        confidence=0.9,
        file="app.py",
        line=8,
        variable_name="API_KEY",
        message="Hardcoded API key exposed in source code",
        source="ai"
    )

    # They should merge because the variable names match and they are within LINE_DISTANCE
    assert deduplicator.are_duplicates(static_finding, ai_finding) is True

    merged = deduplicator.deduplicate([static_finding, ai_finding])
    assert len(merged) == 1
    assert merged[0].rule_id == "SEC002"
    assert merged[0].line == 7  # Keeps the static/primary line

def test_sec003_unaffected_by_entity_matching():
    """
    Tests that SEC003/eval-style rules (no named entity) still merge correctly
    via line-distance alone, unaffected by this change.
    """
    deduplicator = FindingDeduplicator()

    static_finding = Finding(
        rule_id="SEC003",
        category="security",
        severity=Severity.MEDIUM,
        confidence=0.8,
        file="app.py",
        line=5,
        message="Potentially dangerous subprocess.run() usage.",
        source="static_analyzer"
    )

    ai_finding = Finding(
        rule_id="AI_COMMAND_INJECTION",
        rule_category="command_injection",
        category="security",
        severity=Severity.HIGH,
        confidence=0.95,
        file="app.py",
        line=5,
        message="Command injection risk due to shell=True",
        source="ai"
    )

    # They have no variable_name, but should merge because they are compatible rules on the same line
    assert deduplicator.are_duplicates(static_finding, ai_finding) is True

    merged = deduplicator.deduplicate([static_finding, ai_finding])
    assert len(merged) == 1
    assert merged[0].rule_id == "SEC003"
