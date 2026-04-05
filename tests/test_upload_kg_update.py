from _bootstrap import ensure_repo_root

ensure_repo_root()

from services.pipeline_v2.query_understanding import build_query_plan
from services.upload_kg import get_upload_kg_service


print("--- Running upload KG update checks ---")

service = get_upload_kg_service()
payload = service.rebuild_from_uploads()

print("Upload KG documents:", len(payload.get("documents", [])))
print("Upload KG entities:", [item.get("label") for item in payload.get("entities", [])])

neuronest_facts = service.query_facts("what is neuro nest")
print("NeuroNest upload KG facts:", neuronest_facts)
assert neuronest_facts, "Uploaded PDFs should contribute facts to the KG."
assert "NeuroNest" in neuronest_facts[0]["entity"], "Spaced compound upload queries should resolve to NeuroNest."

query_plan = build_query_plan("what is neuro nest", [])
print("Upload KG query-plan entities:", query_plan.to_dict().get("entities"))
assert any(item.get("label") == "NeuroNest" for item in query_plan.to_dict().get("entities", [])), "Upload KG entities should participate in query understanding."

print("Upload KG update checks passed.")
