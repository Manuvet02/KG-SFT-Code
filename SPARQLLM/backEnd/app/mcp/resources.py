import json

from mcp_instance import mcp
from graphdb_client import run_query, shorten_uri

PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "ex": "http://www.semanticweb.org/KG-SFT#",
}

@mcp.resource("schema://ontology/prefixes", name="Ontology Prefixes")
async def get_ontology_prefixes() -> str:
    """
    Espone i prefissi/namespace noti usati nel knowledge graph.
    Utile per interpretare gli URI abbreviati restituiti dagli altri tool e per costruire query SPARQL raw corrette.
    """
    return json.dumps(PREFIXES, indent=2, ensure_ascii=False)


@mcp.resource("schema://ontology/classes", name="List Classes")
async def get_ontology_classes_overview() -> str:
    ''' 
        Espone una panoramica delle classi del grafo con conteggio istanze.
        Fornisce la 'mappa' dello schema senza dover chiamare esplicitamente il tool sparqllm_list_classes.
    '''
    sparql = """
        SELECT ?class (COUNT(?instance) AS ?count) WHERE {
        ?instance a ?class .
        }
        GROUP BY ?class
        ORDER BY DESC(?count)
    """

    data = await run_query(sparql)
    bindings = data["results"]["bindings"]
    results = [
        {"class": shorten_uri(b["class"]["value"], PREFIXES), "instance_count": int(b["count"]["value"])}
        for b in bindings
    ]
    return json.dumps(results, indent=2, ensure_ascii=False)


@mcp.resource("schema://ontology/properties", name="List Properties")
async def get_ontology_properties_overview() -> str:
    """
        Espone tutte le proprietà (predicati) distinte usate nel grafo, con conteggio utilizzi.
        Aiuta a scoprire quali relazioni sono disponibili per sparqllm_get_related_entities senza doverle indovinare.
    """

    sparql = """
        SELECT ?p (COUNT(*) AS ?count) WHERE {
            ?s ?p ?o .
        }
        GROUP BY ?p
        ORDER BY DESC(?count)
    """

    data = await run_query(sparql)
    bindings = data["results"]["bindings"]
    results = [
        {"property": shorten_uri(b["p"]["value"], PREFIXES), "usage_count": int(b["count"]["value"])}
        for b in bindings
    ]
    return json.dumps(results, indent=2, ensure_ascii=False)