import pytest
from app.models.finding import Finding, Severity
from app.engine.deduplicator import FindingDeduplicator

def test_ai_structured_rule_merging_zero_keywords():
    """
    Tests that an AI finding with a structured category tag (e.g., rule_category="hardcoded_secret")
    correctly merges with its equivalent static finding (SEC002) even if the message texts
    share zero keywords.
    """
    deduplicator = FindingDeduplicator()

    # Static analyzer finding (SEC002)
    static_finding = Finding(
        rule_id="SEC002",
        category="security",
        severity=Severity.HIGH,
        confidence=0.85,
        file="app.py",
        line=7,
        message="Alpha beta gamma delta.",
        explanation="No matching keywords here.",
        suggestion="None.",
        source="static_analyzer"
    )

    # AI review finding (AI_HARDCODED_SECRET)
    ai_finding = Finding(
        rule_id="AI_HARDCODED_SECRET",
        rule_category="hardcoded_secret",
        category="security",
        severity=Severity.HIGH,
        confidence=0.9,
        file="app.py",
        line=7,
        message="Foo bar baz qux.",
        explanation="Totally different explanation text.",
        suggestion="None.",
        source="ai"
    )

    # They should be recognized as duplicates because they have compatible rule IDs and are on the same line
    assert deduplicator.are_duplicates(static_finding, ai_finding) is True

    # Check deduplicate() correctly merges them
    merged = deduplicator.deduplicate([static_finding, ai_finding])
    assert len(merged) == 1
    assert merged[0].rule_id == "SEC002"  # Keeps the static rule ID
    assert "ai" in merged[0].sources
    assert "static_analyzer" in merged[0].sources

def test_unicode_hyphen_fallback_merging():
    """
    Tests that the Unicode hyphen normalization handles cases like "Hard\u2011coded"
    vs "hardcoded" correctly during keyword-based fallback when rule IDs are not present/compatible.
    """
    deduplicator = FindingDeduplicator()

    # Static finding with rule_id = None to force keyword fallback
    static_finding = Finding(
        rule_id=None,
        category="security",
        severity=Severity.HIGH,
        confidence=0.8,
        file="app.py",
        line=7,
        message="This is a hardcoded value.",
        explanation="None",
        source="static_analyzer"
    )

    # AI finding with rule_id = None and Unicode non-breaking hyphen (U+2011) in message
    ai_finding = Finding(
        rule_id=None,
        category="security",
        severity=Severity.HIGH,
        confidence=0.9,
        file="app.py",
        line=7,
        message="Contains a Hard\u2011coded API key.",  # U+2011 non-breaking hyphen
        explanation="None",
        source="ai"
    )

    # The keyword fallback should successfully normalize and match "hardcoded" / "api key"
    assert deduplicator.are_duplicates(static_finding, ai_finding) is True

def test_ai_other_category_no_merge_zero_keywords():
    """
    Tests that an AI finding with rule_category="other" and sharing zero keywords
    with the static finding is NOT merged (treated as a novel/distinct finding).
    """
    deduplicator = FindingDeduplicator()

    static_finding = Finding(
        rule_id="SEC002",
        category="security",
        severity=Severity.HIGH,
        confidence=0.85,
        file="app.py",
        line=7,
        message="Possible hardcoded secret in variable.",
        explanation="Secrets stored in source code.",
        source="static_analyzer"
    )

    ai_finding = Finding(
        rule_id=None,
        rule_category="other",
        category="security",
        severity=Severity.HIGH,
        confidence=0.95,
        file="app.py",
        line=7,
        message="Unsafe deserialization of incoming requests.",
        explanation="This is a novel issue.",
        source="ai"
    )

    # Since they share no keywords and have no equivalent rule IDs, they should NOT be duplicates
    assert deduplicator.are_duplicates(static_finding, ai_finding) is False
