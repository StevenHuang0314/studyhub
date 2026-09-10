"""FastAPI application entrypoint.

Run locally with:  uvicorn app.main:app --reload
Interactive docs:  http://127.0.0.1:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, groups, notes, users

DESCRIPTION = """
**StudyHub** is a resource-sharing and study-group API for CS students.

* Post and rate course notes
* Search and filter by course, tag or keyword
* Create study groups and join the ones with space left

Auth is JWT bearer. Register at `/api/auth/register`, then hit **Authorize**
above with any email/password pair you created.
"""


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Fine for a SQLite-backed portfolio project. A production deployment
    # would run Alembic migrations here instead.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    description=DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(notes.router)
app.include_router(groups.router)
app.include_router(users.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
