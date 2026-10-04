# tools.py
import asyncio
import json
from typing import Annotated, Optional

import httpx
from pydantic import Field
from sparql_llm import validate_sparql_with_void

from mcp_instance import mcp
from graphdb_client import run_query, shorten_uri, GRAPHDB_ENDPOINT
from openrouter_client import ask_llm
from agentClient import agent

PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "ex": "http://www.semanticweb.org/KG-SFT#",
}
SFT_NS = PREFIXES["ex"]
SFT_PREFIX = f"PREFIX sft: <{SFT_NS}>"


#Espande un URI abbreviato nel suo URI completo."""
def _expand_uri(uri: str) -> str:
    if ":" in uri and not uri.startswith("http"):
        prefix, local = uri.split(":", 1)
        if prefix in PREFIXES:
            return PREFIXES[prefix] + local
    return uri

# sparqllm_search_entity
@mcp.tool(
    name="Search Entity",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def sparqllm_search_entity(
    label: Annotated[str, Field(description="Testo da cercare nel label dell'entità", min_length=1)],
    limit: Annotated[int, Field(description="Numero massimo di risultati", ge=1, le=100)] = 20,
) -> str:
    """
        Cerca entità nel knowledge graph in base alla label.
        Risultato : JSON con lista di {uri, label} trovati.
    """
    sparql = f"""
        SELECT ?s ?label 
        WHERE {{
            ?s rdfs:label ?label .
            FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{label}")))
        }} 
        LIMIT {limit}
    """
    data = await run_query(sparql)
    results = [
        {"uri": shorten_uri(b["s"]["value"], PREFIXES), "label": b["label"]["value"]}
        for b in data["results"]["bindings"]
    ]
    if not results:
        return f"Nessuna entità trovata per '{label}'. Prova un termine più generico."
    return json.dumps(results, indent=2, ensure_ascii=False)


# sparqllm_get_entity_properties
@mcp.tool(
    name="Entity Properties",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def sparqllm_get_entity_properties(
    uri: Annotated[str, Field(description="URI completo o abbreviato dell'entità", min_length=1)],
) -> str:
    """
        Restituisce tutte le proprietà e i valori associati a un'entità.
        Risultato : JSON con lista di {property, value} oppure messaggio di errore se l'URI non esiste.
    """
    full_uri = _expand_uri(uri)
    sparql = f"""
        SELECT ?p ?o 
        WHERE {{
            <{full_uri}> ?p ?o .
        }}
    """
    data = await run_query(sparql)
    bindings = data["results"]["bindings"]
    if not bindings:
        return f"Errore: nessuna proprietà trovata per '{uri}'. Verifica che l'URI sia corretto (usa 'Search Entity' prima)."
    results = [
        {"property": shorten_uri(b["p"]["value"], PREFIXES), "value": b["o"]["value"]}
        for b in bindings
    ]
    return json.dumps(results, indent=2, ensure_ascii=False)


# sparqllm_list_classes
@mcp.tool(
    name="List Classes",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def sparqllm_list_classes(
    limit: Annotated[int, Field(description="Numero massimo di classi da restituire", ge=1, le=200)] = 50,
) -> str:
    """
        Elenca le classi (rdf:type owl:Class o rdfs:Class) presenti nel grafo, con conteggio istanze.

        Risultato : JSON con lista di {class, instance_count}, ordinata per conteggio decrescente.
    """
    sparql = f"""
        SELECT ?class (COUNT(?instance) AS ?count) 
        WHERE {{
            ?instance a ?class .
        }}
        GROUP BY ?class
        ORDER BY DESC(?count)
        LIMIT {limit}
    """
    data = await run_query(sparql)
    bindings = data["results"]["bindings"]
    if not bindings:
        return "Nessuna classe trovata nel grafo. Verifica che il repository GraphDB non sia vuoto."
    results = [
        {"class": shorten_uri(b["class"]["value"], PREFIXES), "instance_count": int(b["count"]["value"])}
        for b in bindings
    ]
    return json.dumps(results, indent=2, ensure_ascii=False)


# sparqllm_get_related_entities
VALID_DIRECTIONS = ("outgoing", "incoming", "both")
@mcp.tool(
    name="Related Entities",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def sparqllm_get_related_entities(
    uri: Annotated[str, Field(description="URI completo o abbreviato dell'entità di partenza", min_length=1)],
    property: Annotated[
        Optional[str],
        Field(description="Proprietà specifica da seguire. Se omessa, restituisce tutte le relazioni."),
    ] = None,
    direction: Annotated[
        str,
        Field(description="Direzione della relazione: 'outgoing', 'incoming' o 'both'"),
    ] = "both",
    limit: Annotated[int, Field(description="Numero massimo di risultati", ge=1, le=100)] = 30,
) -> str:
    """
        Trova entità collegate a un'entità data, opzionalmente filtrando per proprietà e direzione.
        Risultato : JSON con lista di {direction, property, related_uri}, oppure messaggio di errore.
    """
    if direction not in VALID_DIRECTIONS:
        return f"Errore: direction deve essere una tra {VALID_DIRECTIONS}, ricevuto '{direction}'."

    full_uri = _expand_uri(uri)
    prop_filter = f"<{_expand_uri(property)}>" if property else "?p"

    clauses = []
    if direction in ("outgoing", "both"):
        clauses.append(
            f'{{ <{full_uri}> {prop_filter} ?related . BIND("outgoing" AS ?dir) BIND({prop_filter if property else "?p"} AS ?relProp) }}'
        )
    if direction in ("incoming", "both"):
        clauses.append(
            f'{{ ?related {prop_filter} <{full_uri}> . BIND("incoming" AS ?dir) BIND({prop_filter if property else "?p"} AS ?relProp) }}'
        )

    union_block = " UNION ".join(clauses)
    sparql = f"""
        SELECT ?dir ?relProp ?related 
        WHERE {{
            {union_block}
        }}
        LIMIT {limit}
    """
    data = await run_query(sparql)
    bindings = data["results"]["bindings"]
    if not bindings:
        return f"Nessuna relazione trovata per '{uri}'{' con la proprietà specificata' if property else ''}."
    results = [
        {
            "direction": b["dir"]["value"],
            "property": shorten_uri(b["relProp"]["value"], PREFIXES),
            "related_uri": shorten_uri(b["related"]["value"], PREFIXES),
        }
        for b in bindings
    ]
    return json.dumps(results, indent=2, ensure_ascii=False)


# sparqllm_summarize_results
@mcp.tool(
    name="Summarize Results",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
)
async def sparqllm_summarize_results(
    data: Annotated[
        str,
        Field(description="Dati da riassumere: stringa JSON (es. output di altri tool SPARQL) oppure testo semplice", min_length=1),
    ],
) -> str:
    """
    Riassume in linguaggio naturale un blocco di risultati usando un modello LLM via OpenRouter.
    Il parametro data va passato come testo: se è un JSON valido viene usato così com'è, altrimenti viene trattato come testo semplice da riassumere.

    Risultato : Riassunto testuale generato dal modello.
    """

    try:
        json.loads(data)
        data_str = data
    except json.JSONDecodeError:
        data_str = data

    prompt = f"Riassumi in italiano, in modo chiaro e conciso, questi dati:\n\n{data_str}"
    try:
        summary = await ask_llm(prompt, system="Sei un assistente che riassume dati di knowledge graph in modo leggibile.")
    except httpx.HTTPStatusError as e:
        return f"Errore chiamata OpenRouter: {e.response.status_code}. Verifica la chiave API o il nome del modello."
    return summary


# Generate Query

@mcp.tool(
    name="Generate Query",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
)
async def sparqllm_generate_query(
    question: Annotated[str, Field(description="Domanda in linguaggio naturale da tradurre in SPARQL su KG-SFT", min_length=1)],
) -> str:
    """
    Traduce una domanda in linguaggio naturale in una query SPARQL per KG-SFT.

    Usa SparqLLMAgent: recupera few-shot examples pertinenti, genera la query
    con l'LLM, e la corregge automaticamente in un loop se non è sintatticamente
    valida (fino a 10 tentativi).

    Risultato : la query SPARQL generata (testo grezzo, senza markdown).
    """

    return await asyncio.to_thread(agent.generate_query, question)

#Validate Query
@mcp.tool(
    name="Validate Query",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def sparqllm_validate_query(
    query: Annotated[str, Field(description="Query SPARQL da validare contro lo schema VoID di KG-SFT", min_length=1)],
) -> str:
    """
    Controlla che una query SPARQL usi solo classi e proprietà realmente presenti in KG-SFT, confrontandola con la descrizione VoID dell'endpoint.
    Risultato : "OK: nessun problema rilevato." oppure la lista di problemi trovati,ognuno con un suggerimento in linguaggio naturale su come correggerlo.
    """
    try:
        issues = validate_sparql_with_void(query, GRAPHDB_ENDPOINT)
    except Exception as e:
        return f"Errore durante la validazione: {type(e).__name__}: {e}"

    if not issues:
        return "OK: nessun problema rilevato rispetto allo schema VoID."
    return "Problemi rilevati:\n" + "\n".join(f"- {issue}" for issue in issues)

#Execute Query
@mcp.tool(
    name="Execute Query",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def sparqllm_execute_query(
    query: Annotated[str, Field(description="Query SPARQL valida da eseguire su KG-SFT", min_length=1)],
    limit: Annotated[int, Field(description="Numero massimo di righe restituite nella risposta", ge=1, le=1000)] = 100,
) -> str:
    """
    Esegue una query SPARQL contro l'endpoint GraphDB di KG-SFT.
    Risultato : risultati in formato JSON oppure messaggio di errore con indicazioni su come correggere la query.
    """
    try:
        data = await asyncio.to_thread(agent.db_client.execute_query, query)
    except Exception as e:
        return (
            f"Errore nell'esecuzione della query: {type(e).__name__}: {e}. "
            "Controlla la sintassi e che i nomi di classi/proprietà siano corretti "
            "(prova prima sparqllm_validate_query)."
        )

    if "boolean" in data:
        return json.dumps({"result": data["boolean"]}, ensure_ascii=False)

    bindings = data.get("results", {}).get("bindings", [])
    if not bindings:
        return "La query non ha prodotto risultati (0 righe)."
    return json.dumps(bindings[:limit], indent=2, ensure_ascii=False)


#Ask Question to LLM
@mcp.tool(
    name="Ask Question to LLM",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
)
async def sparqllm_ask(
    question: Annotated[str, Field(description="Domanda in linguaggio naturale su KG-SFT", min_length=1)],
) -> str:
    """
    Risponde direttamente a una domanda in linguaggio naturale su KG-SFT.
    Risultato : JSON con {question, query, summary, status}, dove summary è la risposta in linguaggio naturale e status è "success" o "error".
    """
    result = await asyncio.to_thread(agent.ask, question)
    return json.dumps(
        {
            "question": result["question"],
            "query": result["query"],
            "summary": result["summary"],
            "status": result["status"],
        },
        indent=2,
        ensure_ascii=False,
    )

# Find Sport Facilities
@mcp.tool(
    name="Find Sport Facilities",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
)
async def sparqllm_find_facilities(
    sport: Annotated[
        str,
        Field(description="Nome dello sport da filtrare (es. 'tennis', 'calcio')"),
    ],
    city: Annotated[
        str,
        Field(description="Città da filtrare"),
    ],
    limit: Annotated[int, Field(description="Numero massimo di impianti da restituire", ge=1, le=100)] = 20,
) -> str:
    """
    Cerca impianti sportivi (sft:sport_facility) filtrando per sport e/o città.
    Risultato : JSON con lista di {uri, name, city} degli impianti trovati.
    """
    filters = []
    if sport:
        filters.append(
            f'?facility sft:has_sport ?sportUri . FILTER(STRENDS(LCASE(STR(?sportUri)), LCASE("/{sport}")))'
        )
    if city:
        filters.append(f'FILTER(CONTAINS(LCASE(?city), LCASE("{city}")))')
 
    filter_block = "\n      ".join(filters)
    sparql = f"""
        {SFT_PREFIX}
        SELECT DISTINCT ?facility ?name ?city 
        WHERE {{
            ?facility a sft:sport_facility ;
                sft:has_name ?name .
            OPTIONAL {{ ?facility sft:has_city ?city }}
            {filter_block}
        }}
        LIMIT {limit}
    """
    data = await run_query(sparql)
    bindings = data["results"]["bindings"]
    if not bindings:
        return "Nessun impianto trovato con questi filtri."
 
    results = [
        {
            "uri": shorten_uri(b["facility"]["value"], PREFIXES),
            "name": b["name"]["value"],
            "city": b.get("city", {}).get("value", "n/d"),
        }
        for b in bindings
    ]
    return json.dumps(results, indent=2, ensure_ascii=False)