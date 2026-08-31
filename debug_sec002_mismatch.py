import os
import sys

# Ensure project root is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.github.github_client import GitHubClient
from app.engine.pr_reviewer import parse_finding_marker

def main():
    print("=== Diagnostic: Print all review comments in detail ===")
    
    owner = "Anuradha05-Tech"
    repo = "monaco-test-repo"
    pr_number = 1
    
    client = GitHubClient()
    comments = client.get_existing_review_comments(owner, repo, pr_number)
    print(f"Total comments: {len(comments)}")
    
    for idx, c in enumerate(comments, 1):
        print(f"\nComment #{idx}:")
        print(f"  ID:          {c.get('id')}")
        print(f"  Path:        {c.get('path')}")
        print(f"  Line:        {c.get('line')}")
        print(f"  Orig Line:   {c.get('original_line')}")
        print(f"  Commit SHA:  {c.get('commit_id')}")
        print(f"  Orig SHA:    {c.get('original_commit_id')}")
        print(f"  HTML URL:    {c.get('html_url')}")
        print(f"  Created At:  {c.get('created_at')}")
        body = c.get("body") or ""
        print(f"  Body (repr): {repr(body)}")
        parsed = parse_finding_marker(body)
        print(f"  Parsed Key:  {parsed}")

if __name__ == "__main__":
    main()
