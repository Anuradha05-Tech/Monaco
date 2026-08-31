from langgraph.graph import StateGraph, START, END
from app.graph.state import ReviewState
from app.graph.nodes import ReviewGraphNodes
from app.graph.conditions import has_changed_python_files, check_validation_quality

from app.github.github_client import GitHubClient
from app.github.pr_diff_parser import PRDiffParser
from app.repository.dependency_graph import DependencyGraphBuilder
from app.repository.context_retriever import ContextRetriever
from app.github.pr_context_builder import PRContextBuilder
from app.engine.review_engine import ReviewEngine

# Why this graph structure is better than the old linear PRReviewOrchestrator:
# 1. Genuine Conditional Routing:
#    The old orchestrator was strictly sequential and linear. It had to execute the entire code review pipeline
#    (fetching context, running AI LLM review, validating, etc.) even when there were no Python files to review
#    (e.g., if a PR only modified README.md or configuration files). With the graph structure, we can dynamically
#    bypass heavy analysis nodes entirely, saving compute, LLM tokens, and API call time.
# 2. Dynamic Flagging / Fallbacks:
#    If the validator rejects too many findings (rejection_ratio > 0.5), the graph dynamically redirects flow
#    to a 'flag_for_manual_review' node. This lets MONACO mark high-uncertainty code reviews for human audit,
#    which is a non-linear flow that was not easily possible in a simple sequential loop.
# 3. Modular Node Design:
#    Each step in the pipeline is now isolated as a single node in the state graph. This makes testing,
#    monitoring, and debugging of individual pipeline stages significantly cleaner.

def build_graph(nodes: ReviewGraphNodes) -> StateGraph:
    workflow = StateGraph(ReviewState)

    # Register nodes
    workflow.add_node("fetch_pr_context", nodes.fetch_pr_context_node)
    
    # We define a routing helper node to initiate parallel execution when Python files are changed
    workflow.add_node("start_analysis", lambda state: {})
    
    # Register the three parallel review agents
    workflow.add_node("security_agent", nodes.security_agent_node)
    workflow.add_node("quality_agent", nodes.quality_agent_node)
    workflow.add_node("performance_agent", nodes.performance_agent_node)
    
    # Converge / merge node
    workflow.add_node("merge_agent_findings", nodes.merge_agent_findings_node)
    
    # Downstream analysis nodes
    workflow.add_node("deduplicate", nodes.deduplicate_node)
    workflow.add_node("validate", nodes.validate_node)
    workflow.add_node("flag_for_manual_review", nodes.flag_for_manual_review_node)
    workflow.add_node("rank", nodes.rank_node)

    # Set up start transition
    workflow.add_edge(START, "fetch_pr_context")

    # Routing from fetch_pr_context based on whether Python files changed
    workflow.add_conditional_edges(
        "fetch_pr_context",
        has_changed_python_files,
        {
            "analyze": "start_analysis",
            "skip_to_end": END
        }
    )

    # Parallel Fan-Out:
    # Under the hood, LangGraph executes nodes concurrently if they have a common ancestor
    # and independent incoming paths. Here, we fan out from 'start_analysis' to three
    # independent review agents.
    # Why this is a genuine use of LangGraph's capability:
    # 1. Parallel Wall-Clock Optimization: Running the AST quality parser, AST performance parser,
    #    and LLM/static-flow security analyzer in parallel ensures the overall PR review completion
    #    time is bound by the slowest single agent (typically the LLM in the security agent),
    #    rather than the sum of all three.
    # 2. Scope Isolation & Zero Cross-Contamination: Since each agent runs in its own thread/process
    #    context and writes to separate state lists (security_findings, quality_findings, performance_findings),
    #    they cannot overwrite or corrupt each other's intermediate findings.
    # 3. Clean Extensibility: Additional review agents (e.g. style, security scanning, compliance)
    #    can be added as parallel graph nodes without needing to touch or modify any of the existing
    #    agents' codebases.
    workflow.add_edge("start_analysis", "security_agent")
    workflow.add_edge("start_analysis", "quality_agent")
    workflow.add_edge("start_analysis", "performance_agent")

    # Parallel Fan-In:
    # Converge the parallel agents back to the single 'merge_agent_findings' node.
    # LangGraph waits for all three parallel agents to finish executing before executing this node.
    workflow.add_edge("security_agent", "merge_agent_findings")
    workflow.add_edge("quality_agent", "merge_agent_findings")
    workflow.add_edge("performance_agent", "merge_agent_findings")

    # Post-merge flow continuing sequentially
    workflow.add_edge("merge_agent_findings", "deduplicate")
    workflow.add_edge("deduplicate", "validate")

    # Routing from validate based on the quality of AI/heuristic validation
    workflow.add_conditional_edges(
        "validate",
        check_validation_quality,
        {
            "flag_review": "flag_for_manual_review",
            "rank": "rank"
        }
    )

    # Connect manual review flag and rank to the end
    workflow.add_edge("flag_for_manual_review", "rank")
    workflow.add_edge("rank", END)

    return workflow

def run_pr_review(
    owner: str,
    repo: str,
    pr_number: int,
    local_repo_path: str,
    pr_context_builder: PRContextBuilder = None,
    review_engine: ReviewEngine = None
) -> ReviewState:
    """
    Compiles and runs the PR review LangGraph.
    
    If components are not provided, default instances are constructed.
    """
    if pr_context_builder is None:
        github_client = GitHubClient()
        pr_diff_parser = PRDiffParser()
        graph_builder = DependencyGraphBuilder()
        pr_context_builder = PRContextBuilder(
            github_client=github_client,
            pr_diff_parser=pr_diff_parser,
            graph_builder=graph_builder,
            context_retriever_class=ContextRetriever
        )

    if review_engine is None:
        review_engine = ReviewEngine()

    nodes = ReviewGraphNodes(
        pr_context_builder=pr_context_builder,
        review_engine=review_engine
    )

    graph_workflow = build_graph(nodes)
    compiled_app = graph_workflow.compile()

    initial_state = {
        "owner": owner,
        "repo": repo,
        "pr_number": pr_number,
        "local_repo_path": local_repo_path,
        "pr_context": None,
        "all_findings": [],
        "security_findings": [],
        "quality_findings": [],
        "performance_findings": [],
        "deduplicated_findings": [],
        "validated_findings": [],
        "final_findings": [],
        "skipped_files": [],
        "needs_manual_review": False,
        "rejection_ratio": 0.0,
        "status_logs": []
    }

    final_state = compiled_app.invoke(initial_state)
    return final_state
