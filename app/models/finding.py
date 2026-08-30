from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Finding(BaseModel):

    rule_id: str | None = None

    category: str

    severity: Severity

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0
    )

    file: str | None = None

    line: int | None = None

    message: str

    explanation: str | None = None

    suggestion: str | None = None

    source: str = "static_analyzer"

    sources: list[str] = Field(
        default_factory=list
    )

    in_diff: bool = False