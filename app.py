import os
import threading
import time
from flask import Flask, jsonify, redirect, render_template, request, url_for
import psycopg
from psycopg.rows import dict_row

app = Flask(__name__)

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "notes_db")
DB_USER = os.getenv("DB_USER", "notes_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "notes_pass_2026")
STUDENT_NAME = os.getenv("STUDENT_NAME", "Alvaro Becerra")

ALLOWED_CATEGORIES = ("Tendencias", "Docker", "General", "Urgente")

_schema_lock = threading.Lock()
_schema_ready = False


def get_db_connection() -> psycopg.Connection:
    """Create and return a PostgreSQL connection using environment settings."""
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=3,
        row_factory=dict_row,
    )


def ensure_schema(retries: int = 5, delay: float = 1.0) -> None:
    """Initialize the notes table once, retrying briefly while the database starts."""
    global _schema_ready
    if _schema_ready:
        return

    with _schema_lock:
        if _schema_ready:
            return

        last_error = None
        for attempt in range(retries):
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            CREATE TABLE IF NOT EXISTS notes (
                                id SERIAL PRIMARY KEY,
                                title VARCHAR(200) NOT NULL,
                                category VARCHAR(40) NOT NULL DEFAULT 'General',
                                is_done BOOLEAN NOT NULL DEFAULT FALSE,
                                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                            );
                            """
                        )
                _schema_ready = True
                return
            except psycopg.Error as exc:
                last_error = exc
                if attempt < retries - 1:
                    time.sleep(delay)

        raise last_error


def fetch_dashboard_data() -> tuple[list[dict], str]:
    """Load all notes and the active PostgreSQL server version."""
    ensure_schema()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version_row = cur.fetchone()
            raw_version = version_row["version"] if version_row else "PostgreSQL"
            pg_version = " ".join(raw_version.split()[:2])

            cur.execute(
                """
                SELECT id, title, category, is_done,
                       TO_CHAR(created_at, 'DD/MM/YYYY HH24:MI') AS created_label
                FROM notes
                ORDER BY is_done ASC, id DESC;
                """
            )
            notes = cur.fetchall()
    return notes, pg_version


@app.route("/")
def index():
    """Render the main notes dashboard with live PostgreSQL connection status."""
    notes = []
    db_connected = False
    pg_version = "No disponible"
    error_message = None

    try:
        notes, pg_version = fetch_dashboard_data()
        db_connected = True
    except psycopg.Error as exc:
        error_message = str(exc)

    total_count = len(notes)
    done_count = sum(1 for note in notes if note["is_done"])
    pending_count = total_count - done_count

    return render_template(
        "index.html",
        student_name=STUDENT_NAME,
        notes=notes,
        categories=ALLOWED_CATEGORIES,
        db_connected=db_connected,
        db_host=DB_HOST,
        db_name=DB_NAME,
        pg_version=pg_version,
        error_message=error_message,
        total_count=total_count,
        done_count=done_count,
        pending_count=pending_count,
    )


@app.route("/notes", methods=["POST"])
def create_note():
    """Insert a new note into PostgreSQL."""
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "General").strip()
    if category not in ALLOWED_CATEGORIES:
        category = "General"

    if title:
        ensure_schema()
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO notes (title, category) VALUES (%s, %s);",
                    (title[:200], category),
                )

    return redirect(url_for("index"))


@app.route("/notes/<int:note_id>/toggle", methods=["POST"])
def toggle_note(note_id: int):
    """Toggle the completion state of an existing note."""
    ensure_schema()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE notes SET is_done = NOT is_done WHERE id = %s;",
                (note_id,),
            )

    return redirect(url_for("index"))


@app.route("/notes/<int:note_id>/delete", methods=["POST"])
def delete_note(note_id: int):
    """Delete a note from PostgreSQL."""
    ensure_schema()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM notes WHERE id = %s;", (note_id,))

    return redirect(url_for("index"))


@app.route("/health")
def health():
    """Verify database connectivity for monitoring and CLI checks."""
    try:
        ensure_schema(retries=1, delay=0)
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 AS ok;")
                cur.fetchone()
        return jsonify({"status": "ok", "database": "connected", "host": DB_HOST}), 200
    except psycopg.Error as exc:
        return jsonify({"status": "error", "database": "disconnected", "detail": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
