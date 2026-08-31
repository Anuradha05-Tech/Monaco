import os
import sys
from unittest.mock import MagicMock, patch, mock_open
from app.engine.validator import ValidationResult

# Ensure project root is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.graph.state import ReviewState
from app.graph.nodes import ReviewGraphNodes
from app.graph.conditions import has_changed_python_files, check_validation_quality
from app.graph.pr_review_graph import build_graph
from app.models.finding import Finding, Severity

def run_test_a():
    print("=== TEST A: Early-exit Branch (no changed Python files) ===")

    # 1. Construct a mock context builder returning no Python files changed
    mock_context_builder = MagicMock()
    mock_context_builder.build_pr_review_context.return_value = {
        "pr_title": "Docs update only",
        "changed_files": ["README.md", "docs/setup.md"],
        "changed_lines": {}
    }
    
    # Mock ReviewEngine since we won't need it
    mock_review_engine = MagicMock()

    # 2. Build and compile the graph
    nodes = ReviewGraphNodes(
        pr_context_builder=mock_context_builder,
        review_engine=mock_review_engine
    )
    workflow = build_graph(nodes)
    compiled_app = workflow.compile()

    # 3. Invoke with hand-built initial state
    initial_state = {
        "owner": "test-owner",
        "repo": "test-repo",
        "pr_number": 123,
        "local_repo_path": "/fake/path",
        "pr_context": None,
        "all_findings": [],
        "deduplicated_findings": [],
        "validated_findings": [],
        "final_findings": [],
        "skipped_files": [],
        "needs_manual_review": False,
        "rejection_ratio": 0.0,
        "status_logs": []
    }

    final_state = compiled_app.invoke(initial_state)

    # 4. Print results
    logs = final_state.get("status_logs", [])
    print(f"Executed Nodes: {logs}")

    # Check if any analysis/validate/rank nodes ran
    forbidden = ["analyze_files_node", "deduplicate_node", "validate_node", "rank_node"]
    any_forbidden = any(f in logs for f in forbidden)
    
    if not any_forbidden:
        print("SUCCESS: Graph correctly exited early and bypassed analysis nodes.")
    else:
        print(f"FAILED: Found forbidden nodes in logs: {[f for f in forbidden if f in logs]}")
    print("=" * 60 + "\n")


def run_test_b():
    print("=== TEST B: Manual Review Flag Branch (high validation rejection ratio) ===")

    # 1. Mock the PR context builder to return one changed Python file
    mock_context_builder = MagicMock()
    mock_context_builder.build_pr_review_context.return_value = {
        "pr_title": "Fix bug",
        "changed_files": ["app.py"],
        "changed_lines": {"app.py": [5, 10]}
    }
    
    # 2. Mock the components of ReviewEngine
    mock_review_engine = MagicMock()
    
    # Define our findings
    finding_valid = Finding(
        rule_id="SEC001",
        category="security",
        severity=Severity.HIGH,
        line=5,
        message="eval call",
        source="static_analyzer"
    )
    finding_rejected_1 = Finding(
        rule_id="SEC002",
        category="security",
        severity=Severity.HIGH,
        line=10,
        message="suspect key",
        source="ai"
    )
    finding_rejected_2 = Finding(
        rule_id="SEC003",
        category="security",
        severity=Severity.HIGH,
        line=10,
        message="suspect cmd",
        source="ai"
    )
    finding_rejected_3 = Finding(
        rule_id="SEC004",
        category="security",
        severity=Severity.HIGH,
        line=10,
        message="suspect query",
        source="ai"
    )

    # Mock analyzers
    mock_review_engine.analyzer.analyze.return_value = {"findings": [finding_valid]}
    mock_review_engine.data_flow_analyzer.analyze.return_value = []
    
    mock_ai_review = MagicMock()
    mock_ai_review.findings = [finding_rejected_1, finding_rejected_2, finding_rejected_3]
    mock_review_engine.llm.review_code.return_value = mock_ai_review

    # Mock deduplicator to return all of them
    mock_review_engine.deduplicator.deduplicate.return_value = [
        finding_valid,
        finding_rejected_1,
        finding_rejected_2,
        finding_rejected_3
    ]

    # Mock validator so that 1 accepts, 3 reject -> 75% rejection ratio (> 0.5)
    def mock_validate(code, finding):
        if finding.rule_id == "SEC001":
            return ValidationResult.VALID
        return ValidationResult.INVALID
    
    mock_review_engine.validator.validate.side_effect = mock_validate

    # Mock ranker to return whatever survives validation
    mock_review_engine.ranker.rank.side_effect = lambda findings: findings

    # 3. Build and compile the graph
    nodes = ReviewGraphNodes(
        pr_context_builder=mock_context_builder,
        review_engine=mock_review_engine
    )
    workflow = build_graph(nodes)
    compiled_app = workflow.compile()

    # 4. Invoke the compiled graph with initial state
    initial_state = {
        "owner": "test-owner",
        "repo": "test-repo",
        "pr_number": 123,
        "local_repo_path": "/fake/path",
        "pr_context": None,
        "all_findings": [],
        "deduplicated_findings": [],
        "validated_findings": [],
        "final_findings": [],
        "skipped_files": [],
        "needs_manual_review": False,
        "rejection_ratio": 0.0,
        "status_logs": []
    }

    # Patch filesystem calls so analyze_files and validate can read the "file"
    with patch("os.path.exists", return_value=True), \
         patch("os.path.isdir", return_value=False), \
         patch("builtins.open", mock_open(read_data="import eval\nAPI_KEY=123")):
         
        final_state = compiled_app.invoke(initial_state)

    # 5. Print and Assert
    logs = final_state.get("status_logs", [])
    print(f"Executed Nodes:              {logs}")
    print(f"Final Rejection Ratio:       {final_state.get('rejection_ratio', 0.0):.2%}")
    print(f"Final Needs Manual Review:   {final_state.get('needs_manual_review')}")
    print(f"Final Findings Count:        {len(final_state.get('final_findings', []))}")
    
    # Assertions
    assert "flag_for_manual_review_node" in logs, "flag_for_manual_review_node did not execute"
    assert final_state.get("needs_manual_review") is True, "needs_manual_review is not True"
    assert len(final_state.get("final_findings", [])) == 1, "Expected 1 finding to survive validation"
    assert final_state.get("final_findings")[0].rule_id == "SEC001", "Wrong finding survived validation"

    print("SUCCESS: High rejection ratio correctly triggered flag_for_manual_review_node and preserved valid findings.")
    print("=" * 60)

if __name__ == "__main__":
    run_test_a()
    run_test_b()

