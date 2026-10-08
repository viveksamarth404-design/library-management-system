import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app  # noqa: E402


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    return app.test_client()


def new_book(client, isbn="9780306406157", title="Test Book"):
    return client.post("/api/books", json={
        "title": title, "author": "Some Author", "isbn": isbn, "category": "Test"})


def test_add_and_list(client):
    r = new_book(client)
    assert r.status_code == 201
    assert r.get_json()["available"] == 1
    assert any(b["title"] == "Test Book" for b in client.get("/api/books").get_json())


def test_add_validation(client):
    assert client.post("/api/books", json={"title": "x"}).status_code == 400
    assert new_book(client, isbn="abc").status_code == 400


def test_duplicate_isbn(client):
    new_book(client)
    assert new_book(client).status_code == 409


def test_search_by_title_author_isbn(client):
    new_book(client, title="Quantum Gardens")
    assert len(client.get("/api/books?q=quantum").get_json()) == 1
    assert len(client.get("/api/books?q=Some Author").get_json()) == 1
    assert len(client.get("/api/books?q=9780306406157").get_json()) == 1


def test_search_nonexistent_returns_empty(client):
    r = client.get("/api/books?q=zzz-no-such-book")
    assert r.status_code == 200 and r.get_json() == []


def test_issue_and_return_flow(client):
    book_id = new_book(client).get_json()["id"]
    r = client.post(f"/api/books/{book_id}/issue", json={"member_id": 1})
    assert r.status_code == 200 and r.get_json()["available"] == 0
    r = client.post(f"/api/books/{book_id}/return")
    assert r.status_code == 200 and r.get_json()["available"] == 1


def test_cannot_issue_unavailable_book(client):
    book_id = new_book(client).get_json()["id"]
    client.post(f"/api/books/{book_id}/issue", json={"member_id": 1})
    r = client.post(f"/api/books/{book_id}/issue", json={"member_id": 2})
    assert r.status_code == 409
    assert "unavailable" in r.get_json()["error"]


def test_return_book_not_issued(client):
    book_id = new_book(client).get_json()["id"]
    assert client.post(f"/api/books/{book_id}/return").status_code == 409


def test_issue_unknown_member_or_book(client):
    book_id = new_book(client).get_json()["id"]
    assert client.post(f"/api/books/{book_id}/issue", json={"member_id": 999}).status_code == 404
    assert client.post("/api/books/999/issue", json={"member_id": 1}).status_code == 404
    assert client.post(f"/api/books/{book_id}/issue", json={}).status_code == 400


def test_delete(client):
    book_id = new_book(client).get_json()["id"]
    assert client.delete(f"/api/books/{book_id}").status_code == 200
    assert client.delete(f"/api/books/{book_id}").status_code == 404


def test_cannot_delete_issued_book(client):
    book_id = new_book(client).get_json()["id"]
    client.post(f"/api/books/{book_id}/issue", json={"member_id": 1})
    assert client.delete(f"/api/books/{book_id}").status_code == 409


def test_members(client):
    assert len(client.get("/api/members").get_json()) >= 3
    assert client.post("/api/members", json={"name": "Z", "email": "z@x.com"}).status_code == 201
    assert client.post("/api/members", json={"name": "Z", "email": "z@x.com"}).status_code == 409
    assert client.post("/api/members", json={"name": "", "email": "bad"}).status_code == 400
