import re
from rank_bm25 import BM25Okapi

try:
    from .loaders import load_examples
except ImportError:
    from loaders import load_examples

#Tokenizza il testo rimuovendo punteggiatura e convertendolo in minuscolo
def tokenize(text: str) -> list[str]:
    return re.findall(r'\w+', text.lower())

class ExampleRetriever:
    def __init__(self, examples: list[dict] = None):
        if examples is None:
            examples = load_examples()
        self.examples = examples
        
        # Prepara il corpus unendo la domanda ed eventuali keyword
        self.corpus = []
        for ex in self.examples:
            text = f"{ex['question']} {ex['keywords']}"
            self.corpus.append(tokenize(text))
            
        self.bm25 = BM25Okapi(self.corpus)

    #Recupera le top-K competency question più simili alla query in linguaggio naturale
    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        if not self.examples:
            return []
            
        tokenized_query = tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        # Trova gli indici dei punteggi più alti
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        
        results = []
        for idx in top_indices:
            # Ritorna solo se il punteggio è rilevante (o ritorna comunque le top-K few-shot)
            results.append(self.examples[idx])
            
        return results
