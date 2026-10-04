# graphdb_client.py
import httpx
from typing import Any

GRAPHDB_ENDPOINT = "http://localhost:7200/repositories/KG-SFT"

#Esegue una query SPARQL contro GraphDB
async def run_query(sparql: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            GRAPHDB_ENDPOINT,
            params={"query": sparql},
            headers={"Accept": "application/sparql-results+json"},
        )
        response.raise_for_status()
        return response.json()


#Abbrevia un URI usando i prefissi noti, es. http://.../ontology#Person -> ex:Person
def shorten_uri(uri: str, prefixes: dict[str, str]) -> str:
    for prefix, namespace in prefixes.items():
        if uri.startswith(namespace):
            return f"{prefix}:{uri[len(namespace):]}"
    return uri