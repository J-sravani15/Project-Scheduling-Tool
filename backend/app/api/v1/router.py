from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    projects,
    milestones,
    tasks,
    scheduling,
    faculty,
    students,
    notifications,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Identity"])
api_router.include_router(projects.router, prefix="/projects", tags=["Academic Projects"])
api_router.include_router(milestones.router, tags=["Academic Milestones"])
api_router.include_router(tasks.router, tags=["Tasks & Dependencies"])
api_router.include_router(scheduling.router, prefix="/projects", tags=["Scheduling Algorithms"])
api_router.include_router(faculty.router, prefix="/faculty", tags=["Faculty Guide Monitoring"])
api_router.include_router(students.router, prefix="/students", tags=["Student Accounts"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications & Alerts"])
