from app.engine.deduplicator import FindingDeduplicator
from app.models.finding import Finding
from app.models.finding import Severity


def test_duplicate_eval_findings():

    static_finding = Finding(
        rule_id="SEC001",
        category="security",
        severity=Severity.HIGH,
        confidence=1.0,
        line=8,
        message="eval() can execute arbitrary code.",
        explanation="Use of eval can execute attacker-controlled code.",
        source="static_analyzer"
    )

    ai_finding = Finding(
        category="security",
        severity=Severity.CRITICAL,
        confidence=0.99,
        line=7,
        message="Use of eval on untrusted user input",
        explanation="eval can execute attacker-controlled code.",
        source="ai"
    )

    deduplicator = FindingDeduplicator()

    assert deduplicator.are_duplicates(
        static_finding,
        ai_finding
    )


def test_different_findings_are_not_duplicates():

    first = Finding(
        rule_id="SEC001",
        category="security",
        severity=Severity.HIGH,
        confidence=1.0,
        line=5,
        message="eval() can execute arbitrary code.",
        source="static_analyzer"
    )

    second = Finding(
        rule_id="SEC002",
        category="security",
        severity=Severity.HIGH,
        confidence=1.0,
        line=20,
        message="Possible hardcoded API key.",
        source="static_analyzer"
    )

    deduplicator = FindingDeduplicator()

    assert not deduplicator.are_duplicates(
        first,
        second
    )

def test_duplicate_findings_are_merged():

    static_finding = Finding(
        rule_id="SEC001",
        category="security",
        severity=Severity.HIGH,
        confidence=1.0,
        line=8,
        message="eval() can execute arbitrary code.",
        explanation="eval can execute attacker-controlled code.",
        suggestion="Avoid eval().",
        source="static_analyzer"
    )

    ai_finding = Finding(
        category="security",
        severity=Severity.CRITICAL,
        confidence=0.99,
        line=7,
        message="Use of eval on untrusted user input",
        explanation="User input can reach eval.",
        suggestion="Replace eval with a safe parser.",
        source="ai"
    )

    deduplicator = FindingDeduplicator()

    findings = deduplicator.deduplicate(
        [
            static_finding,
            ai_finding
        ]
    )

    assert len(findings) == 1

    merged = findings[0]

    assert merged.rule_id == "SEC001"

    assert merged.severity == Severity.CRITICAL

    assert merged.confidence == 1.0

    assert "static_analyzer" in merged.sources

    assert "ai" in merged.sources