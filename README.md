# Library Management System

A full-stack web application for managing a library's books and members. Users can add, search, issue, return and delete book records, and the page updates instantly without reloading.

## Technologies Used

| Layer | Tools |
|---|---|
| Frontend | HTML, CSS, JavaScript (Fetch API) |
| Frontend tooling | Node.js (npm scripts for linting/syntax check) |
| Backend | Python 3, Flask (REST API, JSON) |
| Database | SQLite (tables: `books`, `members`) |
| Testing | pytest |

## Features

- Add a book (Title, Author, ISBN, Category) with validation and duplicate-ISBN protection
- View all books, with live search by title, author or ISBN
- Filter by availability (All / Available / Issued)
- Issue a book to a member; blocked if the book is already issued
- Return a book; blocked if the book is not issued
- Delete a book; blocked while the book is issued
- Add members
- Updates without page reload (Fetch API)

## REST API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/books?q=&status=` | List / search books |
| POST | `/api/books` | Add a book |
| DELETE | `/api/books/<id>` | Delete a book |
| POST | `/api/books/<id>/issue` | Issue to a member (`{"member_id": 1}`) |
| POST | `/api/books/<id>/return` | Return a book |
| GET | `/api/members` | List members |
| POST | `/api/members` | Add a member |

## Database Schema

- `members(id, name, email UNIQUE)`
- `books(id, title, author, isbn UNIQUE, category, available, issued_to -> members.id, issue_date)`

## How to Run

Requirements: Python 3.9+ and Node.js 18+ (Node is only needed for the optional lint script).

```bash
# 1. Clone the repository
git clone https://github.com/viveksamarth404-design/library-management-system.git
cd library-management-system

# 2. (Optional) create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
python app.py                   # or: npm start
```

Open **http://127.0.0.1:5000** in your browser. The SQLite database (`library.db`) is created automatically with a few sample books and members on first run.

## Testing

```bash
python -m pytest -v      # or: npm test   (backend API + edge cases)
npm run lint             # frontend file and JavaScript syntax check
```

Edge cases covered: searching a non-existent book, returning a book that is not issued, issuing an unavailable book, deleting an issued book, duplicate ISBN, invalid ISBN, unknown member/book.

## Project Structure

```
app.py              Flask app, routes and schema
static/index.html   Page markup
static/css/style.css
static/js/app.js    Fetch API calls and DOM updates
tests/test_api.py   pytest suite
scripts/check.js    Node frontend check
package.json        npm scripts
requirements.txt
```
