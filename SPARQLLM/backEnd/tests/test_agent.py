# test_agent.py
import unittest
import sys
import os

# Configura i path di importazione per risolvere i moduli app/
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)
sys.path.append(os.path.join(backend_dir, "app"))
sys.path.append(os.path.join(backend_dir, "app", "agent"))

from app.agent.loaders import load_examples, load_void_schema, get_schema_context
from app.agent.retriever import ExampleRetriever
from app.agent.agent import extract_sparql_query, validate_sparql_syntax

class TestSPARQLLMAgent(unittest.TestCase):

    def test_extract_sparql_query(self):
        """Verifica l'estrazione corretta di query SPARQL da blocchi di codice markdown."""
        markdown_text = "Ecco la query:\n```sparql\nSELECT * WHERE { ?s ?p ?o }\n```\nSpero sia utile."
        extracted = extract_sparql_query(markdown_text)
        self.assertEqual(extracted, "SELECT * WHERE { ?s ?p ?o }")

        plain_text = "SELECT * WHERE { ?s ?p ?o }"
        extracted = extract_sparql_query(plain_text)
        self.assertEqual(extracted, plain_text)

    def test_validate_sparql_syntax(self):
        """Verifica la validazione sintattica locale di query SPARQL con rdflib."""
        valid_query = "PREFIX sft: <http://www.semanticweb.org/KG-SFT#> SELECT ?s WHERE { ?s a sft:sport_facility }"
        is_valid, err = validate_sparql_syntax(valid_query)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

        invalid_query = "SELECT ?s WHERE { ?s a sft:sport_facility"  # Manca graffa di chiusura
        is_valid, err = validate_sparql_syntax(invalid_query)
        self.assertFalse(is_valid)
        self.assertIsNotNone(err)

    def test_load_examples(self):
        """Verifica che gli esempi vengano caricati correttamente da kgsft_examples.ttl."""
        examples = load_examples()
        self.assertIsInstance(examples, list)
        self.assertTrue(len(examples) > 0)
        
        # Verifica campi attesi in un esempio
        first_ex = examples[0]
        self.assertIn("question", first_ex)
        self.assertIn("query", first_ex)
        self.assertIn("keywords", first_ex)

    def test_load_void_schema(self):
        """Verifica il caricamento dello schema VoID da kgsft_void.ttl."""
        schema = load_void_schema()
        self.assertIsInstance(schema, dict)
        
        # Verifica la presenza della classe sport_facility
        sf_uri = "http://www.semanticweb.org/KG-SFT#sport_facility"
        self.assertIn(sf_uri, schema)
        self.assertEqual(schema[sf_uri]["name"], "sport_facility")
        self.assertTrue(schema[sf_uri]["entities"] > 0)

    def test_retriever(self):
        """Verifica che il retriever trovi query pertinenti basate sulla domanda."""
        retriever = ExampleRetriever()
        
        # Cerca esempi pertinenti alle piste ciclabili (CQ12)
        results = retriever.retrieve("bike path connections", k=1)
        self.assertEqual(len(results), 1)
        self.assertTrue("bike" in results[0]["keywords"] or "path" in results[0]["keywords"])

if __name__ == "__main__":
    unittest.main()
