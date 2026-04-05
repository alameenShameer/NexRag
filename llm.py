import ollama

from services.pipeline_v2.prompts import answer_style_for, build_system_prompt

MODEL_NAME = "llama3.2:3b"


def get_llm_info():
    return {
        "provider": "ollama",
        "model": MODEL_NAME,
    }

def generate_answer(question, context, history=None, stream=False, response_type="explanation", answer_mode=None):
    if history is None:
        history = []
    _ = answer_mode
    _, num_predict = answer_style_for(response_type)
    system_prompt = build_system_prompt(context=context, response_type=response_type)

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
            stream=stream,
            options={
                "temperature": 0.0,
                "num_ctx": 8192, 
                "num_predict": num_predict
            }
        )
        if stream:
            for chunk in response:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content
            return

        yield response["message"]["content"]
    except Exception as e:
        yield f"LLM Generation Error: {str(e)}"
