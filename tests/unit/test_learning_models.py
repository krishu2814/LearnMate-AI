import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, DifficultyLevel, Lesson, Module
from app.models.learning_path import ItemType, LearningPath, LearningPathItem, PathStatus
from app.models.progress import LessonProgress, ProgressStatus
from app.models.user import User


@pytest.mark.asyncio
async def test_course_module_lesson_cascade(db_session: AsyncSession):
    course = Course(
        title="Test Backend Architecture",
        description="Comprehensive course testing models",
        subject_tag="Testing",
        difficulty=DifficultyLevel.BEGINNER,
    )
    db_session.add(course)
    await db_session.flush()

    module = Module(
        course_id=course.id,
        title="Module 1: Introduction",
        position=1,
    )
    db_session.add(module)
    await db_session.flush()

    lesson = Lesson(
        module_id=module.id,
        title="Lesson 1.1: Getting Started",
        content="Welcome to LearnMate AI testing.",
        estimated_minutes=15,
        position=1,
    )
    db_session.add(lesson)
    await db_session.commit()

    # Query course and check eager loading of modules and lessons
    stmt = select(Course).where(Course.id == course.id)
    result = await db_session.execute(stmt)
    queried_course = result.scalar_one_or_none()

    assert queried_course is not None
    assert len(queried_course.modules) == 1
    assert queried_course.modules[0].title == "Module 1: Introduction"
    assert len(queried_course.modules[0].lessons) == 1
    assert queried_course.modules[0].lessons[0].title == "Lesson 1.1: Getting Started"

    # Clean up (cascade delete should remove modules and lessons)
    await db_session.delete(queried_course)
    await db_session.commit()


@pytest.mark.asyncio
async def test_learning_path_and_items(db_session: AsyncSession):
    user = User(
        email=f"path_user_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hashed_pw",
    )
    db_session.add(user)
    await db_session.flush()

    course = Course(
        title="Course for Path",
        description="Testing paths",
        subject_tag="Paths",
    )
    db_session.add(course)
    await db_session.flush()

    module = Module(course_id=course.id, title="Module A", position=1)
    db_session.add(module)
    await db_session.flush()

    lesson = Lesson(module_id=module.id, title="Lesson A.1", content="Content", position=1)
    db_session.add(lesson)
    await db_session.flush()

    path = LearningPath(
        user_id=user.id,
        title="30-Day Backend Track",
        goal="Become a backend engineer",
        status=PathStatus.ACTIVE,
        total_days=30,
        daily_minutes=45,
    )
    db_session.add(path)
    await db_session.flush()

    path_item = LearningPathItem(
        learning_path_id=path.id,
        lesson_id=lesson.id,
        position=1,
        item_type=ItemType.LESSON,
        is_optional=False,
    )
    db_session.add(path_item)
    await db_session.commit()

    # Query learning path with items
    stmt = select(LearningPath).where(LearningPath.id == path.id)
    result = await db_session.execute(stmt)
    queried_path = result.scalar_one_or_none()

    assert queried_path is not None
    assert len(queried_path.items) == 1
    assert queried_path.items[0].lesson.title == "Lesson A.1"
    assert queried_path.items[0].is_completed is False

    # Clean up
    await db_session.delete(user)
    await db_session.delete(course)
    await db_session.commit()


@pytest.mark.asyncio
async def test_lesson_progress_lifecycle(db_session: AsyncSession):
    user = User(
        email=f"prog_user_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hashed_pw",
    )
    db_session.add(user)
    await db_session.flush()

    course = Course(title="Prog Course", description="Test", subject_tag="Prog")
    db_session.add(course)
    await db_session.flush()

    module = Module(course_id=course.id, title="Prog Module", position=1)
    db_session.add(module)
    await db_session.flush()

    lesson = Lesson(module_id=module.id, title="Prog Lesson", content="Text", position=1)
    db_session.add(lesson)
    await db_session.flush()

    # Initial progress
    progress = LessonProgress(user_id=user.id, lesson_id=lesson.id)
    assert progress.status == ProgressStatus.NOT_STARTED
    assert progress.time_spent_seconds == 0
    assert progress.started_at is None
    assert progress.completed_at is None

    # Transition to started
    progress.mark_started()
    assert progress.status == ProgressStatus.IN_PROGRESS
    assert progress.started_at is not None

    # Transition to completed
    progress.mark_completed(additional_seconds=600)
    assert progress.status == ProgressStatus.COMPLETED
    assert progress.completed_at is not None
    assert progress.time_spent_seconds == 600

    db_session.add(progress)
    await db_session.commit()

    # Query progress
    stmt = select(LessonProgress).where(
        LessonProgress.user_id == user.id,
        LessonProgress.lesson_id == lesson.id,
    )
    result = await db_session.execute(stmt)
    saved_prog = result.scalar_one_or_none()
    assert saved_prog is not None
    assert saved_prog.status == ProgressStatus.COMPLETED

    # Clean up
    await db_session.delete(user)
    await db_session.delete(course)
    await db_session.commit()
