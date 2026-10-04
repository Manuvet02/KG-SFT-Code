import os
import sys

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from backEnd.app.client import GraphDBClient
from metadata.stats import DatasetStatistics
from metadata.class_extractor import ClassExtractor
from metadata.serializer import VoidSerializer
from metadata.models import DatasetInfo


def generate_void(output_path: str = "kgsft_void.ttl") -> DatasetInfo:
    """
    Entry point pubblico: interroga GraphDB, estrae classi/proprietà/statistiche e serializza il risultato in un file VoID Turtle.
    """
    graphdb = GraphDBClient()

    stats = DatasetStatistics(graphdb).get_statistics()
    classes = ClassExtractor(graphdb).extract()

    dataset_info = DatasetInfo(
        triples=stats["triples"],
        entities=stats["entities"],
        classes=classes,
    )

    serializer = VoidSerializer()
    serializer.build_dataset(dataset_info).save(output_path)

    return dataset_info


if __name__ == "__main__":
    info = generate_void()
    print(f"Classi trovate: {info.class_count}")
    print(f"Proprietà distinte: {info.property_count}")
    print(f"Triple totali: {info.triples}")
    print(f"Entità totali: {info.entities}")
