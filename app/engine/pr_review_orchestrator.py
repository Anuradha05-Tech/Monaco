import os
from app.github.pr_context_builder import PRContextBuilder
from app.engine.review_engine import ReviewEngine
from app.models.finding import Finding

class PRReviewOrchestrator:
    """
    Orchestrates the end-to-end review of a GitHub Pull Request by combining
    PR diff metadata and file dependency structure with MONACO's analysis engine.
    """
    def __init__(self, pr_context_builder: PRContextBuilder, review_engine: ReviewEngine):
        """
        Initializes the PRReviewOrchestrator.
        
        Args:
            pr_context_builder: An instance of PRContextBuilder.
            review_engine: An instance of ReviewEngine.
        """
        self.pr_context_builder = pr_context_builder
        self.review_engine = review_engine

    def review_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        local_repo_path: str
    ) -> dict:
        """
        Reviews a pull request by fetching context, reviewing changed files,
        tagging findings in the diff, and deduplicating/ranking the aggregated results.
        
        Args:
            owner: The GitHub repository owner.
            repo: The GitHub repository name.
            pr_number: The pull request number.
            local_repo_path: The absolute path to the local git clone.
            
        Returns:
            A dictionary containing:
                "pr_title": The title of the pull request.
                "pr_number": The pull request number.
                "changed_files": List of changed file names.
                "skipped_files": List of files that were skipped (e.g. missing locally).
                "total_findings": Total count of findings.
                "findings_in_diff": Count of findings located on modified lines.
                "findings": Ranked list of Finding objects.
        """
        # a. Fetch PR review context
        context = self.pr_context_builder.build_pr_review_context(
            owner, repo, pr_number, local_repo_path
        )
        
        pr_title = context.get("pr_title", "")
        changed_files = context.get("changed_files", [])
        changed_lines = context.get("changed_lines", {})
        
        # Note on related_files:
        # Currently, related_files contains dependency context mapping changed files to other files
        # in the codebase (depth=1). Using these related_files to feed the AI reviewer richer,
        # cross-file context (e.g. by passing their contents or summaries) is a natural future 
        # enhancement to expand review capabilities, but is not implemented in this phase.
        
        skipped_files = []
        combined_findings = []
        
        # b. For each changed file, read its source and analyze
        for filename in changed_files:
            file_path = os.path.join(local_repo_path, filename)
            
            # Check if file exists and is readable
            if not os.path.exists(file_path) or os.path.isdir(file_path):
                skipped_files.append(filename)
                continue
                
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    code = f.read()
            except Exception:
                skipped_files.append(filename)
                continue
            
            # c. Run file's source code through the ReviewEngine
            file_findings = self.review_engine.review(code)
            
            # d. Tag findings with in_diff and file path
            for finding in file_findings:
                finding.file = filename
                
                # Check if finding's line is within the PR's changed lines
                lines_changed = changed_lines.get(filename, [])
                if finding.line is not None and finding.line in lines_changed:
                    finding.in_diff = True
                else:
                    finding.in_diff = False
                    
                combined_findings.append(finding)
                
        # f. Deduplicate and rank across the WHOLE combined list
        unique_findings = self.review_engine.deduplicator.deduplicate(combined_findings)
        ranked_findings = self.review_engine.ranker.rank(unique_findings)
        
        # Calculate findings in diff
        findings_in_diff_count = sum(1 for f in ranked_findings if f.in_diff)
        
        return {
            "pr_title": pr_title,
            "pr_number": pr_number,
            "changed_files": changed_files,
            "skipped_files": skipped_files,
            "total_findings": len(ranked_findings),
            "findings_in_diff": findings_in_diff_count,
            "findings": ranked_findings
        }
