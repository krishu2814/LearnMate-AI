# LearnMate AI

LearnMate AI is a production-grade, AI-powered personalized learning platform backend built with FastAPI, SQLAlchemy 2.0, MySQL 8, Redis, Google Gemini, and modern asynchronous Python.

## Core Features

- **Authentication & Security:** Argon2id password hashing, JWT stateless access tokens, high-entropy opaque refresh tokens with automated token rotation and token-reuse attack detection.
- **AI Code Playground & Exercise Evaluator:** Automated architectural reviews, algorithmic time/space complexity analysis ($O(n)$ notation), style/anti-pattern audits (blocking event loops, bare excepts), refactored solutions, and tailored hands-on coding challenges with test specifications.
- **Adaptive Spaced Repetition (SRS) & Weakness Remediation:** SuperMemo SM-2 spaced repetition engine that automatically schedules questions missed in quizzes for spaced review, tracks topic weaknesses, and synthesizes targeted AI remediation assessments with Gemini.
- **AI Curriculum & Study Roadmap Generator:** Automatically synthesizes learner goals, target timelines, and daily study budgets into structured, multi-week learning paths grounded in catalog courses with milestone tracking and prior progress credit.
- **Socratic AI Tutor & Multi-Style Lesson Explainer:** Context-aware tutoring with multi-style pedagogical explanations (`beginner`/ELI5, `deep_dive`, `analogy`, `practical`) and interactive Socratic mentorship with conversational continuity.
- **AI Quiz Generation & Adaptive Assessment:** Automated curriculum-grounded or topic-based quiz generation with Gemini structured JSON output schemas, confidence scoring, and pedagogical feedback.
- **Course & Lesson Management:** Structured courses, modules, and lessons with estimated completion durations.
- **Personalized Learning Paths:** Custom learner goals, schedule allocation, and automated item completion synchronization.
- **Progress Tracking & Analytics:** Real-time lesson progress lifecycle (`not_started`, `in_progress`, `completed`), time tracking, and dashboard analytics.
- **Adaptive Quizzes & Scoring:** Immediate grading, question ordering, history tracking, and row-level ownership isolation.
- **Enterprise Observability & Health:** Health checks (`/health/live`, `/health/ready`), distributed tracing IDs (`X-Request-ID`), process latency (`X-Process-Time`), and structured JSON logging via structlog.

## Architecture & Technology Stack

- **Framework:** FastAPI
- **AI Engine:** Google Gemini (`google-genai` SDK with strict Pydantic JSON schema output and resilient mock fallback)
- **Database ORM:** SQLAlchemy 2.0 (Asyncio)
- **Database Engine:** MySQL 8 with connection pooling
- **Migrations:** Alembic
- **Caching & Rate Limiting:** Redis
- **Validation:** Pydantic v2 & Pydantic Settings
- **Testing:** Pytest & Pytest-Asyncio

## API Overview

### AI Code Playground & Exercise Evaluator (`/api/v1/code`)
- `POST /api/v1/code/review` - Submit code for architectural review, scoring, complexity evaluation, and refactored solution.
- `GET /api/v1/code/submissions` - List historical code submissions and review reports for authenticated learner.
- `GET /api/v1/code/submissions/{id}` - Retrieve detailed evaluation report with row-level ownership isolation.
- `POST /api/v1/code/exercises/generate` - Generate tailored coding challenges with test cases, boilerplate starter code, and progressive hints.

### Spaced Repetition & Weakness Remediation (`/api/v1/srs`)
- `GET /api/v1/srs/queue` - Retrieve questions due for review based on SM-2 intervals, with weak-topic analytics.
- `POST /api/v1/srs/items/{item_id}/review` - Submit a review answer, updating repetitions, ease factor, and next review date.
- `POST /api/v1/srs/remediation/generate-quiz` - Generate a targeted AI refresher quiz focusing on the student's specific misconceptions.

### AI Assessment & Learning (`/api/v1/ai`)
- `POST /api/v1/ai/learning-paths/generate` - Generate and persist a personalized learning roadmap with weekly milestones.
- `POST /api/v1/ai/lessons/{lesson_id}/explain` - Generate a multi-style lesson explanation (`beginner`, `deep_dive`, `analogy`, `practical`).
- `POST /api/v1/ai/tutor/chat` - Interactive Socratic tutor chat session with optional lesson grounding.
- `POST /api/v1/ai/quizzes/generate` - Generate an adaptive assessment quiz from topic or lesson content.
- `POST /api/v1/ai/quizzes/evaluate-answer` - Semantic evaluation with AI confidence score and feedback.

### Learning Management (`/api/v1`)
- `GET /api/v1/courses` - List published courses with difficulty and topic filters.
- `GET /api/v1/courses/{id}` - Retrieve course hierarchy with modules and lessons.
- `GET /api/v1/lessons/{id}` - Get lesson content and estimated duration.
- `PUT /api/v1/lessons/{id}/progress` - Update lesson progress lifecycle.
- `POST /api/v1/learning-paths` - Create a custom learning path.
- `GET /api/v1/learning-paths` - List user's learning paths.
- `GET /api/v1/learning-paths/{id}` - Get full path details and item completion stats.
- `GET /api/v1/progress` - Comprehensive learner progress dashboard.
- `GET /api/v1/quizzes` - List available assessment quizzes.
- `POST /api/v1/quizzes/{id}/attempts` - Submit quiz attempt and obtain instant scored results.

## Getting Started

### 1. Prerequisites
- Python 3.11+
- Docker & Docker Compose

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 3. Start Infrastructure
```bash
docker compose up -d mysql redis
```

### 4. Database Migrations & Seeding
```bash
alembic upgrade head
python scripts/seed_db.py
```

### 5. Run API Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Run Test Suite
```bash
pytest
```
