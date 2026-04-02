import ollama

def generate_answer(question, context, history=None):
    if history is None:
        history = []
    system_prompt = f"""You are the official AI Academic Assistant for MES Institute of Technology and Management.
You must answer the User's question using the Context below. If the Context lacks the answer, use the Conversation History to resolve pronouns (e.g., 'he', 'that module') or missing details.
If the answer cannot be logically deduced from the Context or History, explicitly say "I don't know".

Guidelines:
- Provide a detailed and comprehensive answer.
- Explain concepts clearly.
- Use standard markdown bullet points (e.g., starting with '-') if listing information.
- CRUCIAL: Always add a blank line between paragraphs and before/after lists to ensure correct alignment and spacing.

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
            model="llama3.2:3b",
            messages=messages_list,
            stream=False,
            options={
                "temperature": 0.5, # Slightly more creative for better flow
                "num_ctx": 2048, 
                "num_predict": 512  # Allow for longer responses
            }
        )
        yield response["message"]["content"]
    except Exception as e:
        yield f"LLM Generation Error: {str(e)}"
