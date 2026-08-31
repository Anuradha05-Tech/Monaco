from app.graph.state import ReviewState

def has_changed_python_files(state: ReviewState) -> str:
    """
    Checks if there are any changed Python files in the PR context.
    
    Returns:
        "analyze" if there is at least one file ending with ".py", else "skip_to_end".
    """
    pr_context = state.get("pr_context") or {}
    changed_files = pr_context.get("changed_files", [])
    
    has_py = any(f.endswith(".py") for f in changed_files)
    if has_py:
        return "analyze"
    return "skip_to_end"

def check_validation_quality(state: ReviewState) -> str:
    """
    Checks if the proportion of rejected findings is high, suggesting low AI/heuristic quality.
    
    Boundary condition:
        "exceeds 0.5" is interpreted as strictly greater than 0.5 (> 0.5).
        - A rejection ratio of 0.5 (exactly 50%) is not flagged (returns "rank").
        - A rejection ratio of 0.51 (51%) is flagged (returns "flag_review").
        - A rejection ratio of 0.49 (49%) is not flagged (returns "rank").
    """
    rejection_ratio = state.get("rejection_ratio", 0.0)
    if rejection_ratio > 0.5:
        return "flag_review"
    return "rank"
