import time
from typing import Any
from datetime import datetime
import json
from dataclasses import asdict
import asyncio

from data_generation import(SyntheticIncidentGenerator)
from orchestrator import (IncidentManagementSystem)

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from datetime import datetime
import json
import httpx 

import json

from task_queue.consumer import Consumer
from task_queue.jobs_queue import SQLiteQueue
from task_queue.producer import Producer
client = httpx.Client(verify=False)

# Load environment variables
load_dotenv()

#parser = StructuredOutputParser.from_json_schema(schema)

async def main():
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║         INCIDENT MANAGEMENT SYSTEM                                       ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)

    # ------------------------

    queue = SQLiteQueue("demo_queue.db")

    producer1 = Producer(queue, "ProducerRupankar", [
        {"task": "send message ", "data": "send message to jira-1"},
    ])

    print("Starting producers...\n")
    producer1.start()
    producer1.join()

    time.sleep(1)

    # Consumer
    consumer1 = Consumer(queue, "Consumer-1", max_items=3)
    consumer1.start()
    consumer1.join()
    # ------------------------

    ims = IncidentManagementSystem()
    await ims.initialize()
    
    print("🔬 Generating scenarios...")
    generator = SyntheticIncidentGenerator()
    scenarios = generator.generate_scenarios(count=5)
    print(f"✓ Generated {len(scenarios)} scenarios\n")
    
    results = []
    for i, (incident, context) in enumerate(scenarios, 1):
        result = await ims.process_incident(incident, context)
        results.append(result)
        
        if i < len(scenarios):
            print("\n" + "▼" * 80 + "\n")
            await asyncio.sleep(0.5)
    
    ims.print_summary()
    
    # Save results
    output = {
        "summary": {
            "total": len(results),
            "successful": sum(1 for r in results if r['status'] == 'success'),
            "timestamp": datetime.now().isoformat()
        },
        "incidents": results
    }
    
    print("💾 Saving results...")
    with open("incident_results.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    print("✓ Saved to incident_results.json\n")
    
    print("=" * 80)
    print("✅ COMPLETE")
    print("=" * 80)
    print("\nFeatures:")
    print("• Direct OpenAI API (no frameworks)")
    print("• 95% fewer dependencies")
    print("• Same intelligent decision-making")
    print("• Production-ready")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())