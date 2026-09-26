"""Reusable Cypher queries for the app layer."""

SEARCH_ENTITIES = """
MATCH (n)
WHERE toLower(n.name) CONTAINS toLower($query)
RETURN n.name AS name, [l IN labels(n) WHERE l <> 'Entity'][0] AS type
LIMIT 20
"""

SEMANTIC_SEARCH = """
CALL db.index.vector.queryNodes('entity_embeddings', $k, $embedding)
YIELD node, score
RETURN node.name AS name,
       [l IN labels(node) WHERE l <> 'Entity'][0] AS type,
       score
"""

NEIGHBORHOOD = """
MATCH (n {name: $name})-[r]-(m)
RETURN startNode(r).name AS source,
       [l IN labels(startNode(r)) WHERE l <> 'Entity'][0] AS source_type,
       type(r) AS relation,
       endNode(r).name AS target,
       [l IN labels(endNode(r)) WHERE l <> 'Entity'][0] AS target_type
LIMIT $limit
"""

GRAPH_STATS = """
MATCH (n)
WITH count(n) AS node_count
MATCH ()-[r]->()
RETURN node_count, count(r) AS edge_count
"""

TOP_CONNECTED = """
MATCH (n)-[r]-()
RETURN n.name AS name, [l IN labels(n) WHERE l <> 'Entity'][0] AS type, count(r) AS degree
ORDER BY degree DESC
LIMIT $limit
"""


def semantic_search_entities(session, query_embedding: list[float], k: int = 10):
    return session.run(SEMANTIC_SEARCH, {"embedding": query_embedding, "k": k}).data()


def search_entities(session, search_term: str):
    return session.run(SEARCH_ENTITIES, {"query": search_term}).data()


def get_neighborhood(session, name: str, limit: int = 50):
    return session.run(NEIGHBORHOOD, {"name": name, "limit": limit}).data()


def get_graph_stats(session):
    result = session.run(GRAPH_STATS).data()
    return result[0] if result else {"node_count": 0, "edge_count": 0}


def get_top_connected(session, limit: int = 10):
    return session.run(TOP_CONNECTED, {"limit": limit}).data()
