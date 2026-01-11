from SPARQLWrapper import SPARQLWrapper, JSON

FUSEKI_ENDPOINT = "http://localhost:3030/university_faq/sparql"

def query_kg(question):
    sparql = SPARQLWrapper(FUSEKI_ENDPOINT)

    keyword = question.lower().replace("what is", "").replace("define", "").strip()

    sparql.setQuery(f"""
    PREFIX : <http://example.org/unifaq#>
    SELECT ?answer WHERE {{
        ?faq a :FAQ ;
             :hasQuestion ?q ;
             :hasAnswer ?a .
        ?q :text ?question .
        ?a :text ?answer .
        FILTER (CONTAINS(LCASE(?question), "{keyword}"))
    }} LIMIT 1
    """)

    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    if results["results"]["bindings"]:
        return results["results"]["bindings"][0]["answer"]["value"]

    return None
