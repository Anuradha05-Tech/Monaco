from app.engine.ranker import FindingRanker
from app.models.finding import Finding, Severity


def test_critical_finding_ranks_above_low():

    critical = Finding(
        category="security",
        severity=Severity.CRITICAL,
        confidence=1.0,
        message="Critical security issue",
        source="static_analyzer",
        sources=["static_analyzer"]
    )

    low = Finding(
        category="bug",
        severity=Severity.LOW,
        confidence=1.0,
        message="Low priority issue",
        source="ai",
        sources=["ai"]
    )

    ranker = FindingRanker()

    ranked = ranker.rank(
        [low, critical]
    )

    assert ranked[0] == critical
    assert ranked[1] == low


def test_multiple_sources_increase_priority():

    single_source = Finding(
        category="security",
        severity=Severity.HIGH,
        confidence=1.0,
        message="Security issue",
        source="ai",
        sources=["ai"]
    )

    multiple_sources = Finding(
        category="security",
        severity=Severity.HIGH,
        confidence=1.0,
        message="Confirmed security issue",
        source="ai",
        sources=[
            "ai",
            "static_analyzer"
        ]
    )

    ranker = FindingRanker()

    single_score = ranker.calculate_score(
        single_source
    )

    multiple_score = ranker.calculate_score(
        multiple_sources
    )

    assert multiple_score > single_score