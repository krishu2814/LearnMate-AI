import asyncio
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal, engine
from app.models.course import Course, DifficultyLevel, Lesson, Module
from app.models.quiz import QuestionType, Quiz, QuizQuestion


async def seed_quizzes_if_needed(session) -> None:
    existing_quiz = await session.execute(select(Quiz).limit(1))
    if existing_quiz.scalar_one_or_none():
        print("Database already contains quizzes. Skipping quiz seed.")
        return

    first_lesson = (await session.execute(select(Lesson).order_by(Lesson.position).limit(1))).scalar_one_or_none()
    lesson_id = first_lesson.id if first_lesson else None

    quiz1 = Quiz(
        title="Python Concurrency & Async Architecture Quiz",
        topic="Backend Development",
        difficulty=DifficultyLevel.INTERMEDIATE,
        lesson_id=lesson_id,
        question_count=3,
    )
    session.add(quiz1)
    await session.flush()

    q1 = QuizQuestion(
        quiz_id=quiz1.id,
        question="Which keyword in Python is used to declare an asynchronous function?",
        question_type=QuestionType.MCQ,
        options=["async def", "def", "await def", "thread def"],
        correct_answer="async def",
        explanation="In modern Python, native coroutines are defined with the 'async def' syntax.",
        position=1,
    )
    q2 = QuizQuestion(
        quiz_id=quiz1.id,
        question="The asyncio event loop runs across multiple operating system threads simultaneously by default.",
        question_type=QuestionType.TRUE_FALSE,
        options=["True", "False"],
        correct_answer="False",
        explanation="Python's asyncio event loop is single-threaded and relies on cooperative multitasking.",
        position=2,
    )
    q3 = QuizQuestion(
        quiz_id=quiz1.id,
        question="Which FastAPI parameter dependency is used to inject an asynchronous database session?",
        question_type=QuestionType.MCQ,
        options=["Depends", "Query", "Header", "Security"],
        correct_answer="Depends",
        explanation="FastAPI's Depends dependency injection system provides scoped resources like database sessions to route handlers.",
        position=3,
    )
    session.add_all([q1, q2, q3])
    await session.commit()
    print("Database seeded with sample Quiz and Questions!")


async def seed_database() -> None:
    print("Seeding database with production courses and lessons...")
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        existing_course = await session.execute(select(Course).limit(1))
        if existing_course.scalar_one_or_none():
            print("Database already contains course catalog. Skipping duplicate seed.")
            await seed_quizzes_if_needed(session)
            await engine.dispose()
            return

        # -------------------------------------------------------------
        # Course 1: Production Backend Engineering with Python & FastAPI
        # -------------------------------------------------------------
        backend_course = Course(
            title="Production Backend Engineering with Python & FastAPI",
            description="Master asynchronous Python, RESTful API design, ACID database patterns, and security architecture.",
            subject_tag="Backend Development",
            difficulty=DifficultyLevel.INTERMEDIATE,
            is_published=True,
        )
        session.add(backend_course)
        await session.flush()

        # Modules & Lessons for Course 1
        m1 = Module(
            course_id=backend_course.id,
            title="HTTP Architecture & Modern Async Python",
            position=1,
            summary="Understanding networking fundamentals, event loops, and non-blocking I/O.",
        )
        session.add(m1)
        await session.flush()

        l1_1 = Lesson(
            module_id=m1.id,
            title="How HTTP/1.1 and HTTP/2 Work Under the Hood",
            content="HTTP is an application layer request-response protocol. In this lesson, we study TCP handshakes, head-of-line blocking, pipelining, and multiplexing.",
            estimated_minutes=20,
            position=1,
        )
        l1_2 = Lesson(
            module_id=m1.id,
            title="Async Event Loops, Coroutines & Concurrency in Python",
            content="Deep dive into Python's asyncio module, task scheduling, cooperative multitasking, and avoiding blocking calls in the main thread.",
            estimated_minutes=25,
            position=2,
        )
        l1_3 = Lesson(
            module_id=m1.id,
            title="Designing Robust REST APIs with FastAPI & Pydantic v2",
            content="FastAPI leverages type hints for automatic validation, OpenAPI documentation, dependency injection, and high throughput.",
            estimated_minutes=30,
            position=3,
        )
        session.add_all([l1_1, l1_2, l1_3])

        m2 = Module(
            course_id=backend_course.id,
            title="Relational Databases, ACID & Connection Pooling",
            position=2,
            summary="Designing normalized schemas, indexes, and high-concurrency ORM patterns.",
        )
        session.add(m2)
        await session.flush()

        l2_1 = Lesson(
            module_id=m2.id,
            title="Database Normalization, Indexes & Query Execution Plans",
            content="Learn B-Tree indexing, index selectivity, composite keys, and analyzing execution plans using EXPLAIN ANALYZE.",
            estimated_minutes=25,
            position=1,
        )
        l2_2 = Lesson(
            module_id=m2.id,
            title="SQLAlchemy 2.0 Async Engine & Connection Pooling",
            content="Configuring AsyncEngine with asyncpg/aiomysql, understanding QueuePool, connection timeouts, and transaction isolation levels.",
            estimated_minutes=30,
            position=2,
        )
        session.add_all([l2_1, l2_2])

        m3 = Module(
            course_id=backend_course.id,
            title="Authentication, Cryptography & Security Patterns",
            position=3,
            summary="Implementing OWASP-recommended security, Argon2id password hashing, and token rotation.",
        )
        session.add(m3)
        await session.flush()

        l3_1 = Lesson(
            module_id=m3.id,
            title="Argon2id Password Hashing vs Bcrypt",
            content="Why memory-hard hashing algorithms like Argon2id protect credentials against GPU and ASIC cracking attacks.",
            estimated_minutes=20,
            position=1,
        )
        l3_2 = Lesson(
            module_id=m3.id,
            title="JWT Access Tokens & Secure Refresh Token Rotation",
            content="Implementing short-lived stateless JWTs combined with opaque refresh tokens stored as SHA-256 hashes to detect token reuse.",
            estimated_minutes=30,
            position=2,
        )
        session.add_all([l3_1, l3_2])

        # -------------------------------------------------------------
        # Course 2: Generative AI Engineering & RAG Systems
        # -------------------------------------------------------------
        ai_course = Course(
            title="Generative AI Engineering & RAG Systems",
            description="Build scalable AI learning systems with multi-model routing, vector databases, and semantic retrieval.",
            subject_tag="Artificial Intelligence",
            difficulty=DifficultyLevel.INTERMEDIATE,
            is_published=True,
        )
        session.add(ai_course)
        await session.flush()

        ai_m1 = Module(
            course_id=ai_course.id,
            title="LLM Routing & Structured Output Validation",
            position=1,
            summary="Controlling model outputs, cost optimization, and multi-model fallbacks.",
        )
        session.add(ai_m1)
        await session.flush()

        ai_l1_1 = Lesson(
            module_id=ai_m1.id,
            title="Multi-Model Routing: Cost vs Latency Optimization",
            content="Routing high-volume queries to fast models like Gemini Flash while reserving heavy reasoning and curriculum generation for Gemini Pro.",
            estimated_minutes=20,
            position=1,
        )
        ai_l1_2 = Lesson(
            module_id=ai_m1.id,
            title="Strict Structured Outputs with Pydantic v2",
            content="Constraining LLM responses to strict JSON schemas, catching parsing errors, and automated schema validation before persisting to DB.",
            estimated_minutes=25,
            position=2,
        )
        session.add_all([ai_l1_1, ai_l1_2])

        ai_m2 = Module(
            course_id=ai_course.id,
            title="Document Ingestion & Retrieval-Augmented Generation",
            position=2,
            summary="PDF processing, vector embeddings, Qdrant indexing, and grounded answers with citations.",
        )
        session.add(ai_m2)
        await session.flush()

        ai_l2_1 = Lesson(
            module_id=ai_m2.id,
            title="Recursive Text Chunking & Overlap Strategies",
            content="How chunk size affects context preservation and retrieval precision in document RAG pipelines.",
            estimated_minutes=25,
            position=1,
        )
        ai_l2_2 = Lesson(
            module_id=ai_m2.id,
            title="Qdrant Vector Database & Tenant Filter Isolation",
            content="Storing dense embeddings, Cosine similarity search, and enforcing user_id filters to guarantee data privacy.",
            estimated_minutes=30,
            position=2,
        )
        session.add_all([ai_l2_1, ai_l2_2])

        await session.commit()
        await seed_quizzes_if_needed(session)
        await engine.dispose()
        print("Database seeded successfully with 2 courses, 5 modules, and 11 lessons!")


if __name__ == "__main__":
    asyncio.run(seed_database())
