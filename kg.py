from SPARQLWrapper import SPARQLWrapper, JSON
import re

# Updated Endpoint for MESITAM KG
FUSEKI_ENDPOINT = "http://localhost:3030/mesitam_kg/sparql"

STOPWORDS = {
    "what", "is", "who", "describe", "tell", "me", "about", "details", "of",
    "the", "for", "rule", "define", "meaning", "course", "subject", "faculty",
    "teacher", "teaches", "taught", "instructor", "department", "professor"
}


def _extract_search_terms(question):
    cleaned = question.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    tokens = [token for token in cleaned.split() if token not in STOPWORDS]
    joined = " ".join(tokens).strip()

    phrases = []
    if joined:
        phrases.append(joined)

    for size in range(min(4, len(tokens)), 0, -1):
        for start in range(0, len(tokens) - size + 1):
            phrase = " ".join(tokens[start:start + size]).strip()
            if phrase and phrase not in phrases:
                phrases.append(phrase)

    return phrases

def query_kg(question):
    sparql = SPARQLWrapper(FUSEKI_ENDPOINT)

    keywords = _extract_search_terms(question)
    if not keywords:
        return None

    print(f"DEBUG: Searching KG for {keywords}")
    bindings = []

    for keyword in keywords:
        if len(keyword) < 2:
            continue

        # Improved query: Search in Name OR Code OR Abbreviation
        # Also fetch INCOMING relationships (e.g., Who teaches this?)
        query = f"""
        PREFIX : <http://mesitam.ac.in/ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?label ?type ?desc ?prop ?valname ?invProp ?invValName WHERE {{
            {{ ?entity :hasName ?label . }} 
            UNION {{ ?entity :hasCode ?label . }}
            UNION {{ ?entity :abbreviation ?label . }}
            
            ?entity a ?type .
            
            OPTIONAL {{ ?entity :description ?desc . }}
            
            OPTIONAL {{ 
                ?entity ?prop ?val . 
                FILTER(?prop != :hasName && ?prop != rdf:type && ?prop != :description && ?prop != :hasCode && ?prop != :abbreviation)
                OPTIONAL {{ ?val :hasName ?valLabel . }} 
                BIND(COALESCE(?valLabel, str(?val)) AS ?valname) 
            }}
            
            OPTIONAL {{
                ?invVal ?invProp ?entity .
                FILTER(?invProp != rdf:type)
                OPTIONAL {{ ?invVal :hasName ?invLabel . }}
                BIND(COALESCE(?invLabel, str(?invVal)) AS ?invValName)
            }}
            
            FILTER (CONTAINS(LCASE(?label), "{keyword}"))
        }} LIMIT 20
        """

        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)

        try:
            results = sparql.query().convert()
        except Exception as e:
            print(f"Warning: KG Connection Failed. {e}")
            return None

        bindings = results["results"]["bindings"]
        if bindings:
            break

    if not bindings:
        return None

    # Format the answer
    # We aggregate properties for the entity
    entity_info = {}
    
    for row in bindings:
        label = row["label"]["value"]
        type_uri = row["type"]["value"].split("#")[-1]
        
        if label not in entity_info:
            entity_info[label] = {
                "type": type_uri, 
                "desc": row["desc"]["value"] if "desc" in row else None,
                "props": []
            }
        
        # Outgoing
        if "prop" in row:
            prop_name = row["prop"]["value"].split("#")[-1]
            val_text = row["valname"]["value"]
            prop_str = f"{prop_name}: {val_text}"
            if prop_str not in entity_info[label]["props"]:
                entity_info[label]["props"].append(prop_str)
                
        # Incoming (Inverse)
        if "invProp" in row:
            inv_prop_name = row["invProp"]["value"].split("#")[-1]
            inv_val_text = row["invValName"]["value"]
            # Format as "teaches -> Dr. Anitha" or better "taught by: Dr. Anitha"
            # For now, generic: "is [prop] of [value]"
            inv_str = f"is {inv_prop_name} of: {inv_val_text}"
            if inv_prop_name == "teaches":
                inv_str = f"Taught by: {inv_val_text}" # Special handling for common ones
            elif inv_prop_name == "hasHOD":
                 inv_str = f"Is HOD of: {inv_val_text}"
            
            if inv_str not in entity_info[label]["props"]:
                entity_info[label]["props"].append(inv_str)

    # Construct text response
    response_parts = []
    for label, info in entity_info.items():
        text = f"**{label}** ({info['type']})"
        if info["desc"]:
            text += f"\n\n{info['desc']}"
        if info["props"]:
            text += "\n\n**Details:**\n- " + "\n- ".join(info["props"])
        response_parts.append(text)
        
    return "\n\n---\n\n".join(response_parts)
