# Library Books API

A RESTful API for managing a library's book catalogue, built with **FastAPI**, **SQLAlchemy 2.0** and **SQLite** (PostgreSQL-ready).

It demonstrates resource-oriented route design, request validation, centralised error handling, consistent JSON responses, database integration and automated tests.

---

## Contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Interactive documentation](#interactive-documentation)
- [API reference](#api-reference)
- [Error handling](#error-handling)
- [Running the tests](#running-the-tests)
- [Using PostgreSQL](#using-postgresql)
- [Design decisions](#design-decisions)

---

## Features

- **6 CRUD endpoints** for books: create, list, get, replace (PUT), partial update (PATCH), delete
- **Validation** of every input: string lengths, number ranges, ISBN-13 check digit, no future publication years, unknown fields rejected, whitespace trimmed
- **Pagination, filtering, search and sorting** on the list endpoint
- **Consistent error format** for every failure, including framework errors (404 unknown route, 405, malformed JSON)
- **Correct HTTP semantics**: `201 Created` with a `Location` header, `204 No Content` on delete, `409 Conflict` on duplicate ISBN
- **Auto-generated OpenAPI docs** (Swagger UI and ReDoc) plus this written reference
- **27 automated tests** running against an isolated in-memory database

## Tech stack

| Layer          | Choice                          |
| -------------- | ------------------------------- |
| Web framework  | FastAPI                         |
| Validation     | Pydantic v2                     |
| ORM            | SQLAlchemy 2.0                  |
| Database       | SQLite (default) or PostgreSQL  |
| Server         | Uvicorn                         |
| Tests          | pytest + FastAPI `TestClient`   |

## Project structure

```
library-api/
├── app/
│   ├── main.py          # App creation, docs metadata, health check
│   ├── database.py      # Engine, session factory, get_db dependency
│   ├── models.py        # SQLAlchemy table definitions
│   ├── schemas.py       # Pydantic request/response models + validators
│   ├── crud.py          # Database queries and business rules
│   ├── errors.py        # Custom exceptions and global error handlers
│   └── routers/
│       └── books.py     # /api/v1/books endpoints
├── tests/
│   ├── conftest.py      # Test client with a fresh in-memory DB per test
│   └── test_books.py
├── docs/
│   └── openapi.json     # Exported OpenAPI 3.1 specification
├── requirements.txt
└── README.md
```

Each layer has one job: **routers** handle HTTP, **schemas** validate data, **crud** talks to the database, and **errors** turns exceptions into JSON.

## Getting started

Requires **Python 3.10+**.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server (tables are created automatically on startup)
uvicorn app.main:app --reload
```

The API is now running at **http://127.0.0.1:8000**. A `library.db` SQLite file is created in the project folder.

## Interactive documentation

FastAPI generates live documentation from the code, so it never goes out of date:

| URL                                  | What it is                                   |
| ------------------------------------ | -------------------------------------------- |
| http://127.0.0.1:8000/docs           | Swagger UI: try every endpoint in the browser |
| http://127.0.0.1:8000/redoc          | ReDoc: clean, readable reference             |
| http://127.0.0.1:8000/openapi.json   | Raw OpenAPI spec (also saved in `docs/`)     |

---

## API reference

**Base URL:** `http://127.0.0.1:8000/api/v1`
**Content type:** all requests and responses use `application/json`.

### Endpoints

| Method   | Path              | Description               | Success | Errors             |
| -------- | ----------------- | ------------------------- | ------- | ------------------ |
| `GET`    | `/health`         | Service & database health | 200     |                    |
| `GET`    | `/books`          | List books                | 200     | 422                |
| `POST`   | `/books`          | Create a book             | 201     | 409, 422           |
| `GET`    | `/books/{id}`     | Get one book              | 200     | 404, 422           |
| `PUT`    | `/books/{id}`     | Replace a book            | 200     | 404, 409, 422      |
| `PATCH`  | `/books/{id}`     | Partially update a book   | 200     | 404, 409, 422      |
| `DELETE` | `/books/{id}`     | Delete a book             | 204     | 404, 422           |

> `/health` lives at the root (`http://127.0.0.1:8000/health`), not under `/api/v1`.

### The Book object

| Field            | Type             | Rules                                                          |
| ---------------- | ---------------- | -------------------------------------------------------------- |
| `id`             | integer          | Read-only, assigned by the database                            |
| `title`          | string           | **Required**, 1–200 characters                                 |
| `author`         | string           | **Required**, 1–100 characters                                 |
| `isbn`           | string           | **Required**, valid ISBN-13, unique. Hyphens/spaces accepted, stored as 13 digits |
| `published_year` | integer          | **Required**, 1450 up to the current year                      |
| `pages`          | integer \| null  | Optional, 1–10000                                              |
| `genre`          | string \| null   | Optional, 1–50 characters                                      |
| `available`      | boolean          | Optional, defaults to `true`                                   |
| `created_at`     | datetime         | Read-only                                                      |
| `updated_at`     | datetime         | Read-only, changes on every update                             |

Leading/trailing whitespace is trimmed from strings. Any field not listed above is rejected.

---

### List books

`GET /api/v1/books`

| Query param | Type    | Default | Description                                                     |
| ----------- | ------- | ------- | --------------------------------------------------------------- |
| `limit`     | integer | `20`    | Items per page (1–100)                                          |
| `offset`    | integer | `0`     | Items to skip                                                   |
| `author`    | string  |         | Partial, case-insensitive author match                          |
| `genre`     | string  |         | Exact, case-insensitive genre match                             |
| `available` | boolean |         | `true` or `false`                                               |
| `q`         | string  |         | Search in title **or** author                                   |
| `sort`      | string  | `id`    | One of `id`, `title`, `author`, `published_year`, `created_at`  |
| `order`     | string  | `asc`   | `asc` or `desc`                                                 |

```bash
curl "http://127.0.0.1:8000/api/v1/books?available=true&sort=published_year&order=desc&limit=10"
```

**200 OK**
```json
{
  "items": [
    {
      "id": 1,
      "title": "Clean Code",
      "author": "Robert C. Martin",
      "isbn": "9780132350884",
      "published_year": 2008,
      "pages": 464,
      "genre": "Software Engineering",
      "available": true,
      "created_at": "2026-09-16T10:00:00",
      "updated_at": "2026-09-16T10:00:00"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

`total` is the number of books matching the filters across all pages, so a client can build pagination controls.

---

### Create a book

`POST /api/v1/books`

```bash
curl -X POST http://127.0.0.1:8000/api/v1/books \
  -H "Content-Type: application/json" \
  -d '{
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "978-0132350884",
        "published_year": 2008,
        "pages": 464,
        "genre": "Software Engineering"
      }'
```

**201 Created** (header `Location: /api/v1/books/1`)
```json
{
  "id": 1,
  "title": "Clean Code",
  "author": "Robert C. Martin",
  "isbn": "9780132350884",
  "published_year": 2008,
  "pages": 464,
  "genre": "Software Engineering",
  "available": true,
  "created_at": "2026-09-16T10:00:00",
  "updated_at": "2026-09-16T10:00:00"
}
```

**409 Conflict** if the ISBN already exists:
```json
{
  "error": {
    "code": "conflict",
    "message": "A book with ISBN 9780132350884 already exists",
    "details": { "field": "isbn" }
  }
}
```

---

### Get a book

`GET /api/v1/books/{id}`

```bash
curl http://127.0.0.1:8000/api/v1/books/1
```

**200 OK** returns a Book object. **404 Not Found** if no book has that ID.

---

### Replace a book (PUT)

`PUT /api/v1/books/{id}`

Sends the **complete** book. All required fields must be present; optional fields you leave out are reset to their defaults (`pages`/`genre` → `null`, `available` → `true`).

```bash
curl -X PUT http://127.0.0.1:8000/api/v1/books/1 \
  -H "Content-Type: application/json" \
  -d '{
        "title": "Clean Code (Revised)",
        "author": "Robert C. Martin",
        "isbn": "9780132350884",
        "published_year": 2008,
        "available": false
      }'
```

**200 OK** returns the updated Book.

---

### Partially update a book (PATCH)

`PATCH /api/v1/books/{id}`

Send **only** the fields to change. At least one field is required. `pages` and `genre` may be set to `null` to clear them; required fields cannot be `null`.

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/books/1 \
  -H "Content-Type: application/json" \
  -d '{"available": false}'
```

**200 OK** returns the updated Book.

---

### Delete a book

`DELETE /api/v1/books/{id}`

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/books/1
```

**204 No Content** with an empty body. **404 Not Found** if the book doesn't exist.

---

## Error handling

Every error, whether raised by the app or by the framework, returns the same shape:

```json
{
  "error": {
    "code": "machine_readable_code",
    "message": "Human-readable explanation",
    "details": null
  }
}
```

| Status | `code`               | When                                                        |
| ------ | -------------------- | ----------------------------------------------------------- |
| 404    | `not_found`          | Book ID doesn't exist, or the URL isn't a route             |
| 405    | `method_not_allowed` | e.g. `DELETE /api/v1/books`                                 |
| 409    | `conflict`           | ISBN already belongs to another book                        |
| 422    | `validation_error`   | Invalid body, path or query parameter, or malformed JSON    |
| 500    | `internal_error`     | Unexpected failure (logged server-side; no internals leaked) |

For `422` responses, `details` lists every problem at once so clients can show all errors together:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request contains invalid data",
    "details": [
      { "location": "body",  "field": "isbn",  "message": "ISBN check digit is invalid",     "type": "value_error" },
      { "location": "body",  "field": "pages", "message": "Input should be greater than 0", "type": "greater_than" },
      { "location": "query", "field": "limit", "message": "Input should be less than or equal to 100", "type": "less_than_equal" }
    ]
  }
}
```

## Running the tests

```bash
pytest -v
```

Each test gets a brand-new in-memory SQLite database (via FastAPI dependency overrides), so tests are fast, independent, and never touch `library.db`. The suite covers every endpoint, happy paths, validation failures, conflicts, 404/405 handling and the error format.

## Using PostgreSQL

The database is configured through the `DATABASE_URL` environment variable.

```bash
pip install "psycopg[binary]"
export DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/library"
uvicorn app.main:app --reload
```

No code changes are needed; the models use only portable column types.

## Design decisions

- **Versioned, plural, noun-based routes** (`/api/v1/books/{id}`): HTTP methods express the action, and the version prefix allows future breaking changes without disrupting clients.
- **PUT vs PATCH**: PUT replaces the full resource (idempotent); PATCH changes only supplied fields, using Pydantic's `exclude_unset` to tell "not sent" apart from "set to null".
- **Separate input and output schemas**: clients can't set `id` or timestamps, and responses never expose anything the model doesn't declare.
- **Business rules in `crud.py`**: routers stay thin and readable. Duplicate ISBNs are checked before insert, and the database's unique constraint is a second line of defence against race conditions.
- **Whitelisted sort fields**: `sort` is a `Literal` type, so arbitrary column names can't be injected into queries.
- **ISBN normalisation**: `978-0-13-235088-4` and `9780132350884` are treated as the same book.
- **Tables created on startup** for simplicity; a production service would use Alembic migrations.
