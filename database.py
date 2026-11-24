import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "legitx.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def initialize_database():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                function_name TEXT NOT NULL,
                file_name TEXT,
                question TEXT NOT NULL,
                score INTEGER NOT NULL,
                max_score INTEGER NOT NULL,
                percentage REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()


def save_evaluation(function_name, file_name, question, evaluation):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO evaluations (
                function_name, file_name, question,
                score, max_score, percentage
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            function_name,
            file_name,
            question,
            evaluation["total_score"],
            evaluation["maximum_score"],
            evaluation["percentage"]
        ))

        conn.commit()


def get_function_progress():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                function_name,
                COUNT(*) AS attempts,
                AVG(percentage) AS average_score,
                MAX(percentage) AS best_score
            FROM evaluations
            GROUP BY function_name
            ORDER BY average_score ASC
        """)

        return cursor.fetchall()


def get_overall_stats():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*),
                COALESCE(AVG(percentage), 0),
                COUNT(DISTINCT function_name)
            FROM evaluations
        """)

        return cursor.fetchone()


def get_recent_evaluations(limit=10):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                function_name,
                file_name,
                score,
                max_score,
                percentage,
                created_at
            FROM evaluations
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()