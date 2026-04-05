import sys
import asyncio
from api import build_chat_payload
from services.chat import chat_response_from_payload
from llm import generate_answer

def test_question(question, answer_mode=None):
    print(f"--- TESTING: {question} ---")
    payload = build_chat_payload(question, [], answer_mode)
    response = chat_response_from_payload(
        question, 
        payload, 
        answer_mode, 
        [], 
        generate_answer_fn=generate_answer
    )
    print("INTENT:", payload.get("intent", []))
    print("RETRIEVED CHUNKS:", len(payload.get("retrieval_trace", {}).get("passes", [{}])[-1].get("candidates", [])) if "retrieval_trace" in payload else "N/A")
    print("ANSWER GENERATED:")
    print(response.get("answer", ""))
    print("Token length roughly:", len(response.get("answer", "").split()))
    print("="*60, "\n")

questions = [
    "Who is the HOD of Computer Science & Engineering at MESITAM?",
    "What does the MESITAM digital library provide?",
    "Explain the full process of university registration, attendance regulation, and grading in detail according to the KTU curriculum and MESITAM rules.",
]

for q in questions:
    test_question(q)
