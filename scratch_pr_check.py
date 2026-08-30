from app.github.github_client import GitHubClient
from app.github.pr_diff_parser import PRDiffParser

client = GitHubClient()
pr = client.get_pull_request("Anuradha05-Tech", "monaco-test-repo", 1)
print(pr["title"], pr["state"])

files = client.get_pr_files("Anuradha05-Tech", "monaco-test-repo", 1)
for f in files:
    print(f["filename"], f["status"])
    lines = PRDiffParser().parse_patch(f.get("patch"))
    print("added lines:", lines)
