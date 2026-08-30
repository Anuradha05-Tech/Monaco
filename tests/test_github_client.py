import os
import pytest
import responses
from app.github.github_client import (
    GitHubClient,
    GitHubAPIError,
    MissingGitHubTokenError
)

@pytest.fixture
def github_client(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake_token_12345")
    return GitHubClient()

def test_missing_github_token(monkeypatch):
    # Ensure GITHUB_TOKEN is not in the environment
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    # Mock load_dotenv in the client module so it doesn't load the real .env file
    monkeypatch.setattr("app.github.github_client.load_dotenv", lambda *args, **kwargs: None)
    
    with pytest.raises(MissingGitHubTokenError) as exc_info:
        GitHubClient()
    assert "GITHUB_TOKEN environment variable is not set" in str(exc_info.value)

@responses.activate
def test_get_pull_request_success(github_client):
    url = "https://api.github.com/repos/owner/repo/pulls/42"
    mock_payload = {
        "title": "Fix memory leak in engine",
        "number": 42,
        "state": "open",
        "base": {"ref": "main"},
        "head": {"ref": "feature/leak-fix"}
    }
    
    responses.add(
        responses.GET,
        url,
        json=mock_payload,
        status=200
    )
    
    pr = github_client.get_pull_request("owner", "repo", 42)
    assert pr["title"] == "Fix memory leak in engine"
    assert pr["number"] == 42
    assert pr["state"] == "open"

@responses.activate
def test_get_pr_files_pagination(github_client):
    page1_url = "https://api.github.com/repos/owner/repo/pulls/42/files"
    page2_url = "https://api.github.com/repos/owner/repo/pulls/42/files?page=2"
    
    responses.add(
        responses.GET,
        page1_url,
        json=[
            {"filename": "app/main.py", "status": "modified", "patch": "@@ -1,3 +1,4 @@\n..."}
        ],
        headers={"Link": f'<{page2_url}>; rel="next"'},
        status=200
    )
    responses.add(
        responses.GET,
        page2_url,
        json=[
            {"filename": "tests/test_main.py", "status": "added", "patch": "@@ -0,0 +1,5 @@\n..."}
        ],
        status=200
    )
    
    files = github_client.get_pr_files("owner", "repo", 42)
    assert len(files) == 2
    assert files[0]["filename"] == "app/main.py"
    assert files[0]["status"] == "modified"
    assert files[1]["filename"] == "tests/test_main.py"
    assert files[1]["status"] == "added"

@responses.activate
def test_github_api_404_not_found(github_client):
    url = "https://api.github.com/repos/owner/repo/pulls/42"
    responses.add(
        responses.GET,
        url,
        json={"message": "Not Found"},
        status=404
    )
    
    with pytest.raises(GitHubAPIError) as exc_info:
        github_client.get_pull_request("owner", "repo", 42)
    assert "Status 404" in str(exc_info.value)

@responses.activate
def test_github_api_401_unauthorized(github_client):
    url = "https://api.github.com/repos/owner/repo/pulls/42"
    responses.add(
        responses.GET,
        url,
        json={"message": "Bad credentials"},
        status=401
    )
    
    with pytest.raises(GitHubAPIError) as exc_info:
        github_client.get_pull_request("owner", "repo", 42)
    assert "Status 401" in str(exc_info.value)

@responses.activate
def test_rate_limit_exceeded(github_client):
    url = "https://api.github.com/repos/owner/repo/pulls/42"
    responses.add(
        responses.GET,
        url,
        json={"message": "API rate limit exceeded"},
        headers={
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1777777777"
        },
        status=403
    )
    
    with pytest.raises(GitHubAPIError) as exc_info:
        github_client.get_pull_request("owner", "repo", 42)
    assert "rate limit exceeded" in str(exc_info.value)
    assert "1777777777" in str(exc_info.value)
