import sys
import os

# Configura i path di importazione
app_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(app_dir)

from sparql_llm import SparqlVoidShapesLoader, SparqlExamplesLoader

for p in [app_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from agent.agent import SparqLLMAgent

def run_interactive_loop():
    print("=" * 60)
    print(" SPARQLLM —  KG-SFT")
    print("=" * 60)
    print("Caricamento componenti in corso...")
    
    try:
        agent = SparqLLMAgent()
        print("Agente pronto!")
    except Exception as e:
        print(f"Errore nell'inizializzazione dell'agente: {e}")
        return
    
    while True:
        try:
            print("\nInserisci una domanda ('exit' per uscire) :")
            question = input("> ").strip()
            if not question:
                continue
            if question.lower() == "exit":
                break
                
            print("\nElaborazione in corso...")
            res = agent.ask(question)
            
            print("-" * 40)
            print("Query SPARQL generata:")
            print(res["query"])
            print("-" * 40)
            print("Sintesi Risultato:")
            print(res["summary"])
            print("-" * 40)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Errore durante l'elaborazione: {e}")

if __name__ == "__main__":
    run_interactive_loop()