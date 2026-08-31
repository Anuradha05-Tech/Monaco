import re
from app.engine.pr_review_orchestrator import PRReviewOrchestrator
from app.github.github_client import GitHubClient
from app.github.review_comment_formatter import ReviewCommentFormatter


FINDING_MARKER_REGEX = re.compile(r"<!-- monaco-finding:(?P<file>[^:]+):(?P<line>\d+):(?P<rule_id>[^ ]+) -->")

def parse_finding_marker(body: str):
    """
    Parses a monaco-finding marker from a comment body.
    Returns a tuple (file, line, rule_id) if found, else None.
    """
    match = FINDING_MARKER_REGEX.search(body)
    if match:
        file = match.group("file")
        line = int(match.group("line"))
        rule_id = match.group("rule_id")
        if rule_id == "none":
            rule_id = None
        return (file, line, rule_id)
    return None

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
        # 1. Fetch PR head commit ID
        pr_data = self.client.get_pull_request(owner, repo, pr_number)
        commit_id = pr_data.get("head", {}).get("sha")
        if not commit_id:
            raise ValueError("Could not retrieve head commit SHA for the pull request.")

        # 2. Check if MONACO has already reviewed this exact commit_id
        existing_reviews = self.client.get_existing_reviews(owner, repo, pr_number)
        marker = f"<!-- monaco-review:{commit_id} -->"
        for r in existing_reviews:
            body = r.get("body") or ""
            if marker in body:
                return {
                    "already_reviewed": True,
                    "existing_review_url": r.get("html_url"),
                    "posted_count": 0
                }

        # 3. Run PR Review Orchestrator to get ranked findings
        review_result = self.orchestrator.review_pull_request(
            owner, repo, pr_number, local_repo_path
        )
        findings = review_result.get("findings", [])

        # 4. Build comments for in-diff findings
        comments = self.formatter.build_review_comments(findings)
        
        # 5. Handle zero in-diff findings
        if not comments:
            if dry_run:
                return {
                    "already_reviewed": False,
                    "dry_run": True,
                    "would_post_count": 0,
                    "comments": []
                }
            else:
                return {
                    "already_reviewed": False,
                    "dry_run": False,
                    "posted_count": 0,
                    "review_url": None
                }

        # 6. Fetch existing review comments and filter out duplicates
        existing_comments = self.client.get_existing_review_comments(owner, repo, pr_number)
        already_flagged = set()
        for ec in existing_comments:
            body = ec.get("body") or ""
            parsed = parse_finding_marker(body)
            if parsed:
                already_flagged.add(parsed)

        filtered_comments = []
        for c in comments:
            parsed = parse_finding_marker(c["body"])
            if parsed and parsed in already_flagged:
                continue
            filtered_comments.append(c)

        # 7. If filtering leaves zero new comments
        if not filtered_comments:
            if dry_run:
                return {
                    "already_reviewed": False,
                    "no_new_findings": True,
                    "dry_run": True,
                    "would_post_count": 0,
                    "total_findings_found": len(comments),
                    "comments": []
                }
            else:
                return {
                    "already_reviewed": False,
                    "no_new_findings": True,
                    "dry_run": False,
                    "posted_count": 0,
                    "total_findings_found": len(comments),
                    "review_url": None
                }

        # 8. Dry Run check
        if dry_run:
            return {
                "already_reviewed": False,
                "dry_run": True,
                "would_post_count": len(filtered_comments),
                "total_findings_found": len(comments),
                "comments": filtered_comments
            }

        # 9. Post the review atomically with only the filtered comments
        review_body = f"MONACO automated code review findings.\n{marker}"
        review_response = self.client.post_review(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            commit_id=commit_id,
            comments=filtered_comments,
            body=review_body,
            event="COMMENT"
        )

        review_url = review_response.get("html_url")

        return {
            "already_reviewed": False,
            "dry_run": False,
            "posted_count": len(filtered_comments),
            "total_findings_found": len(comments),
            "review_url": review_url
        }


