"""/api/v1/books endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..errors import NotFoundError
from ..models import Book
from ..schemas import BookCreate, BookList, BookPatch, BookRead, BookUpdate, ErrorResponse

router = APIRouter(prefix="/api/v1/books", tags=["Books"])

DB = Annotated[Session, Depends(get_db)]
BookId = Annotated[int, Path(gt=0, description="Unique numeric ID of the book", examples=[1])]

R404 = {404: {"model": ErrorResponse, "description": "Book not found"}}
R409 = {409: {"model": ErrorResponse, "description": "ISBN already used by another book"}}
R422 = {422: {"model": ErrorResponse, "description": "Validation error"}}


def get_book_or_404(db: Session, book_id: int) -> Book:
    book = crud.get_book(db, book_id)
    if book is None:
        raise NotFoundError(f"Book with id {book_id} was not found")
    return book


@router.get("", response_model=BookList, summary="List books", responses=R422)
def list_books(
    db: DB,
    limit: Annotated[int, Query(ge=1, le=100, description="Max items to return")] = 20,
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
    author: Annotated[str | None, Query(max_length=100, description="Partial, case-insensitive match")] = None,
    genre: Annotated[str | None, Query(max_length=50, description="Exact, case-insensitive match")] = None,
    available: Annotated[bool | None, Query(description="Filter by availability")] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=100, description="Search title or author")] = None,
    sort: Annotated[crud.SortField, Query(description="Field to sort by")] = "id",
    order: Annotated[crud.SortOrder, Query(description="Sort direction")] = "asc",
) -> BookList:
    """Return a paginated list of books with optional filtering, search and sorting."""
    items, total = crud.list_books(
        db, limit=limit, offset=offset, author=author, genre=genre,
        available=available, q=q, sort=sort, order=order,
    )
    return BookList(
        items=[BookRead.model_validate(b) for b in items], total=total, limit=limit, offset=offset
    )


@router.post(
    "",
    response_model=BookRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a book",
    responses={**R409, **R422},
)
def create_book(payload: BookCreate, db: DB, response: Response) -> Book:
    """Create a new book. The `Location` response header points to the new resource."""
    book = crud.create_book(db, payload)
    response.headers["Location"] = f"{router.prefix}/{book.id}"
    return book


@router.get("/{book_id}", response_model=BookRead, summary="Get a book", responses={**R404, **R422})
def get_book(book_id: BookId, db: DB) -> Book:
    """Retrieve a single book by its ID."""
    return get_book_or_404(db, book_id)


@router.put(
    "/{book_id}",
    response_model=BookRead,
    summary="Replace a book",
    responses={**R404, **R409, **R422},
)
def replace_book(book_id: BookId, payload: BookUpdate, db: DB) -> Book:
    """Replace every field of a book. Omitted optional fields are reset to their defaults."""
    book = get_book_or_404(db, book_id)
    return crud.update_book(db, book, payload.model_dump())


@router.patch(
    "/{book_id}",
    response_model=BookRead,
    summary="Partially update a book",
    responses={**R404, **R409, **R422},
)
def patch_book(book_id: BookId, payload: BookPatch, db: DB) -> Book:
    """Update only the fields included in the request body."""
    book = get_book_or_404(db, book_id)
    return crud.update_book(db, book, payload.model_dump(exclude_unset=True))


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a book",
    responses={**R404, **R422},
)
def delete_book(book_id: BookId, db: DB) -> Response:
    """Permanently delete a book. Returns an empty body on success."""
    book = get_book_or_404(db, book_id)
    crud.delete_book(db, book)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
