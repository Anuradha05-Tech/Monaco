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
    
    # Mock get_pull_request, get_existing_reviews, and comments for the check
    mock_client.get_pull_request.return_value = {
        "head": {"sha": "abc123commitsha"}
    }
    mock_client.get_existing_reviews.return_value = []
    mock_client.get_existing_review_comments.return_value = []
    
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
    mock_client.get_existing_reviews.return_value = []
    mock_client.get_existing_review_comments.return_value = []
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
    mock_client.get_existing_reviews.assert_called_once_with("test-owner", "test-repo", 42)
    mock_client.get_existing_review_comments.assert_called_once_with("test-owner", "test-repo", 42)
    
    expected_body = "MONACO automated code review findings.\n<!-- monaco-review:abc123commitsha -->"
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
        body=expected_body,
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
    mock_client.get_pull_request.return_value = {
        "head": {"sha": "abc123commitsha"}
    }
    mock_client.get_existing_reviews.return_value = []
    
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


def test_pr_reviewer_existing_review_found():
    # Setup mocks
    mock_orchestrator = MagicMock(spec=PRReviewOrchestrator)
    mock_client = MagicMock(spec=GitHubClient)
    formatter = ReviewCommentFormatter()
    
    mock_client.get_pull_request.return_value = {
        "head": {"sha": "abc123commitsha"}
    }
    
    # Existing review by MONACO for same commit is present
    mock_client.get_existing_reviews.return_value = [
        {
            "id": 1,
            "body": "Some comment\n<!-- monaco-review:abc123commitsha -->",
            "html_url": "https://github.com/existing-review-url",
            "commit_id": "abc123commitsha"
        }
    ]
    
    reviewer = PRReviewer(mock_orchestrator, mock_client, formatter)
    
    result = reviewer.review_and_post(
        owner="test-owner",
        repo="test-repo",
        pr_number=42,
        local_repo_path="/fake/path",
        dry_run=False
    )
    
    assert result.get("already_reviewed") is True
    assert result.get("existing_review_url") == "https://github.com/existing-review-url"
    assert result.get("posted_count") == 0
    
    # Ensure orchestrator and post_review were NOT called
    mock_orchestrator.review_pull_request.assert_not_called()
    mock_client.post_review.assert_not_called()


def test_pr_reviewer_older_commit_review_ignored():
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
        "head": {"sha": "newcommitsha"}
    }
    
    # Existing review by MONACO exists but for an OLDER commit ID
    mock_client.get_existing_reviews.return_value = [
        {
            "id": 1,
            "body": "Older review\n<!-- monaco-review:oldercommitsha -->",
            "html_url": "https://github.com/existing-review-url",
            "commit_id": "oldercommitsha"
        }
    ]
    mock_client.get_existing_review_comments.return_value = []
    mock_client.post_review.return_value = {
        "html_url": "https://github.com/new-review-url"
    }
    
    reviewer = PRReviewer(mock_orchestrator, mock_client, formatter)
    
    result = reviewer.review_and_post(
        owner="test-owner",
        repo="test-repo",
        pr_number=42,
        local_repo_path="/fake/path",
        dry_run=False
    )
    
    # It should not count as already reviewed and post a new review
    assert result.get("already_reviewed") is False
    assert result.get("posted_count") == 1
    assert result.get("review_url") == "https://github.com/new-review-url"
    
    mock_client.post_review.assert_called_once()


def test_pr_reviewer_other_user_review_ignored():
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
    
    # Existing review from someone else (no MONACO marker)
    mock_client.get_existing_reviews.return_value = [
        {
            "id": 1,
            "body": "This is a normal review by another user.",
            "html_url": "https://github.com/other-user-review-url",
            "commit_id": "abc123commitsha"
        }
    ]
    mock_client.get_existing_review_comments.return_value = []
    mock_client.post_review.return_value = {
        "html_url": "https://github.com/new-review-url"
    }
    
    reviewer = PRReviewer(mock_orchestrator, mock_client, formatter)
    
    result = reviewer.review_and_post(
        owner="test-owner",
        repo="test-repo",
        pr_number=42,
        local_repo_path="/fake/path",
        dry_run=False
    )
    
    assert result.get("already_reviewed") is False
    assert result.get("posted_count") == 1
    
    mock_client.post_review.assert_called_once()


def test_pr_reviewer_dry_run_with_existing_review():
    # Setup mocks
    mock_orchestrator = MagicMock(spec=PRReviewOrchestrator)
    mock_client = MagicMock(spec=GitHubClient)
    formatter = ReviewCommentFormatter()
    
    mock_client.get_pull_request.return_value = {
        "head": {"sha": "abc123commitsha"}
    }
    
    # Existing review by MONACO for same commit is present
    mock_client.get_existing_reviews.return_value = [
        {
            "id": 1,
            "body": "Some comment\n<!-- monaco-review:abc123commitsha -->",
            "html_url": "https://github.com/existing-review-url",
            "commit_id": "abc123commitsha"
        }
    ]
    
    reviewer = PRReviewer(mock_orchestrator, mock_client, formatter)
    
    # dry_run=True
    result = reviewer.review_and_post(
        owner="test-owner",
        repo="test-repo",
        pr_number=42,
        local_repo_path="/fake/path",
        dry_run=True
    )
    
    assert result.get("already_reviewed") is True
    assert result.get("existing_review_url") == "https://github.com/existing-review-url"
    assert result.get("posted_count") == 0
    
    # Ensure orchestrator and post_review were NOT called at all
    mock_orchestrator.review_pull_request.assert_not_called()
    mock_client.post_review.assert_not_called()


def test_pr_reviewer_deduplicates_exact_match():
    # Scenario: Same PR, same finding (file+line+rule_id) flagged in an earlier review,
    # new commit pushed with no fix -> finding is excluded. If it is the only finding,
    # post_review is not called at all.
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
        "head": {"sha": "newcommitsha"}
    }
    
    # No exact-commit review exists yet (so we don't early exit on commit check)
    mock_client.get_existing_reviews.return_value = []
    
    # But a comment matching this finding was already posted in a prior review
    mock_client.get_existing_review_comments.return_value = [
        {
            "id": 12,
            "body": "Some formatted comment body\n<!-- monaco-finding:app.py:10:SEC001 -->"
        }
    ]
    
    reviewer = PRReviewer(mock_orchestrator, mock_client, formatter)
    
    result = reviewer.review_and_post(
        owner="test-owner",
        repo="test-repo",
        pr_number=42,
        local_repo_path="/fake/path",
        dry_run=False
    )
    
    # Assertions
    assert result.get("already_reviewed") is False
    assert result.get("no_new_findings") is True
    assert result.get("posted_count") == 0
    assert result.get("total_findings_found") == 1
    
    # Ensure no POST review request was made because everything was filtered out
    mock_client.post_review.assert_not_called()


def test_pr_reviewer_deduplicates_subset_match():
    # Scenario: Genuinely new finding also exists -> only new one gets posted, old one excluded
    mock_orchestrator = MagicMock(spec=PRReviewOrchestrator)
    mock_client = MagicMock(spec=GitHubClient)
    formatter = ReviewCommentFormatter()
    
    old_finding = Finding(
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
    
    new_finding = Finding(
        rule_id="SEC002",
        category="security",
        severity=Severity.MEDIUM,
        confidence=0.8,
        file="utils.py",
        line=25,
        message="hardcoded API key",
        source="static_analyzer",
        in_diff=True
    )
    
    mock_orchestrator.review_pull_request.return_value = {
        "findings": [old_finding, new_finding]
    }
    mock_client.get_pull_request.return_value = {
        "head": {"sha": "newcommitsha"}
    }
    
    mock_client.get_existing_reviews.return_value = []
    
    # Prior comment exists for old_finding only
    mock_client.get_existing_review_comments.return_value = [
        {
            "id": 12,
            "body": "Some formatted comment body\n<!-- monaco-finding:app.py:10:SEC001 -->"
        }
    ]
    mock_client.post_review.return_value = {
        "html_url": "https://github.com/new-review-url"
    }
    
    reviewer = PRReviewer(mock_orchestrator, mock_client, formatter)
    
    result = reviewer.review_and_post(
        owner="test-owner",
        repo="test-repo",
        pr_number=42,
        local_repo_path="/fake/path",
        dry_run=False
    )
    
    # Assertions
    assert result.get("already_reviewed") is False
    assert result.get("posted_count") == 1
    assert result.get("total_findings_found") == 2
    assert result.get("review_url") == "https://github.com/new-review-url"
    
    # Ensure only the new finding is in the post_review call
    mock_client.post_review.assert_called_once()
    posted_comments = mock_client.post_review.call_args[1]["comments"]
    assert len(posted_comments) == 1
    assert posted_comments[0]["path"] == "utils.py"
    assert posted_comments[0]["line"] == 25


def test_pr_reviewer_deduplicates_different_rule_id():
    # Scenario: A finding with the same file+line but a DIFFERENT rule_id -> treated as new, gets posted
    mock_orchestrator = MagicMock(spec=PRReviewOrchestrator)
    mock_client = MagicMock(spec=GitHubClient)
    formatter = ReviewCommentFormatter()
    
    new_finding_diff_rule = Finding(
        rule_id="QUAL002",
        category="code_quality",
        severity=Severity.MEDIUM,
        confidence=0.9,
        file="app.py",
        line=10,
        message="complexity score high",
        source="static_analyzer",
        in_diff=True
    )
    
    mock_orchestrator.review_pull_request.return_value = {
        "findings": [new_finding_diff_rule]
    }
    mock_client.get_pull_request.return_value = {
        "head": {"sha": "newcommitsha"}
    }
    
    mock_client.get_existing_reviews.return_value = []
    
    # Prior comment exists on the same line but for a different rule_id (SEC001)
    mock_client.get_existing_review_comments.return_value = [
        {
            "id": 12,
            "body": "Some formatted comment body\n<!-- monaco-finding:app.py:10:SEC001 -->"
        }
    ]
    mock_client.post_review.return_value = {
        "html_url": "https://github.com/new-review-url"
    }
    
    reviewer = PRReviewer(mock_orchestrator, mock_client, formatter)
    
    result = reviewer.review_and_post(
        owner="test-owner",
        repo="test-repo",
        pr_number=42,
        local_repo_path="/fake/path",
        dry_run=False
    )
    
    # It should treat it as new and post it
    assert result.get("already_reviewed") is False
    assert result.get("posted_count") == 1
    assert result.get("total_findings_found") == 1
    
    mock_client.post_review.assert_called_once()
