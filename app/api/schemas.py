from pydantic import BaseModel, Field

class ReviewRequest(BaseModel):
    owner: str = Field(..., description="The owner of the GitHub repository")
    repo: str = Field(..., description="The name of the GitHub repository")
    pr_number: int = Field(..., description="The pull request number")
    local_repo_path: str = Field(..., description="The absolute path to the local git repository clone")

class PostReviewRequest(BaseModel):
    owner: str = Field(..., description="The owner of the GitHub repository")
    repo: str = Field(..., description="The name of the GitHub repository")
    pr_number: int = Field(..., description="The pull request number")
    local_repo_path: str = Field(..., description="The absolute path to the local git repository clone")
    dry_run: bool = Field(default=True, description="Safety-first dry_run flag. If True, comments will not be posted to GitHub.")
