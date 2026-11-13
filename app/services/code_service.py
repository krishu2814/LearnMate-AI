from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts.code_prompts import (
    build_code_review_prompt,
    build_exercise_generation_prompt,
)
from app.ai.providers.gemini import GeminiProvider
from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.models.code_submission import CodeSubmission
from app.repositories.code_repo import CodeRepository
from app.repositories.learning_repo import LearningRepository
from app.schemas.code import (
    CodeIssue,
    CodeReviewRequest,
    CodeSubmissionResponse,
    CodingExerciseResponse,
    GenerateExerciseRequest,
)


class CodeService:
    """Service orchestrating AI code reviews, algorithmic analysis, and coding exercise generation."""

    def __init__(self, db: AsyncSession, ai_provider: GeminiProvider | None = None):
        self.db = db
        self.code_repo = CodeRepository(db)
        self.learning_repo = LearningRepository(db)
        self.ai_provider = ai_provider or GeminiProvider()

    async def review_code(
        self,
        user_id: str,
        payload: CodeReviewRequest,
    ) -> CodeSubmissionResponse:
        """
        Perform in-depth architectural and algorithmic review of user submitted code.
        Persists the result for the student's portfolio.
        """
        lesson_title = None
        lesson_content = None

        if payload.lesson_id:
            lesson = await self.learning_repo.get_lesson_by_id(payload.lesson_id)
            if not lesson:
                raise NotFoundException(f"Lesson '{payload.lesson_id}' not found")
            lesson_title = lesson.title
            lesson_content = lesson.content

        prompt = build_code_review_prompt(
            title=payload.title,
            language=payload.language,
            source_code=payload.source_code,
            problem_description=payload.problem_description,
            lesson_title=lesson_title,
            lesson_content=lesson_content,
        )

        review_payload = await self.ai_provider.review_code(
            prompt=prompt,
            source_code=payload.source_code,
            language=payload.language,
        )

        issues_data = [issue.model_dump() for issue in review_payload.issues]

        submission = CodeSubmission(
            user_id=user_id,
            title=payload.title,
            language=payload.language,
            source_code=payload.source_code,
            lesson_id=payload.lesson_id,
            score=review_payload.score,
            is_passed=review_payload.is_passed,
            time_complexity=review_payload.time_complexity,
            space_complexity=review_payload.space_complexity,
            review_summary=review_payload.review_summary,
            strengths=review_payload.strengths,
            issues=issues_data,
            refactored_code=review_payload.refactored_code,
        )

        await self.code_repo.create_submission(submission)
        await self.db.commit()

        logger.info(
            "code_review_completed",
            submission_id=submission.id,
            user_id=user_id,
            score=submission.score,
            is_passed=submission.is_passed,
        )

        return self._format_submission_response(submission)

    async def get_submission(
        self,
        user_id: str,
        submission_id: str,
    ) -> CodeSubmissionResponse:
        """Retrieve a specific code submission with ownership check."""
        submission = await self.code_repo.get_submission_by_id(
            submission_id=submission_id,
            user_id=user_id,
        )
        if not submission:
            raise NotFoundException(f"Code submission '{submission_id}' not found")
        return self._format_submission_response(submission)

    async def list_submissions(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[CodeSubmissionResponse]:
        """List all past code reviews for the authenticated student."""
        submissions = await self.code_repo.list_submissions(
            user_id=user_id,
            skip=skip,
            limit=limit,
        )
        return [self._format_submission_response(s) for s in submissions]

    async def generate_exercise(
        self,
        payload: GenerateExerciseRequest,
    ) -> CodingExerciseResponse:
        """Generate a hands-on coding challenge with test cases."""
        lesson_title = None
        lesson_content = None

        if payload.lesson_id:
            lesson = await self.learning_repo.get_lesson_by_id(payload.lesson_id)
            if lesson:
                lesson_title = lesson.title
                lesson_content = lesson.content

        prompt = build_exercise_generation_prompt(
            topic=payload.topic,
            difficulty=payload.difficulty,
            lesson_title=lesson_title,
            lesson_content=lesson_content,
            custom_instructions=payload.custom_instructions,
        )

        exercise_payload = await self.ai_provider.generate_exercise(
            prompt=prompt,
            topic=payload.topic,
            difficulty=payload.difficulty,
        )

        return CodingExerciseResponse(
            title=exercise_payload.title,
            description=exercise_payload.description,
            difficulty=exercise_payload.difficulty,
            starter_code=exercise_payload.starter_code,
            test_cases=exercise_payload.test_cases,
            hints=exercise_payload.hints,
        )

    def _format_submission_response(self, submission: CodeSubmission) -> CodeSubmissionResponse:
        parsed_issues = [
            CodeIssue(
                line_number=it.get("line_number"),
                severity=it.get("severity", "warning"),
                message=it.get("message", ""),
                suggestion=it.get("suggestion", ""),
            )
            for it in (submission.issues or [])
        ]

        return CodeSubmissionResponse(
            id=submission.id,
            user_id=submission.user_id,
            lesson_id=submission.lesson_id,
            title=submission.title,
            language=submission.language,
            source_code=submission.source_code,
            score=submission.score,
            is_passed=submission.is_passed,
            time_complexity=submission.time_complexity,
            space_complexity=submission.space_complexity,
            review_summary=submission.review_summary,
            strengths=submission.strengths,
            issues=parsed_issues,
            refactored_code=submission.refactored_code,
            created_at=submission.created_at,
        )
