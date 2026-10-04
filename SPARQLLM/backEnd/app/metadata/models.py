from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PropertyInfo:
    """Rappresenta una proprietà usata da una classe, con il suo range dedotto empiricamente."""

    iri: str
    domain: Optional[str] = None          # IRI della classe da cui è stata estratta
    range_class: Optional[str] = None     # IRI della classe target, se object property
    datatype: Optional[str] = None        # xsd:string, xsd:integer... se datatype property
    is_object_property: bool = False


@dataclass
class ClassInfo:
    """Rappresenta una classe del dataset con conteggio istanze e proprietà associate."""

    iri: str
    entity_count: int = 0
    properties: list[PropertyInfo] = field(default_factory=list)
    example_resource: Optional[str] = None


@dataclass
class DatasetInfo:
    """Aggregato finale passato al serializer per generare il VoID."""

    triples: int = 0
    entities: int = 0
    classes: list[ClassInfo] = field(default_factory=list)

    @property
    def class_count(self) -> int:
        return len(self.classes)

    @property
    def property_count(self) -> int:
        # Unione delle proprietà distinte su tutte le classi (una proprietà può
        # comparire su più classi, es. has_sport su sport_facility e association)
        seen = {p.iri for c in self.classes for p in c.properties}
        return len(seen)
