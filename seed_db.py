"""Create and populate the SQLite database (courses.db) with a university course catalog.

The dataset is synthetic (generated deterministically with a fixed seed) so that
it is reproducible and free of licensing issues. Run:  python seed_db.py
"""
import random
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("courses.db")

DEPARTMENTS = {
    "CSE": ["Cloud Computing", "Operating Systems", "Database Systems", "Computer Networks",
            "Machine Learning", "Software Engineering", "Data Structures", "Distributed Systems",
            "Information Security", "Compiler Design"],
    "MGT": ["Business Analytics", "Marketing Management", "Financial Accounting",
            "Operations Management", "Organizational Behaviour", "Business Statistics"],
    "MAT": ["Linear Algebra", "Probability and Statistics", "Discrete Mathematics",
            "Numerical Methods", "Calculus II"],
    "ECE": ["Digital Logic Design", "Signals and Systems", "Embedded Systems",
            "Computer Architecture", "Wireless Communication"],
    "HSS": ["Introduction to Psychology", "Environmental Studies", "Public Policy",
            "Sociology of Technology"],
}

INSTRUCTORS = [
    "A. Mehta", "S. Chaudhary", "R. Iyer", "P. Shah", "K. Nair", "N. Bosamiya",
    "D. Patel", "M. Rao", "L. Desai", "T. Joshi", "V. Kulkarni", "F. Khan",
]

SCHEMA = """
DROP TABLE IF EXISTS courses;
CREATE TABLE courses (
    code        TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    department  TEXT NOT NULL,
    level       INTEGER NOT NULL,      -- 100, 200, 300, 400, 500
    credits     INTEGER NOT NULL,
    semester    TEXT NOT NULL,         -- Monsoon / Winter / Summer
    instructor  TEXT NOT NULL,
    capacity    INTEGER NOT NULL,
    enrolled    INTEGER NOT NULL,
    description TEXT NOT NULL
);
CREATE INDEX idx_courses_department ON courses(department);
CREATE INDEX idx_courses_level ON courses(level);
CREATE INDEX idx_courses_semester ON courses(semester);
"""


def build_rows():
    rng = random.Random(540)  # fixed seed -> identical data every run
    rows, used = [], set()
    for dept, titles in DEPARTMENTS.items():
        for title in titles:
            level = rng.choice([100, 200, 300, 400, 500])
            number = level + rng.randint(1, 99)
            while f"{dept}{number}" in used:
                number += 1
            code = f"{dept}{number}"
            used.add(code)
            capacity = rng.choice([30, 40, 60, 80, 120])
            rows.append((
                code, title, dept, level, rng.choice([2, 3, 4]),
                rng.choice(["Monsoon", "Winter", "Summer"]),
                rng.choice(INSTRUCTORS), capacity, rng.randint(int(capacity * 0.4), capacity),
                f"{title}: concepts, case studies and a hands-on project at {level}-level.",
            ))
    return rows


def main():
    rows = build_rows()
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        conn.executemany("INSERT INTO courses VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    print(f"Created {DB_PATH.name} with {len(rows)} courses")


if __name__ == "__main__":
    main()
