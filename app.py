"""Notes app: Flask backend + SQLite storage, serving a single-page frontend."""
import os
import sqlite3
from flask import Flask, jsonify, request, g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "notes.db")

app = Flask(__name__, static_folder="static", static_url_path="")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS notes (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   title TEXT NOT NULL DEFAULT '',
                   body TEXT NOT NULL,
                   created_at TEXT NOT NULL DEFAULT (datetime('now'))
               )"""
        )


def row_to_dict(row):
    return {k: row[k] for k in row.keys()}


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/notes")
def list_notes():
    rows = get_db().execute(
        "SELECT id, title, body, created_at FROM notes ORDER BY id DESC"
    ).fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@app.post("/api/notes")
def create_note():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()[:120]
    body = str(data.get("body", "")).strip()
    if not body:
        return jsonify({"error": "Note text can't be empty."}), 400
    if len(body) > 5000:
        return jsonify({"error": "Note text is limited to 5,000 characters."}), 400
    db = get_db()
    cur = db.execute("INSERT INTO notes (title, body) VALUES (?, ?)", (title, body))
    db.commit()
    row = db.execute(
        "SELECT id, title, body, created_at FROM notes WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return jsonify(row_to_dict(row)), 201


@app.delete("/api/notes/<int:note_id>")
def delete_note(note_id):
    db = get_db()
    cur = db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "Note not found."}), 404
    return "", 204


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
