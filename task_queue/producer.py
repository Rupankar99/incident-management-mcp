import threading
import time

class Producer(threading.Thread):
    """Producer thread that adds items to the queue."""
    
    def __init__(self, queue, producer_id: str, items: list):
        super().__init__(daemon=True)
        self.queue = queue
        self.producer_id = producer_id
        self.items = items
    
    def run(self):
        """Produce items into the queue."""
        for item in self.items:
            item_id = self.queue.enqueue(item)
            print(f"[{self.producer_id}] Produced: {item} (ID: {item_id[:8]}...)")
            time.sleep(0.5)
        
        print(f"[{self.producer_id}] Finished producing")
