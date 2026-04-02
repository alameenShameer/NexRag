import sys
import os
sys.path.append(os.getcwd())

from router import get_intent
from kg import query_kg

queries = [
    # Should exist in KG
    "define seminar",
    "what is a project",
    "who is Prof. Aisha",
    "CST304 details",
    
    # Should be routed to KG but data NOT in KG
    "define quantum physics",
    "who is Albert Einstein",
    "what is mechanical engineering", # 'mechanical engineering' department is in KG, but will it match perfectly? Let's trace.

    # Should NOT be routed to KG
    "how to login to portal",
    "compare CSE and ME",
]

import json

results_list = []
print("Starting tests...\n")

for q in queries:
    intent = get_intent(q)
    
    kg_result = None
    if intent in ["FACULTY_INFO", "COURSE_INFO", "REGULATION", "DEFINITION"]:
        kg_result = query_kg(q)

    route_to_kg = "YES" if intent in ["FACULTY_INFO", "COURSE_INFO", "REGULATION", "DEFINITION"] else "NO"
    found_in_kg = "YES" if kg_result else "NO"
    
    results_list.append({
        "Query": q,
        "Intent": intent,
        "RoutedToKG": route_to_kg,
        "FoundInKG": found_in_kg,
        "Snippet": kg_result[:100] if kg_result else None
    })

with open("test_results.json", "w") as f:
    json.dump(results_list, f, indent=2)
