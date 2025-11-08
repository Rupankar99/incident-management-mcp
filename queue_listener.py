import sqlite3
import asyncio
import json

from main import main as run_main  # Import your existing async main()

DB_PATH = r"Y:\incident_iq\database\data\incident_iq.db"
POLL_INTERVAL = 5  # seconds between checks


def get_pending_message(conn):
    print("Fetch a pending message from the queue (FIFO order).")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, data FROM queue
        WHERE status = 'pending'
        ORDER BY created_at ASC
        LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        return {"id": row[0], "data": json.loads(row[1])}
    return None


def mark_message_processed(conn, message_id):
    """Mark message as processed."""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE queue
        SET status = 'processed',
            processed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (message_id,))
    conn.commit()


async def handle_message(message):
    """Handle a message by triggering the incident system."""
    print(f"\n📬 Consumed message: {message['id']}")
    print(f"🧩 Payload: {json.dumps(message['data'], indent=2)}")

    # Trigger your existing async main() from main.py
    await run_main()

    print("✅ Incident processing completed for this message.\n")


async def watch_queue():
    """Continuously poll the queue for new messages."""
    print("🚀 Queue watcher started. Waiting for messages...\n")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    while True:
        message = get_pending_message(conn)
        if message:
            await handle_message(message)
            mark_message_processed(conn, message["id"])
        else:
            print("⏳ No messages in queue. Checking again soon...")
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(watch_queue())
