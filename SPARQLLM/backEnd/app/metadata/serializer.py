from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS, FOAF

from metadata.models import DatasetInfo

VOID = Namespace("http://rdfs.org/ns/void#")
SFT = Namespace("http://www.semanticweb.org/KG-SFT#")
INSTANCE = Namespace("http://localhost:8080/source/")
DATASET_URI = URIRef("http://www.semanticweb.org/KG-SFT#dataset")


class VoidSerializer:
    """
    Costruisce la descrizione VoID (dataset + classPartition per classe) a partire da un DatasetInfo popolato dagli extractor, e la serializza in Turtle.
    """

    def __init__(self):
        self.graph = Graph()
        self.graph.bind("void", VOID)
        self.graph.bind("dcterms", DCTERMS)
        self.graph.bind("foaf", FOAF)
        self.graph.bind("sft", SFT)
        self.graph.bind("instance", INSTANCE)

    def build_dataset(
        self,
        dataset_info: DatasetInfo,
        description: str = "Knowledge Graph of sport facilities and transport in Trentino (KG-SFT).",
        homepage: str = "http://localhost:8080",
        sparql_endpoint: str = "http://localhost:7200/repositories/KG-SFT",
    ):
        g = self.graph

        g.add((DATASET_URI, RDF.type, VOID.Dataset))
        g.add((DATASET_URI, DCTERMS.description, Literal(description)))
        g.add((DATASET_URI, FOAF.homepage, URIRef(homepage)))
        g.add((DATASET_URI, VOID.sparqlEndpoint, URIRef(sparql_endpoint)))
        g.add((DATASET_URI, VOID.uriSpace, Literal(str(INSTANCE))))

        g.add((DATASET_URI, VOID.triples, Literal(dataset_info.triples, datatype=XSD.integer)))
        g.add((DATASET_URI, VOID.entities, Literal(dataset_info.entities, datatype=XSD.integer)))
        g.add((DATASET_URI, VOID.classes, Literal(dataset_info.class_count, datatype=XSD.integer)))
        g.add((DATASET_URI, VOID.properties, Literal(dataset_info.property_count, datatype=XSD.integer)))

        for class_info in dataset_info.classes:
            self._add_class_partition(dataset_info=DATASET_URI, class_info=class_info)

        return self

    def _add_class_partition(self, dataset_info, class_info):
        g = self.graph
        class_uri = URIRef(class_info.iri)

        partition = BNode()
        g.add((dataset_info, VOID.classPartition, partition))
        g.add((partition, VOID["class"], class_uri))
        g.add((partition, VOID.entities, Literal(class_info.entity_count, datatype=XSD.integer)))
        g.add((partition, VOID.uriSpace, Literal(str(INSTANCE) + self._class_local_name(class_info.iri) + "/")))

        if class_info.example_resource:
            g.add((partition, VOID.exampleResource, URIRef(class_info.example_resource)))

        for prop in class_info.properties:
            self._add_property_partition(partition, prop)

    def _add_property_partition(self, class_partition, property_info):
        g = self.graph
        prop_partition = BNode()

        g.add((class_partition, VOID.propertyPartition, prop_partition))
        g.add((prop_partition, VOID.property, URIRef(property_info.iri)))

        if property_info.is_object_property and property_info.range_class:
            g.add((prop_partition, RDFS.range, URIRef(property_info.range_class)))
        elif property_info.datatype:
            g.add((prop_partition, RDFS.range, URIRef(property_info.datatype)))

    @staticmethod
    def _class_local_name(class_iri: str) -> str:
        # Es. "http://www.semanticweb.org/KG-SFT#sport_facility" -> "SportFacility"
        local = class_iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
        return "".join(part.capitalize() for part in local.split("_"))

    def save(self, filename: str):
        self.graph.serialize(filename, format="turtle")
