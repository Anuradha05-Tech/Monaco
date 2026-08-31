import os
import sys

# Ensure project root is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.github.github_client import GitHubClient
from app.github.pr_diff_parser import PRDiffParser
from app.repository.dependency_graph import DependencyGraphBuilder
from app.repository.context_retriever import ContextRetriever
from app.github.pr_context_builder import PRContextBuilder
from app.engine.review_engine import ReviewEngine
from app.engine.pr_review_orchestrator import PRReviewOrchestrator
from app.github.review_comment_formatter import ReviewCommentFormatter
from app.engine.pr_reviewer import PRReviewer

def main():
    print("=== Initializing MONACO Phase 13 PR Reviewer (REAL Post Test) ===")

    # 1. Instantiate all components
    github_client = GitHubClient()
    pr_diff_parser = PRDiffParser()
    graph_builder = DependencyGraphBuilder()
    
    pr_context_builder = PRContextBuilder(
        github_client=github_client,
        pr_diff_parser=pr_diff_parser,
        graph_builder=graph_builder,
        context_retriever_class=ContextRetriever
    )
    
    review_engine = ReviewEngine()
    
    orchestrator = PRReviewOrchestrator(
        pr_context_builder=pr_context_builder,
        review_engine=review_engine
    )

    formatter = ReviewCommentFormatter()

    reviewer = PRReviewer(
        orchestrator=orchestrator,
        client=github_client,
        formatter=formatter
    )

    # 2. Run the reviewer in dry_run=False mode
    owner = "Anuradha05-Tech"
    repo = "monaco-test-repo"
    pr_number = 1
    local_repo_path = "/home/user/Documents/monaco-test-repo-clone"

    print(f"Running review_and_post (dry_run=False) for {owner}/{repo} PR #{pr_number}...")
    print(f"Local repo clone path: {local_repo_path}\n")

    try:
        result = reviewer.review_and_post(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            local_repo_path=local_repo_path,
            dry_run=False
        )
    except Exception as e:
        print(f"Error during PR review posting: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Print the results clearly
    print("=== REAL Post Output Result ===")
    print(f"Already Reviewed:    {result.get('already_reviewed')}")
    print(f"Existing Review URL: {result.get('existing_review_url')}")
    print(f"Dry Run:             {result.get('dry_run')}")
    print(f"Posted Comments:     {result.get('posted_count')}")
    print(f"Review URL:          {result.get('review_url')}")
    print("=" * 60)

if __name__ == "__main__":
    main()
