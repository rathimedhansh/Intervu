from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401 — registers models on Base before create_all
from app.api.routes import auth, dashboard, health, interviews, resumes
from app.core.config import settings
from app.db.base import Base
from app.db.database import engine
from app.db.migrate import run_lightweight_migrations

Base.metadata.create_all(bind=engine)
run_lightweight_migrations(engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api")
app.include_router(interviews.router, prefix="/api")
app.include_router(resumes.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


@app.get("/")
def root():
    return {"message": settings.app_name}
