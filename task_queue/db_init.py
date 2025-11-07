import sqlite3

def init_db(db_path: str):
    """Initialize the SQLite database schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP NULL,
            consumer_id TEXT NULL
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_status 
        ON queue(status, created_at)
    """)
    conn.commit()
    conn.close()


def get_connection(db_path: str):
    """Return a new SQLite connection with Row factory enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
