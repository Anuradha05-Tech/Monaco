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

def main():
    print("=== Initializing MONACO Phase 12 PR Review Orchestrator ===")
    
    # 1. Instantiate all components
    github_client = GitHubClient()
    pr_diff_parser = PRDiffParser()
    graph_builder = DependencyGraphBuilder()
    
    # Note: ContextRetriever is passed as the class/factory type to PRContextBuilder
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
    
    # 2. Run the review against the real GitHub PR
    owner = "Anuradha05-Tech"
    repo = "monaco-test-repo"
    pr_number = 1
    local_repo_path = "/home/user/Documents/monaco-test-repo-clone"
    
    print(f"Retrieving and reviewing PR #{pr_number} from {owner}/{repo}...")
    print(f"Local repository path: {local_repo_path}\n")
    
    try:
        result = orchestrator.review_pull_request(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            local_repo_path=local_repo_path
        )
    except Exception as e:
        print(f"Error during PR review: {e}", file=sys.stderr)
        sys.exit(1)
        
    # 3. Print the results in a readable format
    print("=== Review Results ===")
    print(f"PR Title:          {result['pr_title']}")
    print(f"PR Number:         {result['pr_number']}")
    print(f"Changed Files:     {result['changed_files']}")
    print(f"Skipped Files:     {result['skipped_files']}")
    print(f"Total Findings:    {result['total_findings']}")
    print(f"Findings in Diff:  {result['findings_in_diff']}")
    print("\n=== Findings Details ===")
    
    for i, finding in enumerate(result["findings"], 1):
        in_diff_str = "[IN DIFF]" if finding.in_diff else "[NOT IN DIFF]"
        print(f"{i}. {in_diff_str} File: {finding.file} | Line: {finding.line} | Severity: {finding.severity} | Category: {finding.category}")
        print(f"   Message:     {finding.message}")
        print(f"   Suggestion:  {finding.suggestion}")
        print(f"   Source(s):   {finding.sources if finding.sources else [finding.source]}")
        print("-" * 60)

if __name__ == "__main__":
    main()
