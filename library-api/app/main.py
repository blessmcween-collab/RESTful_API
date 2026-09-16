"""Application entry point.

Run with:  uvicorn app.main:app --reload
Docs at:   http://127.0.0.1:8000/docs  (Swagger UI)  and  /redoc  (ReDoc)
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from .database import Base, engine
from .errors import register_exception_handlers
from .routers import books
from .routers.books import DB

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup. (A production app would use Alembic migrations.)
    Base.metadata.create_all(bind=engine)
    yield


DESCRIPTION = """
A RESTful API for managing a library's book catalogue.

**Features**
* Full CRUD on `/api/v1/books`: create, list, read, replace, partially update, delete
* Input validation: lengths, ranges, ISBN-13 check digit, rejection of unknown fields
* Pagination, filtering, search and sorting on the list endpoint
* Consistent JSON error format: `{"error": {"code", "message", "details"}}`
"""

app = FastAPI(
    title="Library Books API",
    version="1.0.0",
    description=DESCRIPTION,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Books", "description": "Create, read, update and delete books"},
        {"name": "System", "description": "Service health"},
    ],
)

register_exception_handlers(app)
app.include_router(books.router)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "name": app.title,
        "version": app.version,
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
    }


@app.get("/health", tags=["System"], summary="Health check")
def health(db: DB) -> dict[str, str]:
    """Confirms the API is running and the database is reachable."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
