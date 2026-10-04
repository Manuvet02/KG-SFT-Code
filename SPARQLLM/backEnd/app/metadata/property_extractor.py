from metadata.models import PropertyInfo
from metadata import queries


class PropertyExtractor:
    """
        Per una data classe, scopre le proprietà usate e ne deduce il tipo interrogando l'endpoint,invece di assumerlo.
    """
    def __init__(self, graphdb):
        self.graphdb = graphdb

    @staticmethod
    def _bindings(result):
        return result["results"]["bindings"]

    def list_property_iris(self, class_iri: str) -> list[str]:
        query = queries.PROPERTIES_OF_CLASS % class_iri
        result = self.graphdb.execute_query(query)
        return [row["property"]["value"] for row in self._bindings(result)]

    def _datatype(self, property_iri: str) -> str | None:
        query = queries.PROPERTY_DATATYPES % property_iri
        result = self.graphdb.execute_query(query)
        bindings = self._bindings(result)
        return bindings[0]["dt"]["value"] if bindings else None

    def _range_class(self, property_iri: str) -> str | None:
        query = queries.PROPERTY_RANGE_CLASSES % property_iri
        result = self.graphdb.execute_query(query)
        bindings = self._bindings(result)
        return bindings[0]["class"]["value"] if bindings else None

    def extract_for_class(self, class_iri: str) -> list[PropertyInfo]:
        property_infos = []

        for property_iri in self.list_property_iris(class_iri):
            datatype = self._datatype(property_iri)

            if datatype is not None:
                property_infos.append(
                    PropertyInfo(
                        iri=property_iri,
                        domain=class_iri,
                        datatype=datatype,
                        is_object_property=False,
                    )
                )
                continue

            # Nessun literal trovato -> probabile object property
            range_class = self._range_class(property_iri)
            property_infos.append(
                PropertyInfo(
                    iri=property_iri,
                    domain=class_iri,
                    range_class=range_class,
                    is_object_property=True,
                )
            )

        return property_infos
