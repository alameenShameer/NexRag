import re
import difflib

KNOWN_TERMS = [
    "seminar",
    "project",
    "internship",
    "viva",
    "marks",
    "duration",
    "mandatory",
    "ktu",
    "btech"
]

def correct_spelling(query):
    words = query.split()
    corrected_words = []
    correction_made = False

    for word in words:
        lower_word = word.lower()

        # Do NOT correct short words (avoid acronym distortion)
        if len(lower_word) <= 3:
            corrected_words.append(word)
            continue

        match = difflib.get_close_matches(
            lower_word,
            KNOWN_TERMS,
            n=1,
            cutoff=0.8
        )

        if match and lower_word != match[0]:
            if abs(len(lower_word) - len(match[0])) <= 2:
                corrected_words.append(match[0])
                correction_made = True
            else:
                corrected_words.append(word)
        else:
            corrected_words.append(word)

    corrected_query = " ".join(corrected_words)
    return corrected_query, correction_made

def get_intent(question):
    question = question.lower()
    
    # 1. Faculty / Staff Info (KG)
    # Added "teaches", "instructor", "hod" to catch role-based queries
    if any(x in question for x in ["who is", "hod", "professor", "teacher", "teaches", "taught", "instructor", "faculty", "staff", "principal", "contact"]):
        return "FACULTY_INFO"
        
    # 2. Course / Syllabus Info (KG + Docs)
    if any(x in question for x in ["syllabus", "module", "textbook", "reference", "credit", "course", "subject", "code"]):
        return "COURSE_INFO"
        
    # 3. Regulations / Rules (Docs)
    if any(x in question for x in ["rule", "regulation", "attendance", "mark", "grade", "pass", "fail", "exam", "duty leave", "condonation"]):
        return "REGULATION"

    # 4. Definitions & Explanations
    if any(x in question for x in ["define", "what is", "meaning"]):
        return "DEFINITION"

    if any(x in question for x in ["explain", "describe", "summary", "summarize", "how ", "why "]):
        return "GENERAL"
    
    if "compare" in question or "difference" in question:
        return "COMPARISON"
        
    return "GENERAL"
