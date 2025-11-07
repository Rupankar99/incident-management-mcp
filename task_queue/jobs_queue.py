import json
import uuid
import threading
from typing import Any, Optional
from .db_init import init_db, get_connection

class SQLiteQueue:
    """Thread-safe queue implementation using SQLite3."""
    
    def __init__(self, db_path: str = "queue.db"):
        self.db_path = db_path
        init_db(self.db_path)
        self.lock = threading.Lock()
    
    def enqueue(self, data: Any) -> str:
        """Add an item to the queue."""
        item_id = str(uuid.uuid4())
        data_json = json.dumps(data)
        
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO queue (id, data) VALUES (?, ?)", (item_id, data_json))
        conn.commit()
        conn.close()
        
        return item_id
    
    def dequeue(self, consumer_id: str) -> Optional[tuple[str, Any]]:
        """Fetch and lock an item from the queue for a specific consumer."""
        with self.lock:
            conn = get_connection(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, data FROM queue 
                WHERE status = 'pending' 
                ORDER BY created_at ASC 
                LIMIT 1
            """)
            row = cursor.fetchone()
            
            if row:
                item_id = row['id']
                data = json.loads(row['data'])
                
                cursor.execute("""
                    UPDATE queue 
                    SET status = 'processing', consumer_id = ? 
                    WHERE id = ?
                """, (consumer_id, item_id))
                conn.commit()
                conn.close()
                
                return (item_id, data)
            
            conn.close()
            return None
    
    def complete(self, item_id: str):
        """Mark an item as completed."""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE queue 
            SET status = 'completed', processed_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (item_id,))
        conn.commit()
        conn.close()
    
    def fail(self, item_id: str):
        """Requeue a failed item."""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE queue 
            SET status = 'pending', consumer_id = NULL 
            WHERE id = ?
        """, (item_id,))
        conn.commit()
        conn.close()
    
    def get_stats(self) -> dict:
        """Get queue status counts."""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) as count FROM queue GROUP BY status")
        stats = {row['status']: row['count'] for row in cursor.fetchall()}
        conn.close()
        return stats
