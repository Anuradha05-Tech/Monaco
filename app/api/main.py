import os
import json
import datetime
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from app.graph.pr_review_graph import run_pr_review
from app.api.schemas import ReviewRequest, PostReviewRequest
from app.github.github_client import GitHubClient, MissingGitHubTokenError, GitHubAPIError
from app.github.pr_diff_parser import PRDiffParser
from app.repository.dependency_graph import DependencyGraphBuilder
from app.repository.context_retriever import ContextRetriever
from app.github.pr_context_builder import PRContextBuilder
from app.engine.review_engine import ReviewEngine
from app.engine.pr_review_orchestrator import PRReviewOrchestrator
from app.github.review_comment_formatter import ReviewCommentFormatter
from app.engine.pr_reviewer import PRReviewer

# Load environment variables from root path .env file
load_dotenv()

app = FastAPI(
    title="MONACO API",
    description="Backend API for the MONACO AI-powered PR Review Platform",
    version="1.0.0"
)

# Configure CORS for local frontend testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resolve directories
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
HISTORY_DIR = os.path.join(PROJECT_ROOT, ".monaco_history")
os.makedirs(HISTORY_DIR, exist_ok=True)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

def serialize_finding(finding) -> dict:
    if hasattr(finding, "model_dump"):
        return finding.model_dump()
    elif hasattr(finding, "dict"):
        return finding.dict()
    elif isinstance(finding, dict):
        return finding
    return str(finding)

def serialize_state(state: dict) -> dict:
    serialized = {}
    for k, v in state.items():
        if k in [
            "security_findings", 
            "quality_findings", 
            "performance_findings", 
            "all_findings", 
            "deduplicated_findings", 
            "validated_findings", 
            "final_findings"
        ]:
            serialized[k] = [serialize_finding(f) for f in (v or [])]
        elif k == "pr_context" and v:
            serialized[k] = v
        else:
            serialized[k] = v
            
    # Compute and add conditional branches based on execution logs
    logs = state.get("status_logs", [])
    
    # has_changed_python_files conditional edge decision
    if "start_analysis" in logs or any(
        agent in logs for agent in ["security_agent_node", "quality_agent_node", "performance_agent_node"]
    ):
        has_py_branch = "analyze"
    else:
        has_py_branch = "skip_to_end"
        
    # check_validation_quality conditional edge decision
    if "validate_node" in logs:
        validation_branch = "flag_review" if "flag_for_manual_review_node" in logs else "rank"
    else:
        validation_branch = None
        
    serialized["conditional_branches"] = {
        "has_changed_python_files": has_py_branch,
        "check_validation_quality": validation_branch
    }
    return serialized

@app.post("/api/review", status_code=status.HTTP_200_OK)
def review_pr(request: ReviewRequest):
    """
    Runs the full PR review graph on the given repository and pull request.
    This call is synchronous and blocking.
    """
    # 1. Validation checks
    if not os.path.exists(request.local_repo_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Local repository path '{request.local_repo_path}' does not exist on the server."
        )
    
    if not os.path.isdir(request.local_repo_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Local repository path '{request.local_repo_path}' is not a directory."
        )

    if not os.environ.get("GITHUB_TOKEN"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GITHUB_TOKEN environment variable is not configured on the server."
        )

    if not os.environ.get("GROQ_API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GROQ_API_KEY environment variable is not configured on the server."
        )

    # 2. Run the LangGraph PR review flow
    try:
        final_state = run_pr_review(
            owner=request.owner,
            repo=request.repo,
            pr_number=request.pr_number,
            local_repo_path=request.local_repo_path
        )
    except MissingGitHubTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing GITHUB_TOKEN configuration: {str(e)}"
        )
    except GitHubAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub API Error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing review graph: {str(e)}"
        )

    # 3. Serialize and prepare history entry
    serialized = serialize_state(final_state)
    
    # Generate timestamp and unique key
    now = datetime.datetime.utcnow()
    timestamp_str = now.isoformat() + "Z"
    history_id = now.strftime("%Y%m%d_%H%M%S_%f")

    # Add metadata fields to the serialized dictionary for history tracking
    serialized["id"] = history_id
    serialized["timestamp"] = timestamp_str
    
    # Store complete review state to history file
    history_file_path = os.path.join(HISTORY_DIR, f"{history_id}.json")
    try:
        with open(history_file_path, "w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=2)
    except Exception as e:
        # Don't fail the request if history save fails, but log it
        print(f"Warning: Failed to save run to history directory: {e}")

    return serialized

@app.post("/api/post-review", status_code=status.HTTP_200_OK)
def post_review_comments(request: PostReviewRequest):
    """
    Coordinates reviewing a PR and posting the comments to GitHub.
    Uses the safety-first 'dry_run' parameter which defaults to True.
    """
    # 1. Validation checks
    if not os.path.exists(request.local_repo_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Local repository path '{request.local_repo_path}' does not exist on the server."
        )

    if not os.environ.get("GITHUB_TOKEN"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GITHUB_TOKEN environment variable is not configured on the server."
        )

    # 2. Instantiate dependencies for PRReviewer
    try:
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error initializing review components: {str(e)}"
        )

    # 3. Call reviewer.review_and_post()
    try:
        result = reviewer.review_and_post(
            owner=request.owner,
            repo=request.repo,
            pr_number=request.pr_number,
            local_repo_path=request.local_repo_path,
            dry_run=request.dry_run
        )
        return result
    except MissingGitHubTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing GITHUB_TOKEN configuration: {str(e)}"
        )
    except GitHubAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub API Error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing and posting review: {str(e)}"
        )

@app.get("/api/history", response_model=List[Dict[str, Any]])
def get_review_history():
    """
    Returns a sorted list of past review runs stored under .monaco_history/
    """
    history_entries = []
    
    if not os.path.exists(HISTORY_DIR):
        return []

    for filename in os.listdir(HISTORY_DIR):
        if filename.endswith(".json"):
            file_path = os.path.join(HISTORY_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Extract summary info
                final_findings = data.get("final_findings", [])
                
                history_entries.append({
                    "id": data.get("id"),
                    "timestamp": data.get("timestamp"),
                    "owner": data.get("owner"),
                    "repo": data.get("repo"),
                    "pr_number": data.get("pr_number"),
                    "local_repo_path": data.get("local_repo_path"),
                    "total_findings": len(final_findings),
                    "needs_manual_review": data.get("needs_manual_review", False),
                    "rejection_ratio": data.get("rejection_ratio", 0.0),
                    "pr_title": data.get("pr_context", {}).get("pr_title") if data.get("pr_context") else None
                })
            except Exception as e:
                # Log warning and skip malformed history files
                print(f"Warning: Failed to read history file {filename}: {e}")
                
    # Sort history entries by timestamp descending
    history_entries.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return history_entries

@app.get("/api/history/{history_id}", response_model=Dict[str, Any])
def get_history_detail(history_id: str):
    """
    Retrieves the full detail of a specific past review run from its ID.
    """
    file_path = os.path.join(HISTORY_DIR, f"{history_id}.json")
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"History record with ID '{history_id}' not found."
        )
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading history record: {str(e)}"
        )

@app.get("/api/graph-structure")
def get_graph_structure():
    """
    Returns the static JSON description of the LangGraph structure.
    
    IMPORTANT: This structure matches the graph built in app/graph/pr_review_graph.py.
    This description must be kept in sync manually if the graph structure changes.
    """
    return {
        "nodes": [
            {"id": "START", "label": "START", "type": "special"},
            {"id": "fetch_pr_context", "label": "Fetch PR Context", "type": "node"},
            {"id": "start_analysis", "label": "Start Parallel Analysis", "type": "node"},
            {"id": "security_agent", "label": "Security Agent", "type": "agent"},
            {"id": "quality_agent", "label": "Quality Agent", "type": "agent"},
            {"id": "performance_agent", "label": "Performance Agent", "type": "agent"},
            {"id": "merge_agent_findings", "label": "Merge Agent Findings", "type": "node"},
            {"id": "deduplicate", "label": "Deduplicate Findings", "type": "node"},
            {"id": "validate", "label": "Validate Code Syntax", "type": "node"},
            {"id": "flag_for_manual_review", "label": "Flag for Manual Review", "type": "warning"},
            {"id": "rank", "label": "Rank Findings", "type": "node"},
            {"id": "END", "label": "END", "type": "special"}
        ],
        "edges": [
            {"source": "START", "target": "fetch_pr_context", "type": "direct"},
            {
                "source": "fetch_pr_context",
                "target": "start_analysis",
                "type": "conditional",
                "condition": "has_changed_python_files",
                "branch": "analyze"
            },
            {
                "source": "fetch_pr_context",
                "target": "END",
                "type": "conditional",
                "condition": "has_changed_python_files",
                "branch": "skip_to_end"
            },
            {"source": "start_analysis", "target": "security_agent", "type": "direct"},
            {"source": "start_analysis", "target": "quality_agent", "type": "direct"},
            {"source": "start_analysis", "target": "performance_agent", "type": "direct"},
            {"source": "security_agent", "target": "merge_agent_findings", "type": "direct"},
            {"source": "quality_agent", "target": "merge_agent_findings", "type": "direct"},
            {"source": "performance_agent", "target": "merge_agent_findings", "type": "direct"},
            {"source": "merge_agent_findings", "target": "deduplicate", "type": "direct"},
            {"source": "deduplicate", "target": "validate", "type": "direct"},
            {
                "source": "validate",
                "target": "flag_for_manual_review",
                "type": "conditional",
                "condition": "check_validation_quality",
                "branch": "flag_review"
            },
            {
                "source": "validate",
                "target": "rank",
                "type": "conditional",
                "condition": "check_validation_quality",
                "branch": "rank"
            },
            {"source": "flag_for_manual_review", "target": "rank", "type": "direct"},
            {"source": "rank", "target": "END", "type": "direct"}
        ]
    }

# Serve Frontend static files if the directory exists
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    
    @app.get("/")
    def read_index():
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "MONACO API is running. Frontend index.html not found yet. Please create frontend/index.html."}
