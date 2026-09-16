"""Database operations. Routers stay thin; business rules live here."""
from typing import Any, Literal

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .errors import ConflictError
from .models import Book
from .schemas import BookCreate

SortField = Literal["id", "title", "author", "published_year", "created_at"]
SortOrder = Literal["asc", "desc"]


def get_book(db: Session, book_id: int) -> Book | None:
    return db.get(Book, book_id)


def list_books(
    db: Session,
    *,
    limit: int,
    offset: int,
    author: str | None = None,
    genre: str | None = None,
    available: bool | None = None,
    q: str | None = None,
    sort: SortField = "id",
    order: SortOrder = "asc",
) -> tuple[list[Book], int]:
    stmt = select(Book)
    if author:
        stmt = stmt.where(Book.author.icontains(author, autoescape=True))
    if genre:
        stmt = stmt.where(func.lower(Book.genre) == genre.lower())
    if available is not None:
        stmt = stmt.where(Book.available == available)
    if q:
        stmt = stmt.where(
            or_(Book.title.icontains(q, autoescape=True), Book.author.icontains(q, autoescape=True))
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    # `sort` is restricted to a whitelist by its Literal type, so getattr is safe.
    column = getattr(Book, sort)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), Book.id.asc())
    items = list(db.scalars(stmt.limit(limit).offset(offset)))
    return items, total


def _ensure_isbn_available(db: Session, isbn: str, exclude_id: int | None = None) -> None:
    stmt = select(Book.id).where(Book.isbn == isbn)
    if exclude_id is not None:
        stmt = stmt.where(Book.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise ConflictError(f"A book with ISBN {isbn} already exists", details={"field": "isbn"})


def _commit(db: Session) -> None:
    """Commit, converting a race-condition unique violation into a 409."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("The request conflicts with existing data") from exc


def create_book(db: Session, data: BookCreate) -> Book:
    _ensure_isbn_available(db, data.isbn)
    book = Book(**data.model_dump())
    db.add(book)
    _commit(db)
    db.refresh(book)
    return book


def update_book(db: Session, book: Book, changes: dict[str, Any]) -> Book:
    if "isbn" in changes and changes["isbn"] != book.isbn:
        _ensure_isbn_available(db, changes["isbn"], exclude_id=book.id)
    for field, value in changes.items():
        setattr(book, field, value)
    _commit(db)
    db.refresh(book)
    return book


def delete_book(db: Session, book: Book) -> None:
    db.delete(book)
    db.commit()
