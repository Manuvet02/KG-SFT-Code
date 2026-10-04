from metadata.queries import TRIPLES, ENTITIES


class DatasetStatistics:
    """
    Conteggi globali del dataset (triple, entità)
    """

    def __init__(self, graphdb):
        self.graphdb = graphdb

    def _count(self, query: str) -> int:
        result = self.graphdb.execute_query(query)
        return int(result["results"]["bindings"][0]["count"]["value"])

    def get_statistics(self) -> dict:
        return {
            "triples": self._count(TRIPLES),
            "entities": self._count(ENTITIES),
        }
