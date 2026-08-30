import os
import requests
from dotenv import load_dotenv

class MissingGitHubTokenError(Exception):
    """Raised when the GITHUB_TOKEN environment variable is not set."""
    pass

class GitHubAPIError(Exception):
    """Raised when a GitHub API request fails or encounters rate limits."""
    pass

class GitHubClient:
    """
    Client for interacting with the GitHub REST API using raw HTTP requests.
    """
    def __init__(self):
        # Load environment variables from .env if present
        load_dotenv()
        self.token = os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise MissingGitHubTokenError("GITHUB_TOKEN environment variable is not set.")
        
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Monaco-Code-Review-App"
        }

    def _check_response(self, response: requests.Response):
        """
        Validates the API response, handling rate limits and HTTP errors.
        """
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining is not None and remaining.strip() == "0":
            reset_time = response.headers.get("X-RateLimit-Reset", "unknown")
            raise GitHubAPIError(
                f"GitHub API rate limit exceeded. Rate limit resets at: {reset_time}. "
                f"Status: {response.status_code}. Response body: {response.text}"
            )

        if not (200 <= response.status_code < 300):
            raise GitHubAPIError(
                f"GitHub API error (Status {response.status_code}): {response.text}"
            )

    def get_pull_request(self, owner: str, repo: str, pr_number: int) -> dict:
        """
        Retrieves metadata for a pull request.
        
        Args:
            owner: The GitHub repository owner.
            repo: The GitHub repository name.
            pr_number: The pull request number.
            
        Returns:
            A dictionary containing the parsed pull request details.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        try:
            response = requests.get(url, headers=self.headers)
        except Exception as e:
            raise GitHubAPIError(f"Network request to GitHub failed: {e}")
        
        self._check_response(response)
        
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise GitHubAPIError(f"Expected a dict from PR response, got: {type(data)}")
            return data
        except (ValueError, TypeError) as e:
            raise GitHubAPIError(
                f"Failed to parse JSON response from GitHub API: {e}. Raw response: {response.text}"
            )

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list[dict]:
        """
        Retrieves the list of changed files in a pull request, handling pagination.
        
        Args:
            owner: The GitHub repository owner.
            repo: The GitHub repository name.
            pr_number: The pull request number.
            
        Returns:
            A list of dicts, where each dict has:
            - "filename": The path of the file.
            - "status": The file status (added, modified, removed, etc.).
            - "patch": The unified diff patch text (or None/missing).
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        files = []
        
        while url:
            try:
                response = requests.get(url, headers=self.headers)
            except Exception as e:
                raise GitHubAPIError(f"Network request to GitHub failed: {e}")
            
            self._check_response(response)
            
            try:
                page_files = response.json()
                if not isinstance(page_files, list):
                    raise GitHubAPIError(f"Expected a list of files, but got: {type(page_files)}")
            except (ValueError, TypeError) as e:
                raise GitHubAPIError(
                    f"Failed to parse JSON response from GitHub API: {e}. Raw response: {response.text}"
                )
            
            for f in page_files:
                if not isinstance(f, dict):
                    raise GitHubAPIError(f"Expected file entry to be a dict, got: {type(f)}")
                
                files.append({
                    "filename": f.get("filename"),
                    "status": f.get("status"),
                    "patch": f.get("patch")
                })
            
            # Follow pagination links (requests parses link headers automatically into response.links)
            url = response.links.get("next", {}).get("url")
            
        return files

    def post_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_id: str,
        comments: list[dict],
        body: str = "",
        event: str = "COMMENT"
    ) -> dict:
        """
        Submits a pull request review with multiple inline comments.
        
        Each item in comments must be:
        {
            "path": str,   # File path
            "line": int,   # Line number (head side)
            "body": str,   # Comment body
            "side": str    # "RIGHT" (default side of PR head changes)
        }
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        payload = {
            "commit_id": commit_id,
            "event": event
        }
        if body:
            payload["body"] = body
        if comments:
            payload["comments"] = comments

        try:
            response = requests.post(url, json=payload, headers=self.headers)
        except Exception as e:
            raise GitHubAPIError(f"Network request to GitHub failed: {e}")

        self._check_response(response)

        try:
            data = response.json()
            if not isinstance(data, dict):
                raise GitHubAPIError(f"Expected a dict from POST review response, got: {type(data)}")
            return data
        except (ValueError, TypeError) as e:
            raise GitHubAPIError(
                f"Failed to parse JSON response from GitHub API: {e}. Raw response: {response.text}"
            )

