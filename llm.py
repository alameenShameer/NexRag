import ollama

MODEL_NAME = "llama3.2:3b"


def get_llm_info():
    return {
        "provider": "ollama",
        "model": MODEL_NAME,
    }

def generate_answer(question, context, history=None):
    if history is None:
        history = []
    system_prompt = f"""You are the official AI Academic Assistant for MES Institute of Technology and Management.
You must answer the User's question using the Context below. If the Context lacks the answer, use the Conversation History to resolve pronouns (e.g., 'he', 'that module') or missing details.
If the answer cannot be logically deduced from the Context or History, explicitly say "I don't know".

Guidelines:
- Start with the most direct answer possible.
- Never guess, invent faculty names, or fill gaps with likely-sounding details.
- If the context only gives a partial answer, clearly separate what is known from what is unknown.
- Prefer short paragraphs or flat bullet lists over long filler text.
- Mention the source basis briefly, such as "According to the knowledge graph" or "From the uploaded documents", when helpful.
- Always keep the tone confident but honest.

Context:
{context}
"""

    # Build discrete roles for Llama 3 instruct mapping
    messages_list = [{"role": "system", "content": system_prompt}]
    
    for h in history:
        role = "assistant" if h.get("role") == "assistant" else "user"
        messages_list.append({"role": role, "content": h.get("content", "")})
    
    # Append the raw user query
    messages_list.append({"role": "user", "content": question})

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=messages_list,
            stream=False,
            options={
                "temperature": 0.2,
                "num_ctx": 2048, 
                "num_predict": 384
            }
        )
        yield response["message"]["content"]
    except Exception as e:
        yield f"LLM Generation Error: {str(e)}"
