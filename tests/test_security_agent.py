from unittest.mock import MagicMock
from app.agents.security_agent import SecurityAgent
from app.models.finding import Finding, Severity

def test_security_agent_retains_security_findings():
    mock_review_engine = MagicMock()
    
    sec_static = Finding(
        rule_id="SEC001",
        category="security",
        severity=Severity.HIGH,
        confidence=1.0,
        line=5,
        message="Dangerous eval usage",
        source="static_analyzer"
    )
    sec_flow = Finding(
        rule_id="FLOW001",
        category="security",
        severity=Severity.CRITICAL,
        confidence=1.0,
        line=10,
        message="Taint flows into eval",
        source="data_flow"
    )
    sec_ai = Finding(
        rule_id=None,
        category="security",
        severity=Severity.HIGH,
        confidence=0.9,
        line=15,
        message="Hardcoded credentials found",
        source="ai"
    )
    
    mock_review_engine.analyzer.analyze.return_value = {"findings": [sec_static]}
    mock_review_engine.data_flow_analyzer.analyze.return_value = [sec_flow]
    
    mock_ai_review = MagicMock()
    mock_ai_review.findings = [sec_ai]
    mock_review_engine.llm.review_code.return_value = mock_ai_review
    
    agent = SecurityAgent(mock_review_engine)
    findings = agent.analyze("app.py", "dummy code")
    
    assert len(findings) == 3
    for f in findings:
        assert f.category == "security"
        assert f.file == "app.py"


def test_security_agent_excludes_static_quality_and_complexity():
    mock_review_engine = MagicMock()
    
    qual_static = Finding(
        rule_id="QUAL010",
        category="code_quality",
        severity=Severity.MEDIUM,
        confidence=1.0,
        line=5,
        message="Function too long",
        source="static_analyzer"
    )
    comp_static = Finding(
        rule_id="COMP001",
        category="complexity",
        severity=Severity.MEDIUM,
        confidence=1.0,
        line=10,
        message="Function has high complexity score",
        source="static_analyzer"
    )
    
    mock_review_engine.analyzer.analyze.return_value = {"findings": [qual_static, comp_static]}
    mock_review_engine.data_flow_analyzer.analyze.return_value = []
    mock_review_engine.llm = None
    
    agent = SecurityAgent(mock_review_engine)
    findings = agent.analyze("app.py", "dummy code")
    
    assert len(findings) == 0


def test_security_agent_excludes_ai_quality_with_keywords():
    mock_review_engine = MagicMock()
    
    ai_quality = Finding(
        rule_id=None,
        category="security",
        severity=Severity.MEDIUM,
        confidence=0.8,
        line=29,
        message="Bare except clause catches all exceptions",
        source="ai"
    )
    
    mock_review_engine.analyzer.analyze.return_value = {"findings": []}
    mock_review_engine.data_flow_analyzer.analyze.return_value = []
    
    mock_ai_review = MagicMock()
    mock_ai_review.findings = [ai_quality]
    mock_review_engine.llm.review_code.return_value = mock_ai_review
    
    agent = SecurityAgent(mock_review_engine)
    findings = agent.analyze("app.py", "dummy code")
    
    assert len(findings) == 0


def test_security_agent_limitation_different_phrasing():
    mock_review_engine = MagicMock()
    
    # This finding describes a complexity concern but uses a custom phrasing not matched by the keyword list
    ai_complex_phrased = Finding(
        rule_id=None,
        category="security",
        severity=Severity.MEDIUM,
        confidence=0.8,
        line=12,
        message="this function has grown too complex, consider refactoring",
        source="ai"
    )
    
    mock_review_engine.analyzer.analyze.return_value = {"findings": []}
    mock_review_engine.data_flow_analyzer.analyze.return_value = []
    
    mock_ai_review = MagicMock()
    mock_ai_review.findings = [ai_complex_phrased]
    mock_review_engine.llm.review_code.return_value = mock_ai_review
    
    agent = SecurityAgent(mock_review_engine)
    findings = agent.analyze("app.py", "dummy code")
    
    # Note: With the introduction of security-focused prompt scoping, the AI should
    # avoid generating quality/complexity findings altogether in real-world scenarios.
    # However, if the AI drifts and returns a finding categorized as "security" but
    # phrased differently without matching our exact keyword list, the keyword filter
    # will fail to exclude it. This test serves to document this residual known limitation
    # of the keyword-based secondary safety net.
    assert len(findings) == 1
    assert findings[0].message == "this function has grown too complex, consider refactoring"

