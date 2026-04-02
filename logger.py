import os
import csv
from datetime import datetime

LOG_FILE = "logs/query_history.csv"
os.makedirs("logs", exist_ok=True)

def log_interaction(question, answer, intent, latency=0.0):
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

def log_query(query, source, confidence):
    try:
        with open("logs/query_history.txt", "a", encoding="utf-8") as f:
            f.write(
                f"{datetime.now()} | Query: {query} | "
                f"Source: {source} | Confidence: {confidence}\n"
            )
    except Exception:
        pass
