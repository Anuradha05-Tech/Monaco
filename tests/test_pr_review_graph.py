import os
from unittest.mock import MagicMock, patch, mock_open
from app.graph.pr_review_graph import run_pr_review
from app.github.pr_context_builder import PRContextBuilder
from app.engine.review_engine import ReviewEngine
from app.models.finding import Finding, Severity
from app.engine.validator import ValidationResult

def test_graph_short_circuits_with_no_py_files():
    # Setup mocks
    mock_context_builder = MagicMock()
    mock_review_engine = MagicMock()

    # PR does not contain any Python files
    mock_context_builder.build_pr_review_context.return_value = {
        "pr_title": "Update README only",
        "changed_files": ["README.md", "docs/index.html"],
        "changed_lines": {}
    }

    final_state = run_pr_review(
        owner="test-owner",
        repo="test-repo",
        pr_number=42,
        local_repo_path="/fake/path",
        pr_context_builder=mock_context_builder,
        review_engine=mock_review_engine
    )

    # Assertions
    logs = final_state["status_logs"]
    assert "fetch_pr_context_node" in logs
    assert "security_agent_node" not in logs
    assert "quality_agent_node" not in logs
    assert "performance_agent_node" not in logs
    assert "merge_agent_findings_node" not in logs
    assert "deduplicate_node" not in logs

    # Verify that no analyzers were called
    mock_review_engine.analyzer.analyze.assert_not_called()
    mock_review_engine.data_flow_analyzer.analyze.assert_not_called()
    mock_review_engine.llm.review_code.assert_not_called()

def test_graph_high_rejection_rate_flags_review():
    mock_context_builder = MagicMock()
    mock_review_engine = MagicMock()

    mock_context_builder.build_pr_review_context.return_value = {
        "pr_title": "Fix bug",
        "changed_files": ["app.py"],
        "changed_lines": {"app.py": [5]}
    }

    # Setup findings
    finding1 = Finding(rule_id="SEC001", category="security", severity=Severity.HIGH, line=5, message="eval", source="static_analyzer")
    finding2 = Finding(rule_id="SEC002", category="security", severity=Severity.HIGH, line=5, message="secret", source="static_analyzer")
    
    # 1. Mock analyzers
    mock_review_engine.analyzer.analyze.return_value = {"findings": [finding1]}
    mock_review_engine.data_flow_analyzer.analyze.return_value = []
    mock_ai_review = MagicMock()
    mock_ai_review.findings = [finding2]
    mock_review_engine.llm.review_code.return_value = mock_ai_review

    # 2. Mock deduplication
    mock_review_engine.deduplicator.deduplicate.return_value = [finding1, finding2]

    # 3. Mock validator to reject both (rejection_ratio = 1.0 > 0.5)
    mock_review_engine.validator.validate.return_value = ValidationResult.INVALID

    # 4. Mock ranker
    mock_review_engine.ranker.rank.return_value = []

    with patch("os.path.exists", return_value=True), \
         patch("os.path.isdir", return_value=False), \
         patch("builtins.open", mock_open(read_data="import eval")):

        final_state = run_pr_review(
            owner="test-owner",
            repo="test-repo",
            pr_number=42,
            local_repo_path="/fake/path",
            pr_context_builder=mock_context_builder,
            review_engine=mock_review_engine
        )

    # Assertions
    logs = final_state["status_logs"]
    assert "fetch_pr_context_node" in logs
    assert "security_agent_node" in logs
    assert "quality_agent_node" in logs
    assert "performance_agent_node" in logs
    assert "merge_agent_findings_node" in logs
    assert "deduplicate_node" in logs
    assert "validate_node" in logs
    assert "flag_for_manual_review_node" in logs
    assert "rank_node" in logs

    assert final_state["needs_manual_review"] is True
    assert final_state["rejection_ratio"] == 1.0

def test_graph_normal_run_succeeds_without_flagging():
    mock_context_builder = MagicMock()
    mock_review_engine = MagicMock()

    mock_context_builder.build_pr_review_context.return_value = {
        "pr_title": "Fix bug",
        "changed_files": ["app.py"],
        "changed_lines": {"app.py": [5]}
    }

    # Setup findings
    finding1 = Finding(rule_id="SEC001", category="security", severity=Severity.HIGH, line=5, message="eval", source="static_analyzer")
    
    mock_review_engine.analyzer.analyze.return_value = {"findings": [finding1]}
    mock_review_engine.data_flow_analyzer.analyze.return_value = []
    mock_ai_review = MagicMock()
    mock_ai_review.findings = []
    mock_review_engine.llm.review_code.return_value = mock_ai_review

    mock_review_engine.deduplicator.deduplicate.return_value = [finding1]

    # Mock validator to accept finding (rejection_ratio = 0.0 <= 0.5)
    mock_review_engine.validator.validate.return_value = ValidationResult.VALID

    mock_review_engine.ranker.rank.return_value = [finding1]

    with patch("os.path.exists", return_value=True), \
         patch("os.path.isdir", return_value=False), \
         patch("builtins.open", mock_open(read_data="import eval")):

        final_state = run_pr_review(
            owner="test-owner",
            repo="test-repo",
            pr_number=42,
            local_repo_path="/fake/path",
            pr_context_builder=mock_context_builder,
            review_engine=mock_review_engine
        )

    # Assertions
    logs = final_state["status_logs"]
    assert "fetch_pr_context_node" in logs
    assert "security_agent_node" in logs
    assert "quality_agent_node" in logs
    assert "performance_agent_node" in logs
    assert "merge_agent_findings_node" in logs
    assert "deduplicate_node" in logs
    assert "validate_node" in logs
    assert "flag_for_manual_review_node" not in logs
    assert "rank_node" in logs

    assert final_state["needs_manual_review"] is False
    assert final_state["rejection_ratio"] == 0.0
    assert len(final_state["final_findings"]) == 1
    assert final_state["final_findings"][0].rule_id == "SEC001"
