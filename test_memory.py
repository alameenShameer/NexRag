import requests

URL = "http://127.0.0.1:8000/api/chat"

print("--- Testing NexRag Conversational Memory (RAG-Aware) ---")

# Turn 2 with forcefully injected memory about an arbitrary professor
payload = {
    "query": "What is his email?",
    "history": [
        {"role": "user", "content": "Who is the Head of Computer Science?"},
        {"role": "assistant", "content": "The Head of Computer Science is Dr. Alan Mathew. His contact email is alan.mathew@mesitam.ac.in."}
    ]
}

print("\n🤖 Sending turn with pronoun 'his':", payload["query"])
resp = requests.post(URL, json=payload).json()
ans = resp.get("answer", "ERROR")
print("   Response:", ans.strip())

if "alan.mathew@mesitam.ac.in" in ans.lower() or "alan" in ans.lower():
    print("\n✅ SUCCESS: The AI perfectly remembered Dr. Alan's details using the conversational history!")
else:
    print("\n❌ FAILED: The AI lost the context of the previous turn.")
