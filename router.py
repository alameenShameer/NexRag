def is_definition_query(question):
    return question.lower().startswith(
        ("what is", "define", "definition of", "meaning of")
    )
