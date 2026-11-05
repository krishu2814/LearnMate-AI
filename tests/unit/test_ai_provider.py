import pytest

from app.ai.prompts.path_prompts import build_curriculum_prompt
from app.ai.prompts.quiz_prompts import (
    build_answer_evaluation_prompt,
    build_quiz_generation_prompt,
)
from app.ai.prompts.tutor_prompts import (
    build_lesson_explanation_prompt,
    build_socratic_tutor_prompt,
)
from app.ai.providers.gemini import GeminiProvider
from app.models.course import DifficultyLevel
from app.models.quiz import QuestionType
from app.schemas.ai import AIExplanationStyle


def test_build_quiz_generation_prompt():
    prompt = build_quiz_generation_prompt(
        topic="FastAPI Dependencies",
        difficulty=DifficultyLevel.ADVANCED,
        num_questions=4,
        lesson_title="Advanced Dependency Injection",
        lesson_content="Depends(get_db) creates a scoped session for each request.",
        allowed_types=[QuestionType.MCQ],
        custom_instructions="Focus on yield cleanup semantics",
    )
    assert "FastAPI Dependencies" in prompt
    assert "ADVANCED" in prompt
    assert "Advanced Dependency Injection" in prompt
    assert "Depends(get_db)" in prompt
    assert "yield cleanup semantics" in prompt
    assert "mcq" in prompt


def test_build_answer_evaluation_prompt():
    prompt = build_answer_evaluation_prompt(
        question_text="What is HTTP 204?",
        question_type="mcq",
        correct_answer="No Content",
        user_answer="No Content",
        explanation="204 means request succeeded with no body returned.",
    )
    assert "What is HTTP 204?" in prompt
    assert "No Content" in prompt
    assert "no body returned" in prompt.lower()


def test_build_curriculum_prompt():
    catalog_summary = [
        {
            "course_title": "Backend Engineering",
            "module_title": "Async Python",
            "lesson_id": "les-1",
            "lesson_title": "Event Loops",
            "estimated_minutes": 20,
        }
    ]
    prompt = build_curriculum_prompt(
        goal="Master Distributed Systems",
        difficulty=DifficultyLevel.ADVANCED,
        total_days=45,
        daily_minutes=45,
        catalog_summary=catalog_summary,
        custom_focus="Consensus algorithms & Raft",
    )
    assert "Master Distributed Systems" in prompt
    assert "ADVANCED" in prompt
    assert "45 total days @ 45 minutes/day" in prompt
    assert "Consensus algorithms & Raft" in prompt
    assert "les-1" in prompt
    assert "Event Loops" in prompt


def test_build_lesson_explanation_and_socratic_prompts():
    explain_prompt = build_lesson_explanation_prompt(
        lesson_title="Database Indexing",
        lesson_content="B-Trees organize keys into hierarchical pages.",
        style="analogy",
        focus_question="Why not use hash indexes everywhere?",
    )
    assert "Database Indexing" in explain_prompt
    assert "ANALOGY" in explain_prompt
    assert "relatable real-world analogy" in explain_prompt
    assert "Why not use hash indexes everywhere?" in explain_prompt

    socratic_prompt = build_socratic_tutor_prompt(
        message="Why did my test fail?",
        lesson_title="Async Loops",
        lesson_content="Asyncio tasks execute cooperatively.",
        history=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Welcome!"},
        ],
    )
    assert "Why did my test fail?" in socratic_prompt
    assert "Async Loops" in socratic_prompt
    assert "Student: Hello" in socratic_prompt


@pytest.mark.asyncio
async def test_gemini_provider_mock_quiz_generation():
    provider = GeminiProvider(api_key=None)
    assert provider.is_configured is False

    quiz_payload = await provider.generate_quiz(
        prompt="Generate quiz",
        fallback_topic="PostgreSQL Performance",
        fallback_difficulty=DifficultyLevel.INTERMEDIATE,
        fallback_count=4,
    )
    assert quiz_payload.topic == "PostgreSQL Performance"
    assert quiz_payload.difficulty == DifficultyLevel.INTERMEDIATE
    assert len(quiz_payload.questions) == 4

    for q in quiz_payload.questions:
        assert q.question_type in [QuestionType.MCQ, QuestionType.TRUE_FALSE]
        assert q.correct_answer in q.options if q.options else True
        assert len(q.explanation) > 0


@pytest.mark.asyncio
async def test_gemini_provider_mock_answer_evaluation():
    provider = GeminiProvider(api_key=None)

    # Correct match
    result_correct = await provider.evaluate_answer(
        prompt="evaluate",
        expected_answer="FastAPI",
        user_answer="fastapi",
    )
    assert result_correct.is_correct is True
    assert result_correct.confidence >= 0.9
    assert "excellent" in result_correct.feedback.lower()

    # Incorrect match
    result_incorrect = await provider.evaluate_answer(
        prompt="evaluate",
        expected_answer="FastAPI",
        user_answer="Django",
    )
    assert result_incorrect.is_correct is False
    assert "not quite right" in result_incorrect.feedback.lower()


@pytest.mark.asyncio
async def test_gemini_provider_mock_curriculum_generation():
    provider = GeminiProvider(api_key=None)
    payload = await provider.generate_curriculum(
        prompt="plan",
        goal="Full Stack FastAPI",
        available_lesson_ids=["l1", "l2", "l3", "l4"],
        total_days=28,
        daily_minutes=60,
    )
    assert "Full Stack FastAPI" in payload.title or "Curated Roadmap" in payload.title
    assert len(payload.weekly_milestones) >= 1
    assert payload.selected_lesson_ids == ["l1", "l2", "l3", "l4"]
    assert len(payload.study_tips) >= 1


@pytest.mark.asyncio
async def test_gemini_provider_mock_lesson_explanation():
    provider = GeminiProvider(api_key=None)
    for style in [
        AIExplanationStyle.BEGINNER,
        AIExplanationStyle.DEEP_DIVE,
        AIExplanationStyle.ANALOGY,
        AIExplanationStyle.PRACTICAL,
    ]:
        res = await provider.explain_lesson(
            prompt="explain",
            lesson_title="Event Loop Mechanics",
            style=style,
        )
        assert len(res.explanation) > 0
        assert len(res.key_takeaways) >= 2
        assert res.code_example is not None
        assert len(res.suggested_followups) >= 1


@pytest.mark.asyncio
async def test_gemini_provider_mock_tutor_chat():
    provider = GeminiProvider(api_key=None)
    res = await provider.tutor_chat(
        prompt="chat",
        user_message="How does connection pooling work?",
    )
    assert len(res.reply) > 0
    assert res.socratic_question is not None
    assert len(res.suggested_topics) >= 1
