import time
from jobs_queue import SQLiteQueue
from producer import Producer
from consumer import Consumer

def main():
    """Demo of the SQLite queue system."""
    print("=== SQLite Queue System Demo ===\n")
    
    queue = SQLiteQueue("demo_queue.db")
    
    producer1 = Producer(queue, "Producer-1", [
        {"task": "task-1", "data": "Process report A"},
        {"task": "task-2", "data": "Send email"},
        {"task": "task-3", "data": "Update database"},
    ])
    
    producer2 = Producer(queue, "Producer-2", [
        {"task": "task-4", "data": "Generate invoice"},
        {"task": "task-5", "data": "Backup files"},
        {"task": "task-6", "data": "Clean temp directory"},
    ])
    
    consumer1 = Consumer(queue, "Consumer-1", max_items=3)
    consumer2 = Consumer(queue, "Consumer-2", max_items=3)
    
    print("Starting producers and consumers...\n")
    producer1.start()
    producer2.start()
    
    time.sleep(1)
    
    consumer1.start()
    consumer2.start()
    
    producer1.join()
    producer2.join()
    consumer1.join()
    consumer2.join()
    
    print("\n=== Final Queue Statistics ===")
    stats = queue.get_stats()
    for status, count in stats.items():
        print(f"{status.capitalize()}: {count}")

if __name__ == "__main__":
    main()
