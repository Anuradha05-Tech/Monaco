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
from app.engine.pr_reviewer import parse_finding_marker

def main():
    print("=== Diagnostic: Finding Deduplication Debugger ===")
    
    owner = "Anuradha05-Tech"
    repo = "monaco-test-repo"
    pr_number = 1
    local_repo_path = "/home/user/Documents/monaco-test-repo-clone"
    
    # 1. Fetch existing review comments
    client = GitHubClient()
    print("Fetching existing review comments from GitHub API...")
    try:
        comments = client.get_existing_review_comments(owner, repo, pr_number)
    except Exception as e:
        print(f"Error fetching comments: {e}")
        return
        
    print(f"Total comments returned: {len(comments)}")
    
    # 2. Print comments details and parse markers
    print("\n--- Details of Existing Review Comments ---")
    already_flagged = set()
    for idx, c in enumerate(comments, 1):
        path = c.get("path")
        line = c.get("line")
        orig_line = c.get("original_line")
        body = c.get("body") or ""
        
        print(f"\nComment #{idx}:")
        print(f"  Path:                  {path}")
        print(f"  Line (current):        {line}")
        print(f"  Original Line:         {orig_line}")
        
        parsed = parse_finding_marker(body)
        print(f"  Parsed Marker:         {parsed}")
        if parsed:
            already_flagged.add(parsed)
            
        # Check if the marker text itself exists in the body
        has_marker = "monaco-finding" in body
        print(f"  Contains 'monaco-finding' in body: {has_marker}")
        if has_marker:
            # Print body substring around the marker
            idx_marker = body.find("<!-- monaco-finding")
            print(f"  Marker text:           {body[idx_marker:].strip()}")
            
    print(f"\nSet of already flagged findings ({len(already_flagged)} keys):")
    for key in already_flagged:
        print(f"  {key}")

    # 3. Run PRReviewOrchestrator to get fresh findings
    print("\nRunning PRReviewOrchestrator for fresh findings...")
    pr_diff_parser = PRDiffParser()
    graph_builder = DependencyGraphBuilder()
    pr_context_builder = PRContextBuilder(
        github_client=client,
        pr_diff_parser=pr_diff_parser,
        graph_builder=graph_builder,
        context_retriever_class=ContextRetriever
    )
    review_engine = ReviewEngine()
    orchestrator = PRReviewOrchestrator(
        pr_context_builder=pr_context_builder,
        review_engine=review_engine
    )
    
    review_result = orchestrator.review_pull_request(owner, repo, pr_number, local_repo_path)
    findings = review_result.get("findings", [])
    print(f"Orchestrator returned {len(findings)} findings.")
    
    # 4. Generate comments and compare
    formatter = ReviewCommentFormatter()
    new_comments = formatter.build_review_comments(findings)
    print(f"Formatter generated {len(new_comments)} inline review comments.")
    
    print("\n--- Comparison & Matching ---")
    for idx, c in enumerate(new_comments, 1):
        parsed = parse_finding_marker(c["body"])
        print(f"\nNew Comment #{idx}:")
        print(f"  Path:                  {c['path']}")
        print(f"  Line:                  {c['line']}")
        print(f"  Parsed Marker Key:     {parsed}")
        
        should_exclude = parsed in already_flagged if parsed else False
        print(f"  Should be excluded?    {should_exclude}")

if __name__ == "__main__":
    main()
