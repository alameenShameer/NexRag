import requests


targets = [
    ("Frontend", "http://127.0.0.1:5173"),
    ("Backend", "http://127.0.0.1:8000/api/status"),
    ("Fuseki", "http://localhost:3030"),
]


print("--- NexRag Health Check ---")
for name, url in targets:
    try:
        response = requests.get(url, timeout=5)
        print(f"{name}: {response.status_code} ({url})")
    except Exception as error:
        print(f"{name}: DOWN ({url}) -> {error}")
