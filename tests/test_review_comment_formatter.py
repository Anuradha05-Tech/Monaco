from app.models.finding import Finding, Severity
from app.github.review_comment_formatter import ReviewCommentFormatter

def test_format_finding_markdown_structure():
    formatter = ReviewCommentFormatter()
    finding = Finding(
        rule_id="SEC001",
        category="security",
        severity=Severity.HIGH,
        confidence=0.9,
        file="app.py",
        line=10,
        message="Use of eval() detected.",
        explanation="eval is dangerous because it executes arbitrary code.",
        suggestion="Avoid eval.",
        source="static_analyzer"
    )
    
    formatted = formatter.format_finding(finding)
    
    assert "MONACO Code Review Finding" in formatted
    assert "security" in formatted
    assert "HIGH" in formatted
    assert "Use of eval() detected." in formatted
    assert "eval is dangerous" in formatted
    assert "Avoid eval." in formatted
    assert "static analysis" in formatted

def test_build_review_comments_filters_in_diff():
    formatter = ReviewCommentFormatter()
    
    in_diff_finding = Finding(
        rule_id="SEC001",
        category="security",
        severity=Severity.HIGH,
        confidence=0.9,
        file="app.py",
        line=10,
        message="eval",
        source="static_analyzer",
        in_diff=True
    )
    
    not_in_diff_finding = Finding(
        rule_id="SEC002",
        category="security",
        severity=Severity.MEDIUM,
        confidence=0.8,
        file="utils.py",
        line=20,
        message="secret",
        source="static_analyzer",
        in_diff=False
    )
    
    comments = formatter.build_review_comments([in_diff_finding, not_in_diff_finding])
    
    assert len(comments) == 1
    assert comments[0]["path"] == "app.py"
    assert comments[0]["line"] == 10
    assert "eval" in comments[0]["body"]
    assert comments[0]["side"] == "RIGHT"

def test_multiple_findings_same_file():
    formatter = ReviewCommentFormatter()
    
    finding1 = Finding(
        rule_id="SEC001",
        category="security",
        severity=Severity.HIGH,
        confidence=0.9,
        file="app.py",
        line=10,
        message="eval",
        source="static_analyzer",
        in_diff=True
    )
    
    finding2 = Finding(
        rule_id="SEC002",
        category="security",
        severity=Severity.HIGH,
        confidence=0.9,
        file="app.py",
        line=15,
        message="secret",
        source="static_analyzer",
        in_diff=True
    )
    
    comments = formatter.build_review_comments([finding1, finding2])
    
    assert len(comments) == 2
    assert comments[0]["path"] == "app.py"
    assert comments[0]["line"] == 10
    assert comments[1]["path"] == "app.py"
    assert comments[1]["line"] == 15
