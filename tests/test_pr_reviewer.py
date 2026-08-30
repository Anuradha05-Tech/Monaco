from unittest.mock import MagicMock
from app.models.finding import Finding, Severity
from app.github.github_client import GitHubClient
from app.github.review_comment_formatter import ReviewCommentFormatter
from app.engine.pr_review_orchestrator import PRReviewOrchestrator
from app.engine.pr_reviewer import PRReviewer

def test_pr_reviewer_dry_run():
    # Setup mocks
    mock_orchestrator = MagicMock(spec=PRReviewOrchestrator)
    mock_client = MagicMock(spec=GitHubClient)
    formatter = ReviewCommentFormatter()
    
    finding = Finding(
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
    
    mock_orchestrator.review_pull_request.return_value = {
        "findings": [finding]
    }
    
    reviewer = PRReviewer(mock_orchestrator, mock_client, formatter)
    
    # Run in dry-run mode (default)
    result = reviewer.review_and_post(
        owner="test-owner",
        repo="test-repo",
        pr_number=42,
        local_repo_path="/fake/path",
        dry_run=True
    )
    
    # Assertions
    assert result["dry_run"] is True
    assert result["would_post_count"] == 1
    assert len(result["comments"]) == 1
    assert result["comments"][0]["path"] == "app.py"
    
    # Ensure post_review was NOT called
    mock_client.post_review.assert_not_called()
    mock_client.get_pull_request.assert_not_called()

def test_pr_reviewer_real_post():
    # Setup mocks
    mock_orchestrator = MagicMock(spec=PRReviewOrchestrator)
    mock_client = MagicMock(spec=GitHubClient)
    formatter = ReviewCommentFormatter()
    
    finding = Finding(
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
    
    mock_orchestrator.review_pull_request.return_value = {
        "findings": [finding]
    }
    mock_client.get_pull_request.return_value = {
        "head": {"sha": "abc123commitsha"}
    }
    mock_client.post_review.return_value = {
        "html_url": "https://github.com/test-owner/test-repo/pull/42#pullrequestreview-123"
    }
    
    reviewer = PRReviewer(mock_orchestrator, mock_client, formatter)
    
    # Run in non-dry-run mode
    result = reviewer.review_and_post(
        owner="test-owner",
        repo="test-repo",
        pr_number=42,
        local_repo_path="/fake/path",
        dry_run=False
    )
    
    # Assertions
    assert result["dry_run"] is False
    assert result["posted_count"] == 1
    assert result["review_url"] == "https://github.com/test-owner/test-repo/pull/42#pullrequestreview-123"
    
    # Ensure calls were made correctly
    mock_client.get_pull_request.assert_called_once_with("test-owner", "test-repo", 42)
    mock_client.post_review.assert_called_once_with(
        owner="test-owner",
        repo="test-repo",
        pr_number=42,
        commit_id="abc123commitsha",
        comments=[{
            "path": "app.py",
            "line": 10,
            "body": formatter.format_finding(finding),
            "side": "RIGHT"
        }],
        body="MONACO automated code review findings.",
        event="COMMENT"
    )

def test_pr_reviewer_zero_in_diff_findings():
    mock_orchestrator = MagicMock(spec=PRReviewOrchestrator)
    mock_client = MagicMock(spec=GitHubClient)
    formatter = ReviewCommentFormatter()
    
    finding = Finding(
        rule_id="SEC001",
        category="security",
        severity=Severity.HIGH,
        confidence=0.9,
        file="app.py",
        line=10,
        message="eval",
        source="static_analyzer",
        in_diff=False # Not in diff
    )
    
    mock_orchestrator.review_pull_request.return_value = {
        "findings": [finding]
    }
    
    reviewer = PRReviewer(mock_orchestrator, mock_client, formatter)
    
    # Test dry-run
    result_dry = reviewer.review_and_post(
        owner="test-owner",
        repo="test-repo",
        pr_number=42,
        local_repo_path="/fake/path",
        dry_run=True
    )
    assert result_dry["dry_run"] is True
    assert result_dry["would_post_count"] == 0
    mock_client.post_review.assert_not_called()
    
    # Test non-dry-run
    result_real = reviewer.review_and_post(
        owner="test-owner",
        repo="test-repo",
        pr_number=42,
        local_repo_path="/fake/path",
        dry_run=False
    )
    assert result_real["dry_run"] is False
    assert result_real["posted_count"] == 0
    assert result_real["review_url"] is None
    
    # Ensure post_review was never called
    mock_client.post_review.assert_not_called()
