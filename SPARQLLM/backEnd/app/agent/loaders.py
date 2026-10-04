import os
import sys
import rdflib

# Configura i path di importazione
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import EXAMPLES_PATH, VOID_PATH

#Carica le competency question e le query SPARQL corrispondenti da kgsft_examples.ttl
def load_examples(file_path: str = EXAMPLES_PATH) -> list[dict]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File degli esempi non trovato in: {file_path}")

    g = rdflib.Graph()
    g.parse(file_path, format="turtle")

    query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX sh: <http://www.w3.org/ns/shacl#>
    PREFIX schema: <https://schema.org/>

    SELECT ?comment ?select ?keywords WHERE {
        ?cq a sh:SPARQLExecutable ;
            rdfs:comment ?comment ;
            sh:select ?select .
        OPTIONAL { ?cq schema:keywords ?keywords }
    }
    """

    results = []
    for row in g.query(query):
        comment = str(row[0])
        select_query = str(row[1])
        keywords = str(row[2]) if row[2] else ""
        
        # Pulisce i commenti per evitare note di avviso sul join
        clean_comment = comment.split("(NOTE:")[0].strip()
        
        results.append({
            "question": clean_comment,
            "query": select_query,
            "keywords": keywords
        })
    return results

#Carica la struttura dell'ontologia definita nel VoID kgsft_void.ttl
def load_void_schema(file_path: str = VOID_PATH) -> dict:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File VoID non trovato in: {file_path}")

    g = rdflib.Graph()
    g.parse(file_path, format="turtle")

    #Recupera le classi e il conteggio delle istanze
    classes_query = """
    PREFIX void: <http://rdfs.org/ns/void#>
    SELECT ?class ?entities WHERE {
        ?partition a void:Dataset ;
                   void:class ?class ;
                   void:entities ?entities .
    }
    """
    
    classes = {}
    for row in g.query(classes_query):
        cls_uri = str(row[0])
        cls_name = cls_uri.split("#")[-1] if "#" in cls_uri else cls_uri.split("/")[-1]
        classes[cls_uri] = {
            "name": cls_name,
            "entities": int(row[1]),
            "properties": {}
        }

    #Recupera le proprietà associate a ciascuna classe e i loro range/datatypes
    props_query = """
    PREFIX void: <http://rdfs.org/ns/void#>
    SELECT ?class ?property ?datatype ?targetClass WHERE {
        ?classPartition void:class ?class ;
                        void:propertyPartition ?propPartition .
        ?propPartition void:property ?property .
        OPTIONAL { ?propPartition void:datatype ?datatype }
        OPTIONAL { ?propPartition void:classPartition/void:class ?targetClass }
    }
    """

    for row in g.query(props_query):
        cls_uri = str(row[0])
        prop_uri = str(row[1])
        datatype = str(row[2]) if row[2] else None
        target_class = str(row[3]) if row[3] else None

        if cls_uri in classes:
            prop_name = prop_uri.split("#")[-1] if "#" in prop_uri else prop_uri.split("/")[-1]
            
            # Determina il tipo/range
            if datatype:
                range_type = datatype.split("#")[-1]
            elif target_class:
                range_type = target_class.split("#")[-1] if "#" in target_class else target_class.split("/")[-1]
                range_type = f"relation to {range_type}"
            else:
                range_type = "unknown"

            classes[cls_uri]["properties"][prop_uri] = {
                "name": prop_name,
                "range": range_type
            }

    return classes

#Ritorna una rappresentazione leggibile dello schema del grafo da inserire nel prompt
def get_schema_context(file_path: str = VOID_PATH) -> str:
    schema_data = load_void_schema(file_path)
    
    lines = ["Ontology Schema (Classes & Properties available in KG-SFT):"]
    for cls_uri, cls_info in schema_data.items():
        lines.append(f"- Class: sft:{cls_info['name']} (instances: {cls_info['entities']})")
        for prop_uri, prop_info in cls_info["properties"].items():
            lines.append(f"  * Property: sft:{prop_info['name']} -> ({prop_info['range']})")
            
    lines.append("\nNamespace prefix for queries:")
    lines.append("PREFIX sft: <http://www.semanticweb.org/KG-SFT#>")
    lines.append("\nInstance URI Rules:")
    lines.append("All entities (SportFacility, Sport, Association, Service, Stop, Path, Route, MeanOfTransport, Athlete, Reservation, App) are identified by URIs following the pattern:")
    lines.append("  http://localhost:8080/source/{{ClassName}}/{{id}}")
    lines.append("Examples:")
    lines.append("  - Sport: <http://localhost:8080/source/Sport/tennis>, <http://localhost:8080/source/Sport/sci>")
    lines.append("  - Service: <http://localhost:8080/source/Service/3>")
    lines.append("  - SportFacility: <http://localhost:8080/source/SportFacility/101>")
    lines.append("  - Association: <http://localhost:8080/source/Association/15>")
    lines.append("DO NOT search for rdfs:label on entities that store their identifier directly in the URI (e.g. Sport, Association).")
    lines.append("To filter by an entity URI name, use exact URI match or STRENDS/LCASE checks on STR(?var):")
    lines.append("  * Exact URI match: ?sport_facility sft:has_sport <http://localhost:8080/source/Sport/tennis>")
    lines.append("  * String filter: FILTER(STRENDS(LCASE(STR(?sport)), '/tennis'))")
    lines.append("To extract human-readable ID from URI in SELECT clause, use:")
    lines.append("  (REPLACE(STR(?entity), \"http://localhost:8080/source/{{ClassName}}/\", \"\") AS ?id)")
    return "\n".join(lines)
