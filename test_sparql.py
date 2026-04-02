from SPARQLWrapper import SPARQLWrapper, JSON

sparql = SPARQLWrapper("http://localhost:3030/mesitam_kg/sparql")
query = """
    PREFIX : <http://mesitam.ac.in/ns#>
    
    SELECT ?label WHERE {
        ?entity :hasName ?label .
    }
"""
sparql.setQuery(query)
sparql.setReturnFormat(JSON)

try:
    results = sparql.query().convert()
    labels = [r["label"]["value"] for r in results["results"]["bindings"]]
    print("Labels in KG:", labels)
except Exception as e:
    print("Error:", e)
