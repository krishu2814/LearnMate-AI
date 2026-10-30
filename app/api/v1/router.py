from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.courses import router as courses_router
from app.api.v1.learning_paths import router as learning_paths_router
from app.api.v1.lessons import router as lessons_router
from app.api.v1.progress import router as progress_router
from app.api.v1.quizzes import router as quizzes_router
from app.api.v1.users import router as users_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(courses_router)
api_v1_router.include_router(learning_paths_router)
api_v1_router.include_router(lessons_router)
api_v1_router.include_router(progress_router)
api_v1_router.include_router(quizzes_router)
