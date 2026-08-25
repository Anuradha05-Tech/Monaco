from pydantic import BaseModel

from app.models.finding import Finding


class AIReview(BaseModel):

    findings: list[Finding]