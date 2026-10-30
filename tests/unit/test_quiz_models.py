import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import DifficultyLevel
from app.models.quiz import QuestionType, Quiz, QuizAnswer, QuizAttempt, QuizQuestion
from app.models.user import User


@pytest.mark.asyncio
async def test_quiz_and_questions_cascade(db_session: AsyncSession):
    quiz = Quiz(
        title="Unit Test Python Quiz",
        topic="Python Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_count=2,
    )
    db_session.add(quiz)
    await db_session.flush()

    q1 = QuizQuestion(
        quiz_id=quiz.id,
        question="What is the result of 2 + 2?",
        question_type=QuestionType.MCQ,
        options=["3", "4", "5"],
        correct_answer="4",
        explanation="2 + 2 equals 4.",
        position=1,
    )
    q2 = QuizQuestion(
        quiz_id=quiz.id,
        question="Python is a compiled language.",
        question_type=QuestionType.TRUE_FALSE,
        options=["True", "False"],
        correct_answer="False",
        explanation="Python is an interpreted language.",
        position=2,
    )
    db_session.add_all([q1, q2])
    await db_session.commit()

    # Verify retrieval
    res = await db_session.execute(select(Quiz).where(Quiz.id == quiz.id))
    retrieved_quiz = res.scalar_one()
    assert len(retrieved_quiz.questions) == 2
    assert retrieved_quiz.questions[0].position == 1
    assert retrieved_quiz.questions[0].correct_answer == "4"

    # Cascade delete quiz
    await db_session.delete(retrieved_quiz)
    await db_session.commit()

    # Questions should be cascade deleted
    questions_res = await db_session.execute(
        select(QuizQuestion).where(QuizQuestion.quiz_id == quiz.id)
    )
    assert len(questions_res.scalars().all()) == 0


@pytest.mark.asyncio
async def test_quiz_attempt_and_answer_lifecycle(db_session: AsyncSession):
    import uuid
    user = User(
        email=f"quiz_unit_test_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="hashed_pwd",
        full_name="Quiz Tester",
    )
    db_session.add(user)
    await db_session.flush()

    quiz = Quiz(
        title="Scoring Test Quiz",
        topic="Testing",
        difficulty=DifficultyLevel.BEGINNER,
        question_count=1,
    )
    db_session.add(quiz)
    await db_session.flush()

    question = QuizQuestion(
        quiz_id=quiz.id,
        question="Is unit testing important?",
        question_type=QuestionType.TRUE_FALSE,
        options=["True", "False"],
        correct_answer="True",
        position=1,
    )
    db_session.add(question)
    await db_session.flush()

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user.id,
        score=100.0,
        total_questions=1,
        correct_count=1,
        time_seconds=30,
    )
    db_session.add(attempt)
    await db_session.flush()

    answer = QuizAnswer(
        attempt_id=attempt.id,
        question_id=question.id,
        user_answer="True",
        is_correct=True,
    )
    db_session.add(answer)
    await db_session.commit()

    # Query attempt
    attempt_res = await db_session.execute(
        select(QuizAttempt).where(QuizAttempt.id == attempt.id)
    )
    retrieved_attempt = attempt_res.scalar_one()
    assert retrieved_attempt.score == 100.0
    assert retrieved_attempt.correct_count == 1
    assert len(retrieved_attempt.answers) == 1
    assert retrieved_attempt.answers[0].is_correct is True

    # Cleanup
    await db_session.delete(user)
    await db_session.delete(quiz)
    await db_session.commit()
