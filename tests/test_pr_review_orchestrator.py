import os
import pytest
from unittest.mock import MagicMock
from app.engine.pr_review_orchestrator import PRReviewOrchestrator
from app.models.finding import Finding, Severity

# Dummy/Mock implementations for dependency graph and context builders
class MockPRContextBuilder:
    def __init__(self, context_dict):
        self.context_dict = context_dict
        
    def build_pr_review_context(self, owner, repo, pr_number, local_repo_path):
        return self.context_dict

def test_pr_review_orchestrator_success(tmp_path):
    # 1. Create temporary files representing local repository files
    file_a = tmp_path / "file_a.py"
    file_b = tmp_path / "file_b.py"
    
    file_a.write_text("file_a_content")
    file_b.write_text("file_b_content")
    
    # 2. Define the mock context returned by PRContextBuilder
    # changed_files has file_a.py, file_b.py, and a missing file_c.py
    mock_context = {
        "pr_title": "Implement feature X",
        "pr_number": 42,
        "changed_files": ["file_a.py", "file_b.py", "file_c.py"],
        "changed_lines": {
            "file_a.py": [10],       # line 10 is changed in file_a
            "file_b.py": [30],       # line 30 is changed in file_b
            "file_c.py": []
        },
        "related_files": {
            "file_a.py": ["helper.py"],
            "file_b.py": []
        }
    }
    
    context_builder = MockPRContextBuilder(mock_context)
    
    # 3. Create mock findings to return from ReviewEngine for each file content
    def mock_review(code):
        if "file_a_content" in code:
            return [
                # Line 10 is in changed_lines -> should be tagged with in_diff=True
                Finding(category="Security", severity=Severity.HIGH, line=10, message="A1"),
                # Line 20 is NOT in changed_lines -> should be tagged with in_diff=False
                Finding(category="Quality", severity=Severity.LOW, line=20, message="A2")
            ]
        elif "file_b_content" in code:
            return [
                # Line 30 is in changed_lines -> should be tagged with in_diff=True
                Finding(category="Security", severity=Severity.CRITICAL, line=30, message="B1")
            ]
        return []

    # 4. Mock ReviewEngine, Deduplicator, and Ranker
    mock_deduplicator = MagicMock()
    mock_deduplicator.deduplicate.side_effect = lambda x: x
    
    mock_ranker = MagicMock()
    mock_ranker.rank.side_effect = lambda x: x
    
    mock_engine = MagicMock()
    mock_engine.review.side_effect = mock_review
    mock_engine.deduplicator = mock_deduplicator
    mock_engine.ranker = mock_ranker
    
    # 5. Instantiate orchestrator and run review
    orchestrator = PRReviewOrchestrator(
        pr_context_builder=context_builder,
        review_engine=mock_engine
    )
    
    result = orchestrator.review_pull_request(
        owner="owner-name",
        repo="repo-name",
        pr_number=42,
        local_repo_path=str(tmp_path)
    )
    
    # 6. Assert metadata
    assert result["pr_title"] == "Implement feature X"
    assert result["pr_number"] == 42
    assert result["changed_files"] == ["file_a.py", "file_b.py", "file_c.py"]
    
    # Assert missing file is recorded in skipped_files and didn't crash the orchestrator
    assert result["skipped_files"] == ["file_c.py"]
    
    # Assert findings summary counts
    assert result["total_findings"] == 3
    assert result["findings_in_diff"] == 2
    
    findings = result["findings"]
    assert len(findings) == 3
    
    # Assert finding A1: in changed lines
    a1 = next(f for f in findings if f.message == "A1")
    assert a1.file == "file_a.py"
    assert a1.in_diff is True
    
    # Assert finding A2: NOT in changed lines
    a2 = next(f for f in findings if f.message == "A2")
    assert a2.file == "file_a.py"
    assert a2.in_diff is False
    
    # Assert finding B1: in changed lines
    b1 = next(f for f in findings if f.message == "B1")
    assert b1.file == "file_b.py"
    assert b1.in_diff is True
    
    # Assert Deduplicator and Ranker were invoked on the combined list (cross-file)
    mock_deduplicator.deduplicate.assert_called_once()
    called_list = mock_deduplicator.deduplicate.call_args[0][0]
    assert len(called_list) == 3
    assert {f.message for f in called_list} == {"A1", "A2", "B1"}
    
    mock_ranker.rank.assert_called_once()
