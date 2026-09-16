"""Pydantic schemas: request validation and response serialisation."""
from datetime import datetime
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator


# --------------------------------------------------------------------------- #
# Reusable validators
# --------------------------------------------------------------------------- #
def validate_isbn13(value: str) -> str:
    """Accept ISBN-13 with optional hyphens/spaces; store digits only."""
    digits = value.replace("-", "").replace(" ", "")
    if len(digits) != 13 or not digits.isdigit():
        raise ValueError("ISBN must contain exactly 13 digits (hyphens and spaces are allowed)")
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
    if (10 - total % 10) % 10 != int(digits[12]):
        raise ValueError("ISBN check digit is invalid")
    return digits


def validate_not_future_year(value: int) -> int:
    if value > datetime.now().year:
        raise ValueError("published_year cannot be in the future")
    return value


Title = Annotated[str, Field(min_length=1, max_length=200, examples=["Clean Code"])]
Author = Annotated[str, Field(min_length=1, max_length=100, examples=["Robert C. Martin"])]
ISBN = Annotated[
    str,
    Field(description="ISBN-13; hyphens/spaces allowed, stored as digits", examples=["978-0132350884"]),
    AfterValidator(validate_isbn13),
]
Year = Annotated[int, Field(ge=1450, examples=[2008]), AfterValidator(validate_not_future_year)]
Pages = Annotated[int, Field(gt=0, le=10000, examples=[464])]
Genre = Annotated[str, Field(min_length=1, max_length=50, examples=["Software Engineering"])]


class _InputModel(BaseModel):
    # Trim whitespace before length checks; reject unknown fields.
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #
class BookCreate(_InputModel):
    """Body for POST (create)."""

    title: Title
    author: Author
    isbn: ISBN
    published_year: Year
    pages: Pages | None = None
    genre: Genre | None = None
    available: bool = True


class BookUpdate(BookCreate):
    """Body for PUT. PUT replaces the whole resource, so the same fields are required."""


class BookPatch(_InputModel):
    """Body for PATCH: send only the fields you want to change."""

    title: Title | None = None
    author: Author | None = None
    isbn: ISBN | None = None
    published_year: Year | None = None
    pages: Pages | None = None
    genre: Genre | None = None
    available: bool | None = None

    @model_validator(mode="after")
    def check_fields(self) -> "BookPatch":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        non_nullable = ("title", "author", "isbn", "published_year", "available")
        for name in non_nullable:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"'{name}' cannot be null")
        return self


# --------------------------------------------------------------------------- #
# Responses
# --------------------------------------------------------------------------- #
class BookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str
    published_year: int
    pages: int | None
    genre: str | None
    available: bool
    created_at: datetime
    updated_at: datetime


class BookList(BaseModel):
    items: list[BookRead]
    total: int = Field(description="Total books matching the filters (ignores pagination)")
    limit: int
    offset: int


class ErrorInfo(BaseModel):
    code: str = Field(examples=["not_found"])
    message: str = Field(examples=["Book with id 42 was not found"])
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorInfo
