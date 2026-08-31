from typing import TypedDict, Optional, Annotated
import operator
from app.models.finding import Finding

# Tradeoff between TypedDict and Pydantic model for LangGraph state:
# 1. TypedDict (Chosen):
#    - Native fit for LangGraph. Nodes can return simple dict updates, which LangGraph automatically
#      merges into the state.
#    - Less overhead; no need to instantiate or validate Pydantic objects during every node execution.
#    - Allows flexibility in partial updates without triggering schema validation errors on incomplete states.
# 2. Pydantic Model:
#    - Pros: Strict type coercion, runtime field validation, and clean serialization out-of-the-box.
#    - Cons: Enforces strict schema constraints at every step, requiring all required fields to be present
#      or set as Optional, and adds validation overhead to every node execution.
class ReviewState(TypedDict):
    owner: str
    repo: str
    pr_number: int
    local_repo_path: str
    pr_context: Optional[dict]
    all_findings: list[Finding]
    security_findings: list[Finding]
    quality_findings: list[Finding]
    performance_findings: list[Finding]
    deduplicated_findings: list[Finding]
    validated_findings: list[Finding]
    final_findings: list[Finding]
    skipped_files: Annotated[list[str], operator.add]
    needs_manual_review: bool
    rejection_ratio: float
    status_logs: Annotated[list[str], operator.add]


