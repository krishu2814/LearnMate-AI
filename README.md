# LearnMate AI

LearnMate AI is a production-grade, AI-powered personalized learning platform backend built with FastAPI, SQLAlchemy 2.0, MySQL 8, Redis, and modern asynchronous Python.

## Core Features

- **Authentication & Security:** Argon2id password hashing, JWT stateless access tokens, high-entropy opaque refresh tokens with automated token rotation and token-reuse attack detection.
- **Course & Lesson Management:** Structured courses, modules, and lessons with estimated completion durations.
- **Personalized Learning Paths:** Custom learner goals, schedule allocation, and automated item completion synchronization.
- **Progress Tracking & Analytics:** Real-time lesson progress lifecycle (`not_started`, `in_progress`, `completed`), time tracking, and dashboard analytics.
- **Adaptive Quizzes:** Automated scoring, question ordering, history tracking, and row-level ownership isolation.
- **Enterprise Observability & Health:** Health checks (`/health/live`, `/health/ready`), distributed tracing IDs (`X-Request-ID`), process latency (`X-Process-Time`), and structured JSON logging via structlog.

## Architecture & Technology Stack

- **Framework:** FastAPI
- **Database ORM:** SQLAlchemy 2.0 (Asyncio)
- **Database Engine:** MySQL 8 with connection pooling
- **Migrations:** Alembic
- **Caching & Rate Limiting:** Redis
- **Validation:** Pydantic v2 & Pydantic Settings
- **Testing:** Pytest & Pytest-Asyncio

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
