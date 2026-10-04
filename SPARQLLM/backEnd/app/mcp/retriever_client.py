# retriever_client.py
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.retrievers import BM25Retriever
from sparql_llm import SparqlVoidShapesLoader, SparqlExamplesLoader


from graphdb_client import GRAPHDB_ENDPOINT
from config import EXAMPLES_PATH, VOID_PATH

VOID_FILE = VOID_PATH
EXAMPLES_FILE = EXAMPLES_PATH


def _build_retriever(k: int = 5) -> BM25Retriever:
    void_docs = SparqlVoidShapesLoader(GRAPHDB_ENDPOINT, void_file=VOID_FILE).load()
    example_docs = SparqlExamplesLoader(GRAPHDB_ENDPOINT, examples_file=EXAMPLES_FILE).load()

    retriever = BM25Retriever.from_documents(void_docs + example_docs)
    retriever.k = k
    return retriever


retriever = _build_retriever()