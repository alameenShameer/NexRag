import os
import csv
import json
from datetime import datetime

LOG_FILE = "logs/query_history.csv"
TRACE_LOG_FILE = "logs/query_trace.jsonl"
os.makedirs("logs", exist_ok=True)

def log_interaction(question, answer, intent, latency=0.0, metadata=None):
    file_exists = os.path.isfile(LOG_FILE)
    
    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        # Write header if new file
        if not file_exists:
            writer.writerow(["Timestamp", "Question", "Intent", "Latency (s)", "Answer"])
            
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            question,
            intent,
            f"{latency:.2f}",
            answer
        ])

    trace_entry = {
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "answer": answer,
        "intent": intent,
        "latency_seconds": round(float(latency), 4),
        "metadata": metadata or {},
    }
    try:
        with open(TRACE_LOG_FILE, "a", encoding="utf-8") as trace_handle:
            trace_handle.write(json.dumps(trace_entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

def log_query(query, source, confidence):
    try:
        with open("logs/query_history.txt", "a", encoding="utf-8") as f:
            f.write(
                f"{datetime.now()} | Query: {query} | "
                f"Source: {source} | Confidence: {confidence}\n"
            )
    except Exception:
        pass
