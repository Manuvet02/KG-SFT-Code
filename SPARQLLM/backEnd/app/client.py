from SPARQLWrapper import SPARQLWrapper, JSON
from config import GRAPHDB_ENDPOINT


class GraphDBClient:

    def __init__(self):
        self.client = SPARQLWrapper(GRAPHDB_ENDPOINT)

    def execute_query(self, query: str):

        self.client.setQuery(query)
        self.client.setReturnFormat(JSON)

        return self.client.query().convert()