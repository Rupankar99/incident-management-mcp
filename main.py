import asyncio
import json
import sqlite3
from models import IncidentContext, Incident
from orchestrator import IncidentManagementSystem

DB_PATH = "/Users/rupankarchakroborty/Documents/incident-management-2/data.db"


def get_db_connection():
    """Create a database connection with proper settings."""
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30.0,
        isolation_level='DEFERRED',  # Use DEFERRED instead of None
        check_same_thread=False
    )
    # Enable WAL mode for better concurrent access
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


async def main():
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                        INCIDENT MANAGEMENT SYSTEM                        ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)
    await process_all_queue_items()


async def process_all_queue_items():
    ims = IncidentManagementSystem()

    print("🔍 Inspecting current queue state...\n")

    # 1️⃣ Print current status counts
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) FROM queue GROUP BY status;")
            print("📊 Queue status summary:")
            for status, count in cursor.fetchall():
                print(f"  {status}: {count}")
    except sqlite3.OperationalError as e:
        print(f"⚠️  Error reading queue status: {e}")

    # 2️⃣ Reset processed → pending
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE queue
                SET status='pending', processed_at=NULL
                WHERE LOWER(status)='processed'
            """)
            conn.commit()
            print(f"🔄 Reset {cursor.rowcount} 'processed' rows to 'pending'.")
    except sqlite3.OperationalError as e:
        print(f"⚠️  Error resetting processed rows: {e}")
        return

    # 3️⃣ Fetch pending items
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, data FROM queue
                WHERE status='pending'
                ORDER BY created_at ASC
            """)
            rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"⚠️  Error fetching pending items: {e}")
        return

    print(f"🟢 Found {len(rows)} pending incidents in queue.\n")
    if not rows:
        print("✅ No pending incidents. Exiting.\n")
        return

    # 4️⃣ Process each pending record
    for i, row in enumerate(rows, 1):
        queue_id = row["id"]
        try:
            payload = json.loads(row["data"])
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON in queue item {queue_id}, skipping.")
            continue

        print(f"\n📦 Processing queue item {i}/{len(rows)} → ID: {queue_id}")
        print("-" * 80)

        try:
            context = IncidentContext(
                business_hours=payload.get("business_hours", True),
                weekend=payload.get("weekend", False),
                peak_traffic_hours=payload.get("peak_traffic_hours", False),
                customer_facing=payload.get("customer_facing", True),
                revenue_impacting=payload.get("revenue_impacting", False)
            )

            print("--------- payload -------")
            print(payload)
            result = await ims.process_incident(payload,context)

            # ✅ Mark as processed with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE queue
                            SET status='processed', processed_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        """, (queue_id,))
                        conn.commit()
                        print(f"✅ Updated status for {queue_id} → processed")
                        break
                except sqlite3.OperationalError as e:
                    if attempt < max_retries - 1:
                        print(f"⚠️  Database locked, retrying... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(0.1 * (attempt + 1))
                    else:
                        print(f"❌ Failed to update status after {max_retries} attempts: {e}")

            print(f"✅ Completed queue item {i}/{len(rows)}")
            print(f"   Result: {result}\n")

        except Exception as e:
            print(f"❌ Error processing queue item {queue_id}: {e}\n")

        await asyncio.sleep(0.5)

    print("\n🎯 All pending incidents processed successfully.\n")


if __name__ == "__main__":
    asyncio.run(main())