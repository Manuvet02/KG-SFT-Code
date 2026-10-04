import re
import sys
import os
import logging
import rdflib

# Configura i path di importazione
agent_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(agent_dir)
backend_dir = os.path.dirname(app_dir)

for p in [agent_dir, app_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)


try:
    from .loaders import get_schema_context
    from .retriever import ExampleRetriever
    from .llm import get_llm
except ImportError:
    from loaders import get_schema_context
    from retriever import ExampleRetriever
    from llm import get_llm

from config import EXAMPLES_PATH, VOID_PATH
from client import GraphDBClient
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

#Estrae la query SPARQL pulita rimuovendo eventuali blocchi markdown sparql
def extract_sparql_query(text: str) -> str:
    match = re.search(r"```(?:sparql)?(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()

#Valida sintatticamente una query SPARQL in locale usando rdflib
def validate_sparql_syntax(query: str) -> tuple[bool, str | None]:
    try:
        rdflib.plugins.sparql.parser.parseQuery(query)
        return True, None
    except Exception as e:
        return False, str(e)

class SparqLLMAgent:
    def __init__(self, endpoint_url: str = None):
        self.retriever = ExampleRetriever()
        self.llm = get_llm(temperature=0.0)
        self.db_client = GraphDBClient()
        self.schema_context = get_schema_context()

    #Genera una query SPARQL per la domanda, con loop di validazione e correzione
    def generate_query(self, user_question: str, max_retries: int = 10) -> str:

        #Recupero esempi few-shot
        relevant_examples = self.retriever.retrieve(user_question, k=3)
        few_shot_str = ""
        for i, ex in enumerate(relevant_examples, 1):
            few_shot_str += f"Esempio {i}:\nDomanda: {ex['question']}\nQuery:\n```sparql\n{ex['query']}\n```\n\n"

        # 2. Prepara il prompt di generazione
        system_prompt = (
            "Sei un assistente AI specializzato nella scrittura di query SPARQL per il Knowledge Graph KG-SFT.\n"
            "Usa lo schema dell'ontologia e gli esempi forniti per generare una query corretta.\n\n"
            "REGOLE FONDAMENTALI SUGLI URI ED ENTITÀ:\n"
            "1. Tutte le entità (Athlete, Sport, Reservation, Association, SportFacility, App, MeanOfTransport, Route, Service, Stop, Path , Persona) seguono il pattern URI Karma:\n"
            "   http://localhost:8080/source/{{ClassName}}/{{id}}\n"
            "2. Molte entità (come Sport, Association, Service, Stop, Route, ecc.) NON hanno la proprietà rdfs:label. L'identificativo è nel percorso dell'URI stesso.\n"
            "3. Per filtrare per un'entità specifica (es. uno sport come 'tennis' o 'sci'), usa l'URI completo se noto (es. <http://localhost:8080/source/Sport/tennis>) oppure STRENDS/LCASE su STR(?var) (es. FILTER(STRENDS(LCASE(STR(?sport)), '/tennis'))).\n"
            "4. NON cercare proprietà rdfs:label su entità che memorizzano l'identificativo nell'URI.\n"
            "5. Nei SELECT, usa REPLACE(STR(?entity), 'http://localhost:8080/source/{{ClassName}}/', '') per restituire l'ID pulito dell'entità.\n\n"
            "6. Quando devi filtrare per una città, USA SEMPRE 'FILTER(CONTAINS(LCASE(STR(?city)), \"<città>\"))' o 'FILTER(STRENDS(LCASE(STR(?city)), \"<città>\"))'. NONUSA rdfs:label su entità di tipo Location/City.\n\n"
            "7. Quando filtri per nome dell'entità 'SportFacility' usa la proprietà 'has_name' seguita dal nome della struttura.\n"
            "Rispondi esclusivamente con la query SPARQL racchiusa in un blocco di codice markdown ```sparql ... ```."
        )

        user_prompt_template = (
            "{schema_context}\n\n"
            "Ecco alcuni esempi di query di riferimento:\n"
            "{few_shot_examples}\n"
            "Domanda dell'utente: {user_question}\n\n"
            "Genera la query SPARQL corrispondente:"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt_template)
        ])

        chain = prompt | self.llm
        
        # Chiamata
        response = chain.invoke({
            "schema_context": self.schema_context,
            "few_shot_examples": few_shot_str,
            "user_question": user_question
        })
        
        raw_output = response.content
        sparql_query = extract_sparql_query(raw_output)

        #Validazione e Correzione
        retries = 0
        is_valid, error_msg = validate_sparql_syntax(sparql_query)
        
        while not is_valid and retries < max_retries:
            logger.warning(f"Sintassi SPARQL non valida (tentativo {retries+1}/{max_retries}): {error_msg}")
            
            correction_system = (
                "Sei un parser e correttore di query SPARQL. Identifica l'errore di sintassi e correggilo.\n"
                "Rispondi esclusivamente con la query SPARQL corretta racchiusa in un blocco di codice markdown ```sparql ... ```."
            )
            
            correction_user = (
                "La query SPARQL generata contiene un errore di sintassi.\n\n"
                "Query errata:\n"
                "```sparql\n{bad_query}\n```\n\n"
                "Errore riscontrato:\n{error_msg}\n\n"
                "Riscrivi la query SPARQL corretta:"
            )
            
            correction_prompt = ChatPromptTemplate.from_messages([
                ("system", correction_system),
                ("user", correction_user)
            ])
            
            correction_chain = correction_prompt | self.llm
            correction_response = correction_chain.invoke({
                "bad_query": sparql_query,
                "error_msg": error_msg
            })
            
            sparql_query = extract_sparql_query(correction_response.content)
            is_valid, error_msg = validate_sparql_syntax(sparql_query)
            retries += 1

        if not is_valid:
            logger.error(f"Impossibile generare una query SPARQL valida dopo {max_retries} tentativi.")
        
        # Ritorna comunque la query per ispezione
        return sparql_query

    #Esegue la query SPARQL generata su GraphDB (se online) e riassume il risultato
    def execute_and_summarize(self, user_question: str, sparql_query: str) -> dict:
        result_dict = {
            "question": user_question,
            "query": sparql_query,
            "raw_results": None,
            "summary": None,
            "status": "success"
        }

        # Tenta l'esecuzione su GraphDB
        try:
            raw_results = self.db_client.execute_query(sparql_query)
            result_dict["raw_results"] = raw_results
        except Exception as e:
            # Se GraphDB è offline o la query fallisce
            logger.error(f"Errore durante l'esecuzione della query su GraphDB: {e}")
            result_dict["status"] = "error"
            result_dict["error_message"] = str(e)
            result_dict["summary"] = (
                "Impossibile eseguire la query. Verifica che l'istanza GraphDB sia avviata e che "
                "il repository sia configurato correttamente."
            )
            return result_dict

        # Se l'esecuzione ha successo, riassume i risultati
        try:
            # Estrae i binding per renderli più leggibili nel prompt di sintesi
            bindings = raw_results.get("results", {}).get("bindings", [])
            if not bindings:
                result_dict["summary"] = "Non ho trovato risultati nel Knowledge Graph per questa domanda."
                return result_dict

            # Formatta i dati grezzi per l'LLM
            formatted_data = []
            for b in bindings:
                row = {k: v["value"] for k, v in b.items()}
                formatted_data.append(row)

            # Genera il riassunto
            summary_system = "Sei un assistente amichevole che presenta i risultati di un Knowledge Graph in modo chiaro e leggibile in italiano."
            summary_user = (
                "Domanda dell'utente: {question}\n\n"
                "Risultati restituiti dal Knowledge Graph:\n{data}\n\n"
                "Formula una risposta in linguaggio naturale chiara, coincisa e accurata basandoti solo sui dati sopra:"
            )
            
            summary_prompt = ChatPromptTemplate.from_messages([
                ("system", summary_system),
                ("user", summary_user)
            ])
            
            summary_chain = summary_prompt | self.llm
            summary_response = summary_chain.invoke({
                "question": user_question,
                "data": str(formatted_data[:10])  # limita a 10 righe per non saturare il contesto
            })
            result_dict["summary"] = summary_response.content
        except Exception as e:
            logger.error(f"Errore durante la sintesi dei risultati: {e}")
            result_dict["summary"] = f"Query eseguita con successo. Trovati {len(bindings)} risultati."

        return result_dict

    #Esegue l'intero flusso: generazione -> esecuzione -> sintesi
    def ask(self, user_question: str) -> dict:
        query = self.generate_query(user_question)
        return self.execute_and_summarize(user_question, query)
