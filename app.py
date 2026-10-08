"""Library Management System - Flask backend with SQLite storage."""
import os
import sqlite3
from datetime import date

from flask import Flask, g, jsonify, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCHEMA = """
CREATE TABLE IF NOT EXISTS members (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    email   TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS books (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    author      TEXT NOT NULL,
    isbn        TEXT NOT NULL UNIQUE,
    category    TEXT NOT NULL DEFAULT 'General',
    available   INTEGER NOT NULL DEFAULT 1,
    issued_to   INTEGER REFERENCES members(id),
    issue_date  TEXT
);
"""

BOOK_SELECT = """
SELECT b.id, b.title, b.author, b.isbn, b.category, b.available,
       b.issued_to, b.issue_date, m.name AS member_name
FROM books b LEFT JOIN members m ON m.id = b.issued_to
"""


def create_app(db_path=None):
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config["DATABASE"] = db_path or os.path.join(BASE_DIR, "library.db")

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        if db.execute("SELECT COUNT(*) FROM members").fetchone()[0] == 0:
            db.executemany(
                "INSERT INTO members (name, email) VALUES (?, ?)",
                [("Aarav Deshmukh", "aarav@example.com"),
                 ("Meera Kulkarni", "meera@example.com"),
                 ("Rohan Patil", "rohan@example.com")],
            )
            db.executemany(
                "INSERT INTO books (title, author, isbn, category) VALUES (?, ?, ?, ?)",
                [("Introduction to Algorithms", "Thomas H. Cormen", "9780262046305", "Computer Science"),
                 ("Digital Signal Processing", "John G. Proakis", "9780133737622", "Electronics"),
                 ("Wings of Fire", "A. P. J. Abdul Kalam", "9788173711466", "Biography")],
            )
            db.commit()

    def error(message, status):
        return jsonify({"error": message}), status

    def clean(data, key):
        value = data.get(key, "")
        return value.strip() if isinstance(value, str) else ""

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    # ---------- Books ----------
    @app.get("/api/books")
    def list_books():
        q = request.args.get("q", "").strip()
        status = request.args.get("status", "").strip()
        sql, params = BOOK_SELECT + " WHERE 1=1", []
        if q:
            sql += " AND (b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ?)"
            params += [f"%{q}%"] * 3
        if status == "available":
            sql += " AND b.available = 1"
        elif status == "issued":
            sql += " AND b.available = 0"
        sql += " ORDER BY b.title COLLATE NOCASE"
        rows = get_db().execute(sql, params).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/api/books")
    def add_book():
        data = request.get_json(silent=True) or {}
        title, author = clean(data, "title"), clean(data, "author")
        isbn = clean(data, "isbn").replace("-", "").replace(" ", "")
        category = clean(data, "category") or "General"
        if not title or not author or not isbn:
            return error("Title, author and ISBN are required.", 400)
        if not isbn.isdigit() or len(isbn) not in (10, 13):
            return error("ISBN must be 10 or 13 digits.", 400)
        db = get_db()
        try:
            cur = db.execute(
                "INSERT INTO books (title, author, isbn, category) VALUES (?, ?, ?, ?)",
                (title, author, isbn, category),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return error("A book with this ISBN already exists.", 409)
        row = db.execute(BOOK_SELECT + " WHERE b.id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(dict(row)), 201

    @app.delete("/api/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if book is None:
            return error("Book not found.", 404)
        if not book["available"]:
            return error("This book is currently issued. Return it before deleting.", 409)
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return jsonify({"message": "Book deleted."})

    @app.post("/api/books/<int:book_id>/issue")
    def issue_book(book_id):
        data = request.get_json(silent=True) or {}
        member_id = data.get("member_id")
        if not isinstance(member_id, int):
            return error("Choose a member to issue the book to.", 400)
        db = get_db()
        book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if book is None:
            return error("Book not found.", 404)
        if db.execute("SELECT 1 FROM members WHERE id = ?", (member_id,)).fetchone() is None:
            return error("Member not found.", 404)
        if not book["available"]:
            return error("This book is already issued and unavailable.", 409)
        db.execute(
            "UPDATE books SET available = 0, issued_to = ?, issue_date = ? WHERE id = ?",
            (member_id, date.today().isoformat(), book_id),
        )
        db.commit()
        row = db.execute(BOOK_SELECT + " WHERE b.id = ?", (book_id,)).fetchone()
        return jsonify(dict(row))

    @app.post("/api/books/<int:book_id>/return")
    def return_book(book_id):
        db = get_db()
        book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if book is None:
            return error("Book not found.", 404)
        if book["available"]:
            return error("This book is not issued, so it cannot be returned.", 409)
        db.execute(
            "UPDATE books SET available = 1, issued_to = NULL, issue_date = NULL WHERE id = ?",
            (book_id,),
        )
        db.commit()
        row = db.execute(BOOK_SELECT + " WHERE b.id = ?", (book_id,)).fetchone()
        return jsonify(dict(row))

    # ---------- Members ----------
    @app.get("/api/members")
    def list_members():
        rows = get_db().execute("SELECT id, name, email FROM members ORDER BY name").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/api/members")
    def add_member():
        data = request.get_json(silent=True) or {}
        name, email = clean(data, "name"), clean(data, "email").lower()
        if not name or "@" not in email:
            return error("Enter a name and a valid email address.", 400)
        db = get_db()
        try:
            cur = db.execute("INSERT INTO members (name, email) VALUES (?, ?)", (name, email))
            db.commit()
        except sqlite3.IntegrityError:
            return error("A member with this email already exists.", 409)
        return jsonify({"id": cur.lastrowid, "name": name, "email": email}), 201

    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=5000)
