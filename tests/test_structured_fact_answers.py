from _bootstrap import ensure_repo_root

ensure_repo_root()

import api
import services.chat as chat_service


class FakeRagEngine:
    def retrieve(self, query, top_k=5, filter_category=None, min_score=0.0):
        return []


class FakeKnowledgeBaseService:
    def public_sections(self):
        return {
            "overview": {
                "college": "MES Institute of Technology and Management",
                "location": "Chathannoor, Kollam, Kerala",
                "summary": "MES Institute of Technology and Management was established in 2009. The College is located at Kollam District near Thirumukku, Chathannoor, Kerala state.",
            },
            "departments": [
                {"name": "Department of Computer Science & Engineering"},
                {"name": "Department of Computer Science & Engineering (Artificial Intelligence)"},
            ],
            "faculty": [
                {
                    "name": "Dr. Vineetha G. R.",
                    "designation": "Head of Department",
                    "department": "Dept. of Computer Science & Engineering",
                    "source_url": "https://www.mesitam.ac.in/HoDs.php",
                },
                {
                    "name": "Prof. Saheer H.",
                    "designation": "Associate Professor & Head (SC&IS)",
                    "department": "Department of Computer Science & Engineering",
                    "source_url": "https://www.mesitam.ac.in/computer-science-and-engineering.php",
                }
            ],
            "courses": [],
            "facilities": [],
            "placements": [],
            "faqs": [],
            "events": [],
            "documents": [
                {
                    "title": "About MESITAM",
                    "source_url": "https://www.mesitam.ac.in/about.php",
                    "text": "Key Personnel\nDr. Shafi K. A. Principal\nProf. Rafi A Vice Principal\n",
                },
                {
                    "title": "Department of Computer Science & Engineering",
                    "source_url": "https://www.mesitam.ac.in/computer-science-and-engineering.php",
                    "text": "Head of Department\nDr. Vineetha G. R.\nDr. Vineetha G.R. Associate Professor & HOD\n",
                },
                {
                    "title": "Department of Computer Science & Engineering (Artificial Intelligence)",
                    "source_url": "https://www.mesitam.ac.in/computer-science-and-engineering-AI.php",
                    "text": "Head of Department\nProf. Basima Yoosaf\nProf. Basima Yoosaf Assistant Professor & HOD\n",
                },
            ],
            "updated_at": "2026-04-04T00:00:00",
            "index_version": "test-structured-facts",
        }


ORIGINAL_GET_RAG_ENGINE_SAFE = api.get_rag_engine_safe
ORIGINAL_QUERY_KG = api.query_kg
ORIGINAL_GENERATE_ANSWER = api.generate_answer
ORIGINAL_GET_KB_SERVICE = chat_service.get_knowledge_base_service


def restore_originals():
    api.get_rag_engine_safe = ORIGINAL_GET_RAG_ENGINE_SAFE
    api.query_kg = ORIGINAL_QUERY_KG
    api.generate_answer = ORIGINAL_GENERATE_ANSWER
    chat_service.get_knowledge_base_service = ORIGINAL_GET_KB_SERVICE


def assert_true(condition, message):
    assert condition, message


try:
    print("--- Running structured fact-answer checks ---")

    llm_calls = []

    def grounded_generator(question, context, history=None, stream=False, answer_mode=None, response_type=None):
        llm_calls.append((question, response_type))
        lowered = question.lower()
        if "principal" in lowered:
            yield "The principal of MESITAM is Dr. Shafi K. A."
        elif "hod" in lowered:
            yield "The Head of Department of Computer Science & Engineering is Dr. Vineetha G. R."
        elif "saheer" in lowered:
            yield "Prof. Saheer H. is Associate Professor & Head (SC&IS) in the Department of Computer Science & Engineering."
        else:
            yield "MESITAM is located in Kollam District near Thirumukku, Chathannoor, Kerala state."

    api.get_rag_engine_safe = lambda: FakeRagEngine()
    api.query_kg = lambda question: []
    api.generate_answer = grounded_generator
    chat_service.get_knowledge_base_service = lambda: FakeKnowledgeBaseService()

    principal = api.chat(api.ChatRequest(query="Who is the principal of MESITAM?", history=[]))
    print("Principal response:", principal["answer"])
    assert_true(principal["answer"] == "The principal of MESITAM is Dr. Shafi K. A.", "Principal should stay grounded while sounding natural.")

    hod = api.chat(api.ChatRequest(query="Who is the HOD of Computer Science & Engineering?", history=[]))
    print("HOD response:", hod["answer"])
    assert_true(hod["answer"] == "The Head of Department of Computer Science & Engineering is Dr. Vineetha G. R.", "HOD queries should resolve to the matching department leader.")
    assert_true(all("Basima" not in source.get("excerpt", "") for source in hod["sources"]), "Plain CSE HOD answers must not leak CSE(AI) evidence.")

    location = api.chat(api.ChatRequest(query="Where is MESITAM located?", history=[]))
    print("Location response:", location["answer"])
    assert_true(
        location["answer"] == "MESITAM is located in Kollam District near Thirumukku, Chathannoor, Kerala state.",
        "Location questions should use the explicit institutional location from the knowledge base.",
    )
    assert_true(len(location["sources"]) == 1, "Location facts should cite the structured overview source only.")

    saheer = api.chat(api.ChatRequest(query="Who is Saheer?", history=[]))
    print("Saheer response:", saheer["answer"])
    assert_true(
        saheer["answer"] == "Prof. Saheer H. is Associate Professor & Head (SC&IS) in the Department of Computer Science & Engineering.",
        "Named faculty questions should use structured faculty profiles instead of disclosure blobs.",
    )
    assert_true(
        saheer["sources"][0]["title"] == "Department of Computer Science & Engineering",
        "Named faculty answers should prioritize the structured faculty source.",
    )
    assert_true(
        "DateofBirth" not in saheer["answer"] and "AICTEid" not in saheer["answer"],
        "Named faculty answers must not leak raw mandatory-disclosure fields.",
    )
    assert_true(len(llm_calls) == 4, "Structured grounded fact answers should now use the LLM for final phrasing.")

    print("Structured fact-answer checks passed.")
finally:
    restore_originals()
