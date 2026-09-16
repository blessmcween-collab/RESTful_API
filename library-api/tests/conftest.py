import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


def make_isbn(prefix12: str) -> str:
    """Build a valid ISBN-13 from its first 12 digits."""
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(prefix12))
    return prefix12 + str((10 - total % 10) % 10)


@pytest.fixture()
def client():
    # Fresh in-memory database for every test, so tests never affect each other.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def book_payload():
    return {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "978-0132350884",
        "published_year": 2008,
        "pages": 464,
        "genre": "Software Engineering",
    }


@pytest.fixture()
def created_book(client, book_payload):
    response = client.post("/api/v1/books", json=book_payload)
    assert response.status_code == 201
    return response.json()
