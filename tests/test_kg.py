from _bootstrap import ensure_repo_root

repo_root = ensure_repo_root()

import json
from pathlib import Path

from kg import query_kg
from router import get_intent


queries = [
    "define seminar",
    "what is a project",
    "who teaches Computer Graphics?",
    "what is the minimum attendance rule",
    "define quantum physics",
]

results = []
print("Running knowledge graph checks...\n")

for query in queries:
    intent = get_intent(query)
    kg_result = None
    if intent in {"FACULTY_INFO", "COURSE_INFO", "REGULATION", "DEFINITION"}:
        kg_result = query_kg(query)

    results.append(
        {
            "query": query,
            "intent": intent,
            "found_in_kg": bool(kg_result),
            "snippet": kg_result[:160] if kg_result else None,
        }
    )
    print(f"{query!r} -> intent={intent}, found_in_kg={bool(kg_result)}")

local_dir = repo_root / "local"
local_dir.mkdir(exist_ok=True)
with open(local_dir / "test_results.json", "w", encoding="utf-8") as file_handle:
    json.dump(results, file_handle, indent=2)

print("\nKG checks completed. Results saved to local/test_results.json")
