from unittest.mock import MagicMock
from app.github.pr_context_builder import PRContextBuilder
from app.github.pr_diff_parser import PRDiffParser

class DummyGraphBuilder:
    """
    A dummy graph builder to return a static dependency graph for testing.
    """
    def build(self, repo_root: str) -> dict:
        return {
            "a.py": ["b.py"],
            "b.py": ["c.py"],
            "c.py": []
        }

def test_pr_context_builder_success():
    # 1. Mock GitHubClient to avoid network requests
    mock_client = MagicMock()
    mock_client.get_pull_request.return_value = {
        "title": "Refactor app structure",
        "number": 42,
        "state": "open"
    }
    
    mock_client.get_pr_files.return_value = [
        {
            "filename": "a.py",
            "status": "modified",
            "patch": "@@ -1,2 +1,3 @@\n import b\n+print('added line')\n"
        }
    ]
    
    # 2. Instantiate dependencies
    parser = PRDiffParser()
    graph_builder = DummyGraphBuilder()
    
    # 3. Instantiate PRContextBuilder
    builder = PRContextBuilder(
        github_client=mock_client,
        pr_diff_parser=parser,
        graph_builder=graph_builder
    )
    
    # 4. Build PR review context
    context = builder.build_pr_review_context(
        owner="test-owner",
        repo="test-repo",
        pr_number=42,
        local_repo_path="/dummy/path"
    )
    
    # 5. Assertions on output structure and values
    assert context["pr_title"] == "Refactor app structure"
    assert context["pr_number"] == 42
    assert context["changed_files"] == ["a.py"]
    assert context["changed_lines"] == {"a.py": [2]}
    assert context["related_files"] == {"a.py": ["b.py"]}
    
    # 6. Verify client interactions
    mock_client.get_pull_request.assert_called_once_with("test-owner", "test-repo", 42)
    mock_client.get_pr_files.assert_called_once_with("test-owner", "test-repo", 42)
