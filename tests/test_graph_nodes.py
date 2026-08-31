import os
from unittest.mock import MagicMock, patch, mock_open
from app.graph.nodes import ReviewGraphNodes
from app.graph.state import ReviewState
from app.github.pr_context_builder import PRContextBuilder
from app.engine.review_engine import ReviewEngine
from app.models.finding import Finding, Severity
from app.engine.validator import ValidationResult

def test_fetch_pr_context_node():
    mock_context_builder = MagicMock()
    mock_review_engine = MagicMock()
    
    mock_context_builder.build_pr_review_context.return_value = {
        "pr_title": "Fake PR",
        "changed_files": ["app.py"]
    }
    
    nodes = ReviewGraphNodes(mock_context_builder, mock_review_engine)
    
    state: ReviewState = {
        "owner": "owner",
        "repo": "repo",
        "pr_number": 1,
        "local_repo_path": "/fake",
        "pr_context": None,
        "status_logs": []
    }
    
    res = nodes.fetch_pr_context_node(state)
    assert res["pr_context"]["pr_title"] == "Fake PR"
    assert "fetch_pr_context_node" in res["status_logs"]

def test_security_agent_node():
    mock_context_builder = MagicMock()
    mock_review_engine = MagicMock()
    
    # Mock the individual engines inside review_engine
    mock_review_engine.analyzer.analyze.return_value = {
        "findings": [Finding(rule_id="SEC001", category="security", severity=Severity.HIGH, line=5, message="eval", source="static_analyzer")]
    }
    mock_review_engine.data_flow_analyzer.analyze.return_value = []
    mock_ai_review = MagicMock()
    mock_ai_review.findings = [Finding(rule_id=None, category="security", severity=Severity.MEDIUM, line=5, message="ai message", source="ai")]
    mock_review_engine.llm.review_code.return_value = mock_ai_review
    
    nodes = ReviewGraphNodes(mock_context_builder, mock_review_engine)
    
    state: ReviewState = {
        "local_repo_path": "/fake",
        "pr_context": {
            "changed_files": ["app.py"],
            "changed_lines": {"app.py": [5]}
        },
        "status_logs": []
    }
    
    with patch("os.path.exists", return_value=True), \
         patch("os.path.isdir", return_value=False), \
         patch("builtins.open", mock_open(read_data="import eval")):
         
        res = nodes.security_agent_node(state)
        
    assert len(res["security_findings"]) == 2
    assert res["security_findings"][0].in_diff is True
    assert res["security_findings"][0].file == "app.py"
    assert res["security_findings"][0].category == "security"
    assert "security_agent_node" in res["status_logs"]

def test_quality_agent_node():
    mock_context_builder = MagicMock()
    mock_review_engine = MagicMock()
    
    nodes = ReviewGraphNodes(mock_context_builder, mock_review_engine)
    
    state: ReviewState = {
        "local_repo_path": "/fake",
        "pr_context": {
            "changed_files": ["app.py"],
            "changed_lines": {"app.py": [3]}
        },
        "status_logs": []
    }
    
    # Trigger bare except (QUAL004) at line 3
    code = "try:\n    x = 1\nexcept:\n    pass"
    with patch("os.path.exists", return_value=True), \
         patch("os.path.isdir", return_value=False), \
         patch("builtins.open", mock_open(read_data=code)):
         
        res = nodes.quality_agent_node(state)
        
    assert len(res["quality_findings"]) == 1
    assert res["quality_findings"][0].rule_id == "QUAL004"
    assert res["quality_findings"][0].in_diff is True
    assert "quality_agent_node" in res["status_logs"]

def test_performance_agent_node():
    mock_context_builder = MagicMock()
    mock_review_engine = MagicMock()
    
    nodes = ReviewGraphNodes(mock_context_builder, mock_review_engine)
    
    state: ReviewState = {
        "local_repo_path": "/fake",
        "pr_context": {
            "changed_files": ["app.py"],
            "changed_lines": {"app.py": [2]}
        },
        "status_logs": []
    }
    
    # Trigger unnecessary list instantiation (PERF002) at line 2
    code = "def f():\n    x = sum([i for i in range(5)])"
    with patch("os.path.exists", return_value=True), \
         patch("os.path.isdir", return_value=False), \
         patch("builtins.open", mock_open(read_data=code)):
         
        res = nodes.performance_agent_node(state)
        
    assert len(res["performance_findings"]) == 1
    assert res["performance_findings"][0].rule_id == "PERF002"
    assert "performance_agent_node" in res["status_logs"]

def test_merge_agent_findings_node():
    mock_context_builder = MagicMock()
    mock_review_engine = MagicMock()
    
    nodes = ReviewGraphNodes(mock_context_builder, mock_review_engine)
    
    f1 = Finding(rule_id="SEC001", category="security", severity=Severity.HIGH, line=5, message="eval", source="static_analyzer")
    f2 = Finding(rule_id="QUAL001", category="quality", severity=Severity.MEDIUM, line=10, message="long", source="quality_agent")
    f3 = Finding(rule_id="PERF001", category="performance", severity=Severity.LOW, line=15, message="concat", source="performance_agent")
    
    state: ReviewState = {
        "security_findings": [f1],
        "quality_findings": [f2],
        "performance_findings": [f3],
        "status_logs": []
    }
    
    res = nodes.merge_agent_findings_node(state)
    assert len(res["all_findings"]) == 3
    assert f1 in res["all_findings"]
    assert f2 in res["all_findings"]
    assert f3 in res["all_findings"]
    assert "merge_agent_findings_node" in res["status_logs"]

def test_deduplicate_node():
    mock_context_builder = MagicMock()
    mock_review_engine = MagicMock()
    
    finding = Finding(rule_id="SEC001", category="security", severity=Severity.HIGH, line=5, message="eval", source="static_analyzer")
    mock_review_engine.deduplicator.deduplicate.return_value = [finding]
    
    nodes = ReviewGraphNodes(mock_context_builder, mock_review_engine)
    
    state: ReviewState = {
        "all_findings": [finding, finding],
        "status_logs": []
    }
    
    res = nodes.deduplicate_node(state)
    assert len(res["deduplicated_findings"]) == 1
    assert "deduplicate_node" in res["status_logs"]

def test_validate_node():
    mock_context_builder = MagicMock()
    mock_review_engine = MagicMock()
    
    finding1 = Finding(rule_id="SEC001", category="security", severity=Severity.HIGH, line=5, message="eval", source="static_analyzer")
    finding1.file = "app.py"
    finding2 = Finding(rule_id="SEC002", category="security", severity=Severity.HIGH, line=10, message="secret", source="static_analyzer")
    finding2.file = "app.py"
    
    # Mock validator behavior
    # finding1: valid, finding2: invalid
    mock_review_engine.validator.validate.side_effect = lambda code, finding: (
        ValidationResult.VALID if finding.rule_id == "SEC001" else ValidationResult.INVALID
    )
    
    nodes = ReviewGraphNodes(mock_context_builder, mock_review_engine)
    
    state: ReviewState = {
        "local_repo_path": "/fake",
        "deduplicated_findings": [finding1, finding2],
        "status_logs": []
    }
    
    with patch("builtins.open", mock_open(read_data="import eval\nAPI_KEY=123")):
        res = nodes.validate_node(state)
        
    assert len(res["validated_findings"]) == 1
    assert res["validated_findings"][0].rule_id == "SEC001"
    # 1 rejected out of 2 checked = 0.5 ratio
    assert res["rejection_ratio"] == 0.5
    assert "validate_node" in res["status_logs"]

def test_rank_node():
    mock_context_builder = MagicMock()
    mock_review_engine = MagicMock()
    
    finding = Finding(rule_id="SEC001", category="security", severity=Severity.HIGH, line=5, message="eval", source="static_analyzer")
    mock_review_engine.ranker.rank.return_value = [finding]
    
    nodes = ReviewGraphNodes(mock_context_builder, mock_review_engine)
    
    state: ReviewState = {
        "validated_findings": [finding],
        "status_logs": []
    }
    
    res = nodes.rank_node(state)
    assert len(res["final_findings"]) == 1
    assert "rank_node" in res["status_logs"]

def test_flag_for_manual_review_node():
    mock_context_builder = MagicMock()
    mock_review_engine = MagicMock()
    
    nodes = ReviewGraphNodes(mock_context_builder, mock_review_engine)
    
    state: ReviewState = {
        "rejection_ratio": 0.6,
        "status_logs": []
    }
    
    res = nodes.flag_for_manual_review_node(state)
    assert res["needs_manual_review"] is True
    assert "flag_for_manual_review_node" in res["status_logs"]
