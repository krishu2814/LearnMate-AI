import uuid

import pytest

from app.ai.prompts.code_prompts import (
    build_code_review_prompt,
    build_exercise_generation_prompt,
)
from app.ai.providers.gemini import GeminiProvider
from app.models.code_submission import CodeSubmission
from app.models.course import DifficultyLevel


def test_code_submission_defaults():
    user_id = str(uuid.uuid4())

    submission = CodeSubmission(
        user_id=user_id,
        title="Two Sum Algorithm",
        language="python",
        source_code="def two_sum(nums, target): return []",
        score=92,
        is_passed=True,
        time_complexity="O(n)",
        space_complexity="O(n)",
        review_summary="Clean hash-map approach with optimal time complexity.",
        strengths=["Optimal O(n) lookup time", "Clean variable names"],
        issues=[],
        refactored_code=None,
    )

    assert submission.user_id == user_id
    assert submission.title == "Two Sum Algorithm"
    assert submission.language == "python"
    assert submission.score == 92
    assert submission.is_passed is True
    assert submission.time_complexity == "O(n)"
    assert submission.space_complexity == "O(n)"
    assert submission.created_at is None
    assert "Two Sum Algorithm" in repr(submission)
    assert "score=92" in repr(submission)


def test_build_code_review_prompt():
    prompt = build_code_review_prompt(
        title="Fibonacci Memoization",
        language="python",
        source_code="def fib(n, memo={}): ...",
        problem_description="Compute nth Fibonacci number in linear time",
        lesson_title="Dynamic Programming Intro",
        lesson_content="Memoization caches recursive subproblem results.",
    )

    assert "Fibonacci Memoization" in prompt
    assert "python" in prompt
    assert "def fib(n, memo={})" in prompt
    assert "Dynamic Programming Intro" in prompt
    assert "Memoization caches recursive" in prompt


def test_build_exercise_generation_prompt():
    prompt = build_exercise_generation_prompt(
        topic="Binary Search Trees",
        difficulty=DifficultyLevel.ADVANCED,
        lesson_title="Tree Balancing",
        lesson_content="AVL and Red-Black trees maintain logarithmic height.",
        custom_instructions="Include edge cases for single-node trees",
    )

    assert "Binary Search Trees" in prompt
    assert "ADVANCED" in prompt
    assert "Tree Balancing" in prompt
    assert "AVL and Red-Black trees" in prompt
    assert "Include edge cases for single-node trees" in prompt


@pytest.mark.asyncio
async def test_gemini_provider_mock_code_review():
    provider = GeminiProvider(api_key=None)

    # 1. Clean code
    clean_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    res_clean = await provider.review_code(
        prompt="review",
        source_code=clean_code,
        language="python",
    )
    assert res_clean.score >= 80
    assert res_clean.is_passed is True
    assert res_clean.time_complexity is not None
    assert res_clean.space_complexity is not None
    assert len(res_clean.strengths) >= 1

    # 2. Flawed code (sleep in loop)
    flawed_code = "import time\nwhile True:\n    time.sleep(1)\n"
    res_flawed = await provider.review_code(
        prompt="review",
        source_code=flawed_code,
        language="python",
    )
    assert res_flawed.score < 80
    assert res_flawed.is_passed is False
    assert len(res_flawed.issues) >= 1
    assert any(i.severity.value in ["warning", "critical"] for i in res_flawed.issues)
    assert res_flawed.refactored_code is not None


@pytest.mark.asyncio
async def test_gemini_provider_mock_exercise_generation():
    provider = GeminiProvider(api_key=None)

    exercise = await provider.generate_exercise(
        prompt="exercise",
        topic="Asynchronous Queue Processing",
        difficulty=DifficultyLevel.ADVANCED,
    )

    assert "Asynchronous Queue Processing" in exercise.title or "Challenge" in exercise.title
    assert len(exercise.description) > 0
    assert exercise.difficulty == DifficultyLevel.ADVANCED
    assert len(exercise.starter_code) > 0
    assert len(exercise.test_cases) >= 2
    assert len(exercise.hints) >= 2
