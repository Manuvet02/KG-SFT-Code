# Query dataset (globali)
TRIPLES = """
    SELECT (COUNT(*) AS ?count)
    WHERE {
        ?s ?p ?o
    }
"""

ENTITIES = """
    SELECT (COUNT(DISTINCT ?s) AS ?count)
    WHERE {
        ?s ?p ?o
    }
"""

CLASSES = """
    SELECT (COUNT(DISTINCT ?class) AS ?count)
    WHERE {
        ?s a ?class
    }
"""

PROPERTIES = """
    SELECT (COUNT(DISTINCT ?property) AS ?count)
    WHERE {
        ?s ?property ?o
    }
"""

# Query di listing

LIST_CLASSES = """
    SELECT DISTINCT ?class
    WHERE {
        ?s a ?class .
        FILTER(isIRI(?class))
    }
    ORDER BY ?class
"""

LIST_PROPERTIES = """
    SELECT DISTINCT ?property
    WHERE {
        ?s ?property ?o .
        FILTER(isIRI(?property))
    }
    ORDER BY ?property
"""

# Query parametriche per classe

ENTITIES_PER_CLASS = """
    SELECT (COUNT(DISTINCT ?s) AS ?count)
    WHERE {
        ?s a <%s>
    }
"""

PROPERTIES_OF_CLASS = """
    SELECT DISTINCT ?property
    WHERE {
        ?s a <%s> ;
        ?property ?o .
        FILTER(isIRI(?property))
    }
    ORDER BY ?property
"""

SAMPLE_RESOURCE = """
    SELECT ?s
    WHERE {
        ?s a <%s>
    }
    LIMIT 1
"""

# Query parametriche per proprietà
PROPERTY_DATATYPES = """
    SELECT DISTINCT ?dt
    WHERE {
        ?s <%s> ?o .
        FILTER(isLiteral(?o))
        BIND(DATATYPE(?o) AS ?dt)
    }
    LIMIT 5
"""

PROPERTY_RANGE_CLASSES = """
    SELECT DISTINCT ?class
    WHERE {
        ?s <%s> ?o .
        ?o a ?class .
    }
    LIMIT 5
"""