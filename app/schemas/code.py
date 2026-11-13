import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.course import DifficultyLevel


class CodeIssueSeverity(enum.StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CodeIssue(BaseModel):
    """Specific line-level code issue or improvement suggestion."""

    model_config = ConfigDict(extra="ignore")

    line_number: int | None = Field(
        default=None, description="Source code line number, if applicable"
    )
    severity: CodeIssueSeverity = Field(
        default=CodeIssueSeverity.WARNING,
        description="Severity: info, warning, or critical",
    )
    message: str = Field(..., description="Description of the bug, anti-pattern, or code smell")
    suggestion: str = Field(..., description="Actionable recommendation for resolving the issue")


class AICodeReviewPayload(BaseModel):
    """Gemini structured output payload for comprehensive code review."""

    model_config = ConfigDict(extra="ignore")

    score: int = Field(..., ge=0, le=100, description="Overall quality score from 0 to 100")
    is_passed: bool = Field(
        ..., description="Whether the code meets architectural and functional standards"
    )
    time_complexity: str = Field(..., description="Estimated runtime time complexity (e.g. 'O(n)')")
    space_complexity: str = Field(
        ..., description="Estimated memory space complexity (e.g. 'O(1)')"
    )
    review_summary: str = Field(..., description="Holistic architectural assessment paragraph")
    strengths: list[str] = Field(
        ..., min_length=1, description="Positive aspects of the implementation"
    )
    issues: list[CodeIssue] = Field(default=[], description="List of detected bugs or design flaws")
    refactored_code: str | None = Field(
        default=None,
        description="Clean, production-grade refactored code demonstrating best practices",
    )


class CodeReviewRequest(BaseModel):
    """Student submission payload for code review and scoring."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=2, max_length=200, description="Exercise or snippet title")
    source_code: str = Field(
        ..., min_length=5, max_length=20000, description="Source code to review"
    )
    language: str = Field(default="python", max_length=50, description="Programming language")
    lesson_id: str | None = Field(
        default=None, description="Optional lesson ID to ground the review"
    )
    problem_description: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional problem description or specification",
    )


class CodeSubmissionResponse(BaseModel):
    """Response payload for a persisted code submission and its architectural review."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    lesson_id: str | None
    title: str
    language: str
    source_code: str
    score: int
    is_passed: bool
    time_complexity: str | None
    space_complexity: str | None
    review_summary: str
    strengths: list[str]
    issues: list[CodeIssue]
    refactored_code: str | None
    created_at: datetime


class CodingTestCase(BaseModel):
    """Specification of a test case for coding challenges."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Descriptive test case name")
    input_description: str = Field(..., description="Input parameter representation")
    expected_output: str = Field(..., description="Expected return value or output")
    is_hidden: bool = Field(
        default=False, description="Whether test case is concealed in student preview"
    )


class AICodingExercisePayload(BaseModel):
    """Gemini structured output payload for an AI generated coding challenge."""

    model_config = ConfigDict(extra="ignore")

    title: str = Field(..., description="Engaging challenge title")
    description: str = Field(..., description="Comprehensive problem statement and requirements")
    difficulty: DifficultyLevel = Field(..., description="Difficulty rating")
    starter_code: str = Field(..., description="Boilerplate starter code for the learner")
    solution_code: str = Field(..., description="Reference implementation")
    test_cases: list[CodingTestCase] = Field(..., min_length=1, description="Test suite")
    hints: list[str] = Field(default=[], description="Progressive hints")


class GenerateExerciseRequest(BaseModel):
    """Request payload to generate a tailored coding exercise."""

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(..., min_length=2, max_length=150, description="Technical concept or topic")
    difficulty: DifficultyLevel = Field(
        default=DifficultyLevel.INTERMEDIATE, description="Target difficulty"
    )
    lesson_id: str | None = Field(
        default=None, description="Optional lesson ID to ground the challenge"
    )
    custom_instructions: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional custom pedagogical focus",
    )


class CodingExerciseResponse(BaseModel):
    """Response payload containing generated coding exercise for students."""

    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str
    difficulty: DifficultyLevel
    starter_code: str
    test_cases: list[CodingTestCase]
    hints: list[str]
