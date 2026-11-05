import json

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.logging import logger
from app.models.course import DifficultyLevel
from app.models.quiz import QuestionType
from app.schemas.ai import (
    AIEvalResult,
    AIExplanationStyle,
    AIGeneratedCurriculumPayload,
    AIGeneratedQuestion,
    AIGeneratedQuizPayload,
    AILessonExplanationPayload,
    AITutorChatPayload,
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
            return self._evaluate_mock_answer(
                expected_answer=expected_answer, user_answer=user_answer
            )

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
            return self._evaluate_mock_answer(
                expected_answer=expected_answer, user_answer=user_answer
            )

    async def generate_curriculum(
        self,
        prompt: str,
        goal: str,
        available_lesson_ids: list[str],
        total_days: int = 30,
        daily_minutes: int = 60,
    ) -> AIGeneratedCurriculumPayload:
        """Generate a personalized curriculum roadmap using Gemini structured outputs."""
        if not self.is_configured:
            return self._generate_mock_curriculum(
                goal=goal,
                available_lesson_ids=available_lesson_ids,
                total_days=total_days,
                daily_minutes=daily_minutes,
            )

        try:
            assert self._client is not None
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AIGeneratedCurriculumPayload,
                    temperature=0.2,
                ),
            )

            raw_text = response.text or "{}"
            payload_data = json.loads(raw_text)
            return AIGeneratedCurriculumPayload.model_validate(payload_data)

        except Exception as exc:  # noqa: BLE001
            logger.error("gemini_curriculum_generation_failed", error=str(exc))
            return self._generate_mock_curriculum(
                goal=goal,
                available_lesson_ids=available_lesson_ids,
                total_days=total_days,
                daily_minutes=daily_minutes,
            )

    async def explain_lesson(
        self,
        prompt: str,
        lesson_title: str,
        style: AIExplanationStyle,
    ) -> AILessonExplanationPayload:
        """Generate multi-style pedagogical lesson explanations."""
        if not self.is_configured:
            return self._explain_mock_lesson(lesson_title=lesson_title, style=style)

        try:
            assert self._client is not None
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AILessonExplanationPayload,
                    temperature=0.2,
                ),
            )

            raw_text = response.text or "{}"
            payload_data = json.loads(raw_text)
            return AILessonExplanationPayload.model_validate(payload_data)

        except Exception as exc:  # noqa: BLE001
            logger.error("gemini_lesson_explanation_failed", error=str(exc))
            return self._explain_mock_lesson(lesson_title=lesson_title, style=style)

    async def tutor_chat(
        self,
        prompt: str,
        user_message: str,
    ) -> AITutorChatPayload:
        """Generate Socratic interactive tutor guidance."""
        if not self.is_configured:
            return self._mock_tutor_chat(user_message=user_message)

        try:
            assert self._client is not None
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AITutorChatPayload,
                    temperature=0.4,
                ),
            )

            raw_text = response.text or "{}"
            payload_data = json.loads(raw_text)
            return AITutorChatPayload.model_validate(payload_data)

        except Exception as exc:  # noqa: BLE001
            logger.error("gemini_tutor_chat_failed", error=str(exc))
            return self._mock_tutor_chat(user_message=user_message)

    # =========================================================================
    # Fallback Generators for Offline Dev and Unit Testing
    # =========================================================================

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

    def _generate_mock_curriculum(
        self,
        goal: str,
        available_lesson_ids: list[str],
        total_days: int = 30,
        daily_minutes: int = 60,
    ) -> AIGeneratedCurriculumPayload:
        """Deterministic fallback curriculum generator."""
        # Select up to 6 available lessons from catalog
        selected = available_lesson_ids[:6] if available_lesson_ids else []
        weeks = max(1, round(total_days / 7))
        milestones = [
            f"Week 1: Core Foundations & Architectural Fundamentals for {goal[:40]}",
            "Week 2: Deep Dive into Asynchronous Patterns & State Management",
            "Week 3: Practical Implementation, Edge Cases & Error Handling",
            "Week 4: Comprehensive Project Integration, Testing & Review",
        ][:weeks]
        if not milestones:
            milestones = [f"Phase 1: Mastery Plan for {goal}"]

        return AIGeneratedCurriculumPayload(
            title=f"Curated Roadmap: {goal[:60]}",
            overview=(
                f"This personalized study path is strategically calibrated for a {total_days}-day commitment "
                f"at {daily_minutes} minutes/day to systematically achieve: {goal}."
            ),
            weekly_milestones=milestones,
            selected_lesson_ids=selected,
            study_tips=[
                "Code actively alongside each lesson rather than passively reading.",
                "Reinforce key concepts using spaced repetition and self-quizzing.",
                "Build a small end-to-end prototype applying each milestone's learnings.",
            ],
        )

    def _explain_mock_lesson(
        self,
        lesson_title: str,
        style: AIExplanationStyle,
    ) -> AILessonExplanationPayload:
        """Deterministic fallback lesson explanation."""
        style_intros = {
            AIExplanationStyle.BEGINNER: (
                f"Think of '{lesson_title}' like a well-organized team where everyone has a specific responsibility. "
                "Instead of one person doing everything slowly, tasks are shared efficiently."
            ),
            AIExplanationStyle.DEEP_DIVE: (
                f"Under the hood, '{lesson_title}' addresses critical system bottlenecks. "
                "By decoupling I/O wait times and managing state transitions cleanly, execution throughput increases."
            ),
            AIExplanationStyle.ANALOGY: (
                f"Imagine '{lesson_title}' as a busy restaurant kitchen. If the chef had to wait by the stove for water to boil, "
                "no other dish would get prepped. Instead, they start prepping vegetables while the water heats up."
            ),
            AIExplanationStyle.PRACTICAL: (
                f"In production environments, '{lesson_title}' prevents connection starvation, "
                "ensuring fast response latencies even under sudden traffic spikes."
            ),
        }

        intro = style_intros.get(style, style_intros[AIExplanationStyle.DEEP_DIVE])

        return AILessonExplanationPayload(
            explanation=(
                f"### Understanding {lesson_title}\n\n"
                f"{intro}\n\n"
                "Key mechanisms to master:\n"
                "1. **Non-blocking Operations:** Allow the execution thread to process concurrent requests.\n"
                "2. **State Encapsulation:** Maintain invariant integrity and prevent race conditions.\n"
                "3. **Idempotence & Safety:** Ensure network retries do not corrupt persistent data."
            ),
            key_takeaways=[
                f"Always structure {lesson_title} components with decoupled responsibilities.",
                "Favor asynchronous non-blocking patterns over thread-blocking operations.",
                "Include structured logging and metrics for observability.",
            ],
            code_example=(
                "# Example illustrating non-blocking asynchronous execution\n"
                "import asyncio\n\n"
                "async def fetch_data(task_id: int) -> dict:\n"
                "    await asyncio.sleep(0.05)  # Non-blocking simulation\n"
                "    return {'task_id': task_id, 'status': 'completed'}\n\n"
                "async def main():\n"
                "    results = await asyncio.gather(*(fetch_data(i) for i in range(5)))\n"
                "    print(results)\n"
            ),
            suggested_followups=[
                f"How would you handle backpressure or rate limits when scaling '{lesson_title}'?",
                "What database transaction isolation level is appropriate for these updates?",
                "How can you write isolated unit tests without hitting live network services?",
            ],
        )

    def _mock_tutor_chat(self, user_message: str) -> AITutorChatPayload:
        """Deterministic fallback Socratic tutor conversation."""
        return AITutorChatPayload(
            reply=(
                f"That's a very perceptive question regarding '{user_message.strip()}'. "
                "When building distributed backend applications, separating asynchronous I/O from CPU-bound computation "
                "is vital. If a database query or network call blocks the main thread, all concurrent requests stall."
            ),
            socratic_question=(
                "What do you think happens to incoming client connections if an async route calls a synchronous time.sleep() instead of await asyncio.sleep()?"
            ),
            suggested_topics=[
                "Event Loop Mechanics & Cooperative Multitasking",
                "Connection Pooling and QueuePool Management",
                "Stateless Authentication and Token Rotation",
            ],
        )
