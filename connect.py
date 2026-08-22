import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def run_query(query, params=None):
    """Run a query. Returns rows as a list of dicts for SELECT-like queries, otherwise None."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            result = cur.fetchall() if cur.description is not None else None
        conn.commit()
        return result
    finally:
        conn.close()


def create_session_table():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                        UPDATE tutors
                        SET ttimes = ARRAY['Monday 12pm-2pm', 'Wednesday 10am-2pm']
                        WHERE tpid = '6235552';
                        """)
        conn.commit()
        print("Success!")
    except psycopg2.Error as e:
        print("Database error:", e)
    finally:
        conn.close()


if __name__ == "__main__":
    create_session_table()
