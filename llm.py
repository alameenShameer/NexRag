import ollama

def generate_answer(question, context):
    prompt = f"""
    Answer ONLY using the context.
    If not present say "I don't know".

    Context:
    {context}

    Question:
    {question}
    """

    response = ollama.chat(
        model="mistral:7b-instruct-q4_K_M",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.4}
    )

    return response["message"]["content"]
