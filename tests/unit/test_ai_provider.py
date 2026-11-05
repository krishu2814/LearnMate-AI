import pytest

from app.ai.prompts.quiz_prompts import (
    build_answer_evaluation_prompt,
    build_quiz_generation_prompt,
)
from app.ai.providers.gemini import GeminiProvider
from app.models.course import DifficultyLevel
from app.models.quiz import QuestionType


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
