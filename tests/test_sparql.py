from _bootstrap import ensure_repo_root

ensure_repo_root()

from SPARQLWrapper import JSON, SPARQLWrapper


sparql = SPARQLWrapper("http://localhost:3030/mesitam_kg/sparql")
sparql.setQuery(
    """
    PREFIX : <http://mesitam.ac.in/ns#>

    SELECT ?label WHERE {
        ?entity :hasName ?label .
    }
    LIMIT 10
    """
)
sparql.setReturnFormat(JSON)

try:
    results = sparql.query().convert()
    labels = [row["label"]["value"] for row in results["results"]["bindings"]]
    print("Sample KG labels:", labels)
except Exception as error:
    print("SPARQL check failed:", error)
