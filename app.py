"""Course Catalog Data-as-a-Service (DaaS) API.

Exposes a SQLite-backed course catalog through a read-only REST/JSON interface.
Run locally:  python app.py          (dev server, port 5000)
Production:   gunicorn app:app       (see Dockerfile / Procfile)
"""
import os
import sqlite3
import time
from pathlib import Path

from flask import Flask, g, jsonify, request

DB_PATH = Path(os.environ.get("DB_PATH", Path(__file__).with_name("courses.db")))
MAX_LIMIT = 100
SORTABLE = {"code", "title", "department", "level", "credits", "semester", "enrolled", "capacity"}

app = Flask(__name__)
app.json.sort_keys = False


# ---------- database helpers ----------
def get_db():
    if "db" not in g:
        # read-only connection: the service only exposes data, never modifies it
        g.db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def rows_to_dicts(rows):
    return [dict(r) for r in rows]


def error(message, status):
    return jsonify({"error": message}), status


@app.before_request
def start_timer():
    g.t0 = time.perf_counter()


@app.after_request
def add_headers(resp):
    if hasattr(g, "t0"):
        resp.headers["X-Response-Time-ms"] = f"{(time.perf_counter() - g.t0) * 1000:.2f}"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


# ---------- endpoints ----------
@app.get("/")
def index():
    return jsonify({
        "service": "Course Catalog DaaS",
        "version": "1.0",
        "endpoints": {
            "GET /health": "liveness check",
            "GET /api/courses": "list/search courses (q, department, level, semester, "
                                "min_credits, max_credits, instructor, available, sort, order, limit, offset)",
            "GET /api/courses/<code>": "one course by code, e.g. CSE540",
            "GET /api/departments": "departments with course counts",
            "GET /api/stats": "summary statistics",
        },
    })


@app.get("/health")
def health():
    try:
        n = get_db().execute("SELECT COUNT(*) FROM courses").fetchone()[0]
        return jsonify({"status": "ok", "courses": n})
    except sqlite3.Error as exc:
        return error(f"database unavailable: {exc}", 503)


@app.get("/api/courses")
def list_courses():
    args = request.args
    where, params = [], []

    if q := args.get("q"):
        where.append("(title LIKE ? OR description LIKE ? OR code LIKE ?)")
        params += [f"%{q}%"] * 3
    if dept := args.get("department"):
        where.append("department = ?")
        params.append(dept.upper())
    if sem := args.get("semester"):
        where.append("semester = ? COLLATE NOCASE")
        params.append(sem)
    if inst := args.get("instructor"):
        where.append("instructor LIKE ?")
        params.append(f"%{inst}%")
    if args.get("available", "").lower() in {"1", "true", "yes"}:
        where.append("enrolled < capacity")

    for key, col, op in (("level", "level", "="), ("min_credits", "credits", ">="),
                         ("max_credits", "credits", "<=")):
        if (val := args.get(key)) is not None:
            if not val.isdigit():
                return error(f"'{key}' must be an integer", 400)
            where.append(f"{col} {op} ?")
            params.append(int(val))

    sort = args.get("sort", "code")
    if sort not in SORTABLE:
        return error(f"'sort' must be one of {sorted(SORTABLE)}", 400)
    order = "DESC" if args.get("order", "asc").lower() == "desc" else "ASC"

    try:
        limit = min(int(args.get("limit", 20)), MAX_LIMIT)
        offset = max(int(args.get("offset", 0)), 0)
        if limit < 1:
            raise ValueError
    except ValueError:
        return error("'limit' and 'offset' must be positive integers", 400)

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    db = get_db()
    total = db.execute(f"SELECT COUNT(*) FROM courses {clause}", params).fetchone()[0]
    rows = db.execute(
        f"SELECT * FROM courses {clause} ORDER BY {sort} {order} LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()
    return jsonify({"total": total, "limit": limit, "offset": offset, "results": rows_to_dicts(rows)})


@app.get("/api/courses/<code>")
def get_course(code):
    row = get_db().execute("SELECT * FROM courses WHERE code = ? COLLATE NOCASE", (code,)).fetchone()
    if row is None:
        return error(f"course '{code}' not found", 404)
    return jsonify(dict(row))


@app.get("/api/departments")
def departments():
    rows = get_db().execute(
        "SELECT department, COUNT(*) AS courses, ROUND(AVG(credits), 2) AS avg_credits "
        "FROM courses GROUP BY department ORDER BY department"
    ).fetchall()
    return jsonify(rows_to_dicts(rows))


@app.get("/api/stats")
def stats():
    db = get_db()
    summary = dict(db.execute(
        "SELECT COUNT(*) AS total_courses, SUM(capacity) AS total_capacity, "
        "SUM(enrolled) AS total_enrolled, ROUND(AVG(credits), 2) AS avg_credits FROM courses"
    ).fetchone())
    summary["by_semester"] = rows_to_dicts(db.execute(
        "SELECT semester, COUNT(*) AS courses FROM courses GROUP BY semester ORDER BY semester"
    ).fetchall())
    summary["by_level"] = rows_to_dicts(db.execute(
        "SELECT level, COUNT(*) AS courses FROM courses GROUP BY level ORDER BY level"
    ).fetchall())
    return jsonify(summary)


@app.errorhandler(404)
def not_found(_e):
    return error("resource not found", 404)


@app.errorhandler(405)
def bad_method(_e):
    return error("method not allowed (this service is read-only)", 405)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
