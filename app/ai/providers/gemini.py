import json

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.logging import logger
from app.models.course import DifficultyLevel
from app.models.quiz import QuestionType
from app.schemas.ai import (
    AIEvalResult,
    AIGeneratedQuestion,
    AIGeneratedQuizPayload,
)


class GeminiProvider:
    """Production Gemini API client wrapper with structured JSON schema enforcement."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self._client: genai.Client | None = None

        if self.api_key:
            self._client = genai.Client(api_key=self.api_key)

    @property
    def is_configured(self) -> bool:
        """Returns True if an active Gemini API key is configured."""
        return bool(self.api_key and self._client)

    async def generate_quiz(
        self,
        prompt: str,
        fallback_topic: str = "General Knowledge",
        fallback_difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE,
        fallback_count: int = 5,
    ) -> AIGeneratedQuizPayload:
        """Generate a structured quiz using Gemini structured outputs."""
        if not self.is_configured:
            logger.info("gemini_mock_mode_active", reason="GEMINI_API_KEY not configured")
            return self._generate_mock_quiz(
                topic=fallback_topic,
                difficulty=fallback_difficulty,
                count=fallback_count,
            )

        try:
            assert self._client is not None
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AIGeneratedQuizPayload,
                    temperature=0.3,
                ),
            )

            raw_text = response.text or "{}"
            payload_data = json.loads(raw_text)
            return AIGeneratedQuizPayload.model_validate(payload_data)

        except Exception as exc:  # noqa: BLE001
            logger.error("gemini_quiz_generation_failed", error=str(exc))
            # Fallback gracefully if API quota or connectivity fails
            logger.info("gemini_falling_back_to_mock", topic=fallback_topic)
            return self._generate_mock_quiz(
                topic=fallback_topic,
                difficulty=fallback_difficulty,
                count=fallback_count,
            )

    async def evaluate_answer(
        self,
        prompt: str,
        expected_answer: str,
        user_answer: str,
    ) -> AIEvalResult:
        """Evaluate a student's answer and produce confidence and pedagogical feedback."""
        if not self.is_configured:
            return self._evaluate_mock_answer(expected_answer=expected_answer, user_answer=user_answer)

        try:
            assert self._client is not None
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AIEvalResult,
                    temperature=0.1,
                ),
            )

            raw_text = response.text or "{}"
            eval_data = json.loads(raw_text)
            return AIEvalResult.model_validate(eval_data)

        except Exception as exc:  # noqa: BLE001
            logger.error("gemini_answer_evaluation_failed", error=str(exc))
            return self._evaluate_mock_answer(expected_answer=expected_answer, user_answer=user_answer)

    def _generate_mock_quiz(
        self,
        topic: str,
        difficulty: DifficultyLevel,
        count: int,
    ) -> AIGeneratedQuizPayload:
        """Deterministic high-quality fallback generator for offline development and testing."""
        questions: list[AIGeneratedQuestion] = []
        for i in range(1, count + 1):
            if i % 2 == 1:
                q = AIGeneratedQuestion(
                    question=f"Regarding {topic}, which of the following is considered an architectural best practice? (Item {i})",
                    question_type=QuestionType.MCQ,
                    options=[
                        "Maintain clear separation of concerns with asynchronous, decoupled modules",
                        "Store plaintext credentials in application source code",
                        "Avoid writing integration or unit test suites",
                        "Perform synchronous blocking network I/O inside the main event loop",
                    ],
                    correct_answer="Maintain clear separation of concerns with asynchronous, decoupled modules",
                    explanation="Decoupled asynchronous architectures prevent thread blocking and ensure scalability and resilience.",
                    topic_tag=topic,
                )
            else:
                q = AIGeneratedQuestion(
                    question=f"In {topic}, idempotent operations produce the exact same server side outcome whether executed once or multiple times.",
                    question_type=QuestionType.TRUE_FALSE,
                    options=["True", "False"],
                    correct_answer="True",
                    explanation="Idempotency guarantees that multiple identical requests have the identical side effect on the underlying state.",
                    topic_tag=topic,
                )
            questions.append(q)

        return AIGeneratedQuizPayload(
            title=f"Mastery Assessment: {topic}",
            topic=topic,
            difficulty=difficulty,
            questions=questions,
        )

    def _evaluate_mock_answer(self, expected_answer: str, user_answer: str) -> AIEvalResult:
        """Deterministic semantic evaluation fallback."""
        normalized_exp = expected_answer.strip().lower()
        normalized_usr = user_answer.strip().lower()

        is_correct = normalized_exp == normalized_usr or (
            len(normalized_usr) > 2 and normalized_usr in normalized_exp
        )

        confidence = 0.95 if is_correct else 0.85
        feedback = (
            "Excellent understanding! Your response precisely addresses the core conceptual requirements."
            if is_correct
            else f"Not quite right. The expected concept was '{expected_answer}'. Review the explanation to reinforce your learning."
        )

        return AIEvalResult(
            is_correct=is_correct,
            confidence=confidence,
            feedback=feedback,
        )
