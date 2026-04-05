from _bootstrap import ensure_repo_root

ensure_repo_root()

import requests


print("--- Running NexRag API integration check ---")

status = requests.get("http://127.0.0.1:8000/api/status", timeout=30).json()
print("Status:", status)

payload = {"query": "Explain the KTU exam rules", "history": []}
response = requests.post("http://127.0.0.1:8000/api/chat", json=payload, timeout=180).json()

print("Status:", response.get("status"))
print("Confidence:", response.get("confidence"))
print("Confidence label:", response.get("confidence_label"))
print("Answer preview:", (response.get("answer") or "")[:220])

assert "answer" in response, "Integration response did not include an answer."
assert "status" in response and "sources" in response and "kg_facts" in response and "type" in response, "Integration response did not match the new schema."
print("Integration check completed.")
