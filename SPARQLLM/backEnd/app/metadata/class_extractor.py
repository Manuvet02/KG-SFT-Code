from metadata.models import ClassInfo
from metadata.property_extractor import PropertyExtractor
from metadata import queries


class ClassExtractor:
    """
    Scopre le classi presenti nell'endpoint e le arricchisce con conteggio istanze, resource di esempio e proprietà (via PropertyExtractor).
    """

    def __init__(self, graphdb):
        self.graphdb = graphdb
        self.property_extractor = PropertyExtractor(graphdb)

    @staticmethod
    def _bindings(result):
        return result["results"]["bindings"]

    def list_class_iris(self) -> list[str]:
        result = self.graphdb.execute_query(queries.LIST_CLASSES)
        return [row["class"]["value"] for row in self._bindings(result)]

    def _entity_count(self, class_iri: str) -> int:
        query = queries.ENTITIES_PER_CLASS % class_iri
        result = self.graphdb.execute_query(query)
        bindings = self._bindings(result)
        return int(bindings[0]["count"]["value"]) if bindings else 0

    def _sample_resource(self, class_iri: str) -> str | None:
        query = queries.SAMPLE_RESOURCE % class_iri
        result = self.graphdb.execute_query(query)
        bindings = self._bindings(result)
        return bindings[0]["s"]["value"] if bindings else None

    def extract(self) -> list[ClassInfo]:
        class_infos = []

        for class_iri in self.list_class_iris():
            class_info = ClassInfo(
                iri=class_iri,
                entity_count=self._entity_count(class_iri),
                example_resource=self._sample_resource(class_iri),
            )
            class_info.properties = self.property_extractor.extract_for_class(class_iri)
            class_infos.append(class_info)

        return class_infos
