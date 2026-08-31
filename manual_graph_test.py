import os
import sys

# Ensure project root is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import MagicMock
from app.github.github_client import GitHubClient
from app.github.pr_diff_parser import PRDiffParser
from app.repository.dependency_graph import DependencyGraphBuilder
from app.repository.context_retriever import ContextRetriever
from app.github.pr_context_builder import PRContextBuilder
from app.engine.review_engine import ReviewEngine
from app.graph.pr_review_graph import run_pr_review

def main():
    print("=== Initializing MONACO Phase 14 StateGraph (REAL PR Test) ===")

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

    owner = "Anuradha05-Tech"
    repo = "monaco-test-repo"
    pr_number = 1
    local_repo_path = "/home/user/Documents/monaco-test-repo-clone"

    print(f"Running run_pr_review() for {owner}/{repo} PR #{pr_number}...")
    print(f"Local repository path: {local_repo_path}\n")

    try:
        final_state = run_pr_review(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            local_repo_path=local_repo_path,
            pr_context_builder=pr_context_builder,
            review_engine=review_engine
        )
    except Exception as e:
        print(f"Error during PR review graph run: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 2. Deduce branches taken
    logs = final_state.get("status_logs", [])
    
    has_py_branch = "analyze" if "security_agent_node" in logs else "skip_to_end"
    
    quality_branch = "rank"
    if "flag_for_manual_review_node" in logs:
        quality_branch = "flag_review"

    # 3. Print the results clearly
    print("=== Graph Execution Summary ===")
    print(f"Nodes executed in order:  {logs}")
    print(f"Conditional Edge 1 (changed_files):  '{has_py_branch}'")
    print(f"Conditional Edge 2 (validation):      '{quality_branch}'")
    print(f"Needs Manual Review:                  {final_state.get('needs_manual_review')}")
    print(f"Validation Rejection Ratio:           {final_state.get('rejection_ratio', 0.0):.2%}")
    print(f"Skipped Files:                        {final_state.get('skipped_files', [])}")
    print(f"Final Findings Count:                 {len(final_state.get('final_findings', []))}")
    print("=" * 60)

    print("\n=== Agent Findings (Before Merge) ===")
    
    print("\n[Security Agent Findings]")
    sec_findings = final_state.get("security_findings", [])
    if not sec_findings:
        print("  No security findings.")
    for i, finding in enumerate(sec_findings, 1):
        severity_val = finding.severity.value if hasattr(finding.severity, "value") else finding.severity
        print(f"  {i}. Rule ID: {finding.rule_id} | Line: {finding.line} | Severity: {severity_val} | In Diff: {finding.in_diff}")
        print(f"     Message: {finding.message}")
        
    print("\n[Quality Agent Findings]")
    qual_findings = final_state.get("quality_findings", [])
    if not qual_findings:
        print("  No quality findings.")
    for i, finding in enumerate(qual_findings, 1):
        severity_val = finding.severity.value if hasattr(finding.severity, "value") else finding.severity
        print(f"  {i}. Rule ID: {finding.rule_id} | Line: {finding.line} | Severity: {severity_val} | In Diff: {finding.in_diff}")
        print(f"     Message: {finding.message}")
        
    print("\n[Performance Agent Findings]")
    perf_findings = final_state.get("performance_findings", [])
    if not perf_findings:
        print("  No performance findings.")
    for i, finding in enumerate(perf_findings, 1):
        severity_val = finding.severity.value if hasattr(finding.severity, "value") else finding.severity
        print(f"  {i}. Rule ID: {finding.rule_id} | Line: {finding.line} | Severity: {severity_val} | In Diff: {finding.in_diff}")
        print(f"     Message: {finding.message}")

    print("\n=== Final Findings Details (After Merge, Deduplication, and Validation) ===")
    findings = final_state.get("final_findings", [])
    for i, finding in enumerate(findings, 1):
        severity_val = finding.severity.value if hasattr(finding.severity, "value") else finding.severity
        print(f"{i}. Rule ID: {finding.rule_id} | Line: {finding.line} | Severity: {severity_val} | In Diff: {finding.in_diff}")
        print(f"   Message:   {finding.message}")
        print(f"   Source(s): {finding.sources if finding.sources else [finding.source]}")
        print("-" * 60)

    # 4. Dry Run check with ZERO changed Python files
    print("\n=== Initializing MONACO Phase 14 StateGraph (README-only PR Test) ===")
    mock_context_builder = MagicMock()
    mock_context_builder.build_pr_review_context.return_value = {
        "pr_title": "Update Documentation",
        "changed_files": ["README.md"],
        "changed_lines": {}
    }
    
    final_state_readme = run_pr_review(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        local_repo_path=local_repo_path,
        pr_context_builder=mock_context_builder,
        review_engine=review_engine
    )
    
    logs_readme = final_state_readme.get("status_logs", [])
    print(f"Nodes executed for README-only PR: {logs_readme}")
    
    # Assert and verify skipped nodes
    for node in [
        "security_agent_node", "quality_agent_node", "performance_agent_node",
        "merge_agent_findings_node", "deduplicate_node", "validate_node", "rank_node"
    ]:
        assert node not in logs_readme
    print("Verification PASSED: None of the analysis/deduplicate/validate/rank nodes were executed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
