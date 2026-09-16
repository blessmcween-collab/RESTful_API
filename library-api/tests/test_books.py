from tests.conftest import make_isbn

BASE = "/api/v1/books"


def assert_error(response, status, code):
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)
    return body["error"]


# --------------------------------------------------------------------------- #
# System
# --------------------------------------------------------------------------- #
def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_openapi_docs_available(client):
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/api/v1/books/{book_id}" in schema["paths"]


# --------------------------------------------------------------------------- #
# Create
# --------------------------------------------------------------------------- #
def test_create_book(client, book_payload):
    response = client.post(BASE, json=book_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["isbn"] == "9780132350884"  # hyphens stripped
    assert data["available"] is True       # default applied
    assert response.headers["location"] == f"{BASE}/1"
    assert "created_at" in data and "updated_at" in data


def test_create_strips_whitespace(client, book_payload):
    book_payload["title"] = "   Clean Code  "
    assert client.post(BASE, json=book_payload).json()["title"] == "Clean Code"


def test_create_missing_required_field(client, book_payload):
    del book_payload["title"]
    error = assert_error(client.post(BASE, json=book_payload), 422, "validation_error")
    assert error["details"][0]["field"] == "title"
    assert error["details"][0]["location"] == "body"


def test_create_invalid_values(client, book_payload):
    book_payload.update(title="", isbn="9780132350885", published_year=3000, pages=-5)
    error = assert_error(client.post(BASE, json=book_payload), 422, "validation_error")
    fields = {d["field"] for d in error["details"]}
    assert fields == {"title", "isbn", "published_year", "pages"}
    isbn_msg = next(d["message"] for d in error["details"] if d["field"] == "isbn")
    assert isbn_msg == "ISBN check digit is invalid"


def test_create_rejects_unknown_fields(client, book_payload):
    book_payload["price"] = 10
    error = assert_error(client.post(BASE, json=book_payload), 422, "validation_error")
    assert error["details"][0]["field"] == "price"


def test_create_malformed_json(client):
    response = client.post(BASE, content="{not json", headers={"Content-Type": "application/json"})
    assert_error(response, 422, "validation_error")


def test_create_duplicate_isbn(client, created_book, book_payload):
    book_payload["title"] = "Another title"
    error = assert_error(client.post(BASE, json=book_payload), 409, "conflict")
    assert error["details"] == {"field": "isbn"}


# --------------------------------------------------------------------------- #
# Read
# --------------------------------------------------------------------------- #
def test_get_book(client, created_book):
    response = client.get(f"{BASE}/{created_book['id']}")
    assert response.status_code == 200
    assert response.json() == created_book


def test_get_missing_book(client):
    error = assert_error(client.get(f"{BASE}/999"), 404, "not_found")
    assert error["message"] == "Book with id 999 was not found"


def test_get_invalid_id(client):
    assert_error(client.get(f"{BASE}/0"), 422, "validation_error")
    assert_error(client.get(f"{BASE}/abc"), 422, "validation_error")


def _seed(client):
    books = [
        ("Dune", "Frank Herbert", 1965, "Sci-Fi", True),
        ("Neuromancer", "William Gibson", 1984, "sci-fi", False),
        ("Clean Architecture", "Robert C. Martin", 2017, "Software Engineering", True),
        ("The Hobbit", "J.R.R. Tolkien", 1937, "Fantasy", True),
    ]
    for i, (title, author, year, genre, available) in enumerate(books):
        payload = {
            "title": title, "author": author, "published_year": year,
            "genre": genre, "available": available, "isbn": make_isbn(f"97800000000{i}"),
        }
        assert client.post(BASE, json=payload).status_code == 201


def test_list_pagination(client):
    _seed(client)
    data = client.get(BASE, params={"limit": 2, "offset": 1}).json()
    assert data["total"] == 4
    assert data["limit"] == 2 and data["offset"] == 1
    assert [b["title"] for b in data["items"]] == ["Neuromancer", "Clean Architecture"]


def test_list_filters_and_search(client):
    _seed(client)
    assert client.get(BASE, params={"genre": "SCI-FI"}).json()["total"] == 2
    assert client.get(BASE, params={"available": "false"}).json()["total"] == 1
    assert client.get(BASE, params={"author": "martin"}).json()["total"] == 1
    assert client.get(BASE, params={"q": "the"}).json()["items"][0]["title"] == "The Hobbit"


def test_list_sorting(client):
    _seed(client)
    items = client.get(BASE, params={"sort": "published_year", "order": "desc"}).json()["items"]
    assert [b["published_year"] for b in items] == [2017, 1984, 1965, 1937]


def test_list_invalid_query_params(client):
    error = assert_error(client.get(BASE, params={"limit": 500, "sort": "password"}), 422, "validation_error")
    assert {(d["location"], d["field"]) for d in error["details"]} == {("query", "limit"), ("query", "sort")}


# --------------------------------------------------------------------------- #
# Update (PUT / PATCH)
# --------------------------------------------------------------------------- #
def test_put_replaces_book(client, created_book, book_payload):
    new = {**book_payload, "title": "Clean Code (2nd ed.)"}
    del new["genre"]  # omitted optional field is reset
    response = client.put(f"{BASE}/{created_book['id']}", json=new)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Clean Code (2nd ed.)"
    assert data["genre"] is None
    assert data["created_at"] == created_book["created_at"]


def test_put_requires_full_body(client, created_book):
    assert_error(client.put(f"{BASE}/{created_book['id']}", json={"title": "x"}), 422, "validation_error")


def test_put_missing_book(client, book_payload):
    assert_error(client.put(f"{BASE}/42", json=book_payload), 404, "not_found")


def test_patch_updates_only_given_fields(client, created_book):
    response = client.patch(f"{BASE}/{created_book['id']}", json={"available": False})
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False
    assert data["title"] == created_book["title"]
    assert data["updated_at"] >= created_book["updated_at"]


def test_patch_can_clear_optional_field(client, created_book):
    data = client.patch(f"{BASE}/{created_book['id']}", json={"genre": None}).json()
    assert data["genre"] is None


def test_patch_rejects_empty_body_and_nulls(client, created_book):
    url = f"{BASE}/{created_book['id']}"
    error = assert_error(client.patch(url, json={}), 422, "validation_error")
    assert error["details"][0]["message"] == "At least one field must be provided"
    error = assert_error(client.patch(url, json={"title": None}), 422, "validation_error")
    assert error["details"][0]["message"] == "'title' cannot be null"


def test_patch_isbn_conflict(client, created_book, book_payload):
    other = client.post(BASE, json={**book_payload, "isbn": make_isbn("978111111111")}).json()
    response = client.patch(f"{BASE}/{other['id']}", json={"isbn": created_book["isbn"]})
    assert_error(response, 409, "conflict")


def test_patch_same_isbn_is_not_a_conflict(client, created_book):
    response = client.patch(f"{BASE}/{created_book['id']}", json={"isbn": created_book["isbn"]})
    assert response.status_code == 200


# --------------------------------------------------------------------------- #
# Delete
# --------------------------------------------------------------------------- #
def test_delete_book(client, created_book):
    url = f"{BASE}/{created_book['id']}"
    response = client.delete(url)
    assert response.status_code == 204
    assert response.content == b""
    assert_error(client.get(url), 404, "not_found")
    assert_error(client.delete(url), 404, "not_found")


# --------------------------------------------------------------------------- #
# Framework-level errors use the same format
# --------------------------------------------------------------------------- #
def test_unknown_route(client):
    assert_error(client.get("/api/v1/authors"), 404, "not_found")


def test_method_not_allowed(client):
    assert_error(client.delete(BASE), 405, "method_not_allowed")
