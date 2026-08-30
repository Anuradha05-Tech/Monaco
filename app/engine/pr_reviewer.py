from app.engine.pr_review_orchestrator import PRReviewOrchestrator
from app.github.github_client import GitHubClient
from app.github.review_comment_formatter import ReviewCommentFormatter

class PRReviewer:
    """
    Coordinates analyzing a PR, formatting findings, and posting them as inline review comments.
    """
    def __init__(
        self, 
        orchestrator: PRReviewOrchestrator, 
        client: GitHubClient, 
        formatter: ReviewCommentFormatter
    ):
        self.orchestrator = orchestrator
        self.client = client
        self.formatter = formatter

    def review_and_post(
        self, 
        owner: str, 
        repo: str, 
        pr_number: int, 
        local_repo_path: str, 
        dry_run: bool = True
    ) -> dict:
        """
        Reviews a pull request and posts comments to GitHub, with dry-run support.
        
        Args:
            owner: Owner of the repository.
            repo: Name of the repository.
            pr_number: Pull request number.
            local_repo_path: Absolute path to the local repository clone.
            dry_run: If True, does not submit comments to GitHub.
            
        Returns:
            A dictionary summarizing the action taken.
        """
        # 1. Run PR Review Orchestrator to get ranked findings
        review_result = self.orchestrator.review_pull_request(
            owner, repo, pr_number, local_repo_path
        )
        findings = review_result.get("findings", [])

        # 2. Build comments for in-diff findings
        comments = self.formatter.build_review_comments(findings)
        
        # 3. Handle zero in-diff findings
        if not comments:
            if dry_run:
                return {
                    "dry_run": True,
                    "would_post_count": 0,
                    "comments": []
                }
            else:
                return {
                    "dry_run": False,
                    "posted_count": 0,
                    "review_url": None
                }

        # 4. Dry Run check
        if dry_run:
            return {
                "dry_run": True,
                "would_post_count": len(comments),
                "comments": comments
            }

        # 5. Fetch PR head commit ID and post the review
        pr_data = self.client.get_pull_request(owner, repo, pr_number)
        commit_id = pr_data.get("head", {}).get("sha")
        if not commit_id:
            raise ValueError("Could not retrieve head commit SHA for the pull request.")

        # Post the review atomically
        review_response = self.client.post_review(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            commit_id=commit_id,
            comments=comments,
            body="MONACO automated code review findings.",
            event="COMMENT"
        )

        review_url = review_response.get("html_url")

        return {
            "dry_run": False,
            "posted_count": len(comments),
            "review_url": review_url
        }
