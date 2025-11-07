import threading
import time

class Consumer(threading.Thread):
    """Consumer thread that processes items from the queue."""
    
    def __init__(self, queue, consumer_id: str, max_items: int = None):
        super().__init__(daemon=True)
        self.queue = queue
        self.consumer_id = consumer_id
        self.max_items = max_items
        self.processed = 0
        self.running = True
    
    def run(self):
        """Continuously consume items from the queue."""
        while self.running:
            if self.max_items and self.processed >= self.max_items:
                break
            
            item = self.queue.dequeue(self.consumer_id)
            
            if item:
                item_id, data = item
                try:
                    print(f"[{self.consumer_id}] Processing: {data}")
                    time.sleep(1)
                    self.queue.complete(item_id)
                    self.processed += 1
                    print(f"[{self.consumer_id}] Completed: {data}")
                except Exception as e:
                    print(f"[{self.consumer_id}] Error: {e}")
                    self.queue.fail(item_id)
            else:
                time.sleep(0.5)
        
        print(f"[{self.consumer_id}] Finished consuming ({self.processed} items)")
    
    def stop(self):
        """Stop consumer gracefully."""
        self.running = False
