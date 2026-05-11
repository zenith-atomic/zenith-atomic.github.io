"""Neo4j knowledge graph manager for financial entity relationships."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from neo4j import Record as Neo4jRecord

logger = logging.getLogger(__name__)


class GraphNode(BaseModel):
    """A node in the knowledge graph."""

    id: str = Field(description="Unique node identifier")
    labels: list[str] = Field(default_factory=list, description="Neo4j labels e.g. Asset, Event")
    properties: dict[str, Any] = Field(default_factory=dict, description="Node properties")


class GraphRelationship(BaseModel):
    """A directed relationship between two nodes."""

    start_node_id: str = Field(description="ID of the start node")
    end_node_id: str = Field(description="ID of the end node")
    type: str = Field(description="Relationship type e.g. RELATES_TO, IMPACTS")
    properties: dict[str, Any] = Field(default_factory=dict, description="Relationship properties")


class KnowledgeGraphManager:
    """Manages a Neo4j knowledge graph for financial entity relationships."""

    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.driver: AsyncDriver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self.logger = logging.getLogger(self.__class__.__name__)
        self._connected = False

    async def close(self) -> None:
        """Close the Neo4j driver."""
        if self._connected:
            await self.driver.close()
            self._connected = False
            self.logger.info("Neo4j driver closed")

    async def _ensure_connection(self) -> None:
        """Verify connectivity to Neo4j."""
        if not self._connected:
            await self.driver.verify_connectivity()
            self._connected = True
            self.logger.info("Neo4j connection verified: %s", self.uri)

    async def add_node(self, node: GraphNode) -> bool:
        """Add or update a node in the graph.

        Args:
            node: The graph node to upsert.

        Returns:
            True on success, False on failure.
        """
        try:
            await self._ensure_connection()
            async with self.driver.session() as session:
                labels = ":" + ":".join(node.labels) if node.labels else ""
                props = {k: v for k, v in node.properties.items()}
                props["node_id"] = node.id
                set_clause = ", ".join(f"n.{k} = ${k}" for k in props)
                cypher = f"""
                    MERGE (n {labels} {{node_id: $node_id}})
                    SET {set_clause}
                """
                await session.run(cypher, props)
                self.logger.debug("Node upserted: id=%s, labels=%s", node.id, node.labels)
                return True
        except Exception as exc:
            self.logger.error("Failed to add node %s: %s", node.id, exc)
            return False

    async def add_relationship(self, relationship: GraphRelationship) -> bool:
        """Add a directed relationship between two existing nodes.

        Args:
            relationship: The relationship to create.

        Returns:
            True on success, False on failure.
        """
        try:
            await self._ensure_connection()
            async with self.driver.session() as session:
                props = {k: v for k, v in relationship.properties.items()}
                set_clause = ", ".join(f"r.{k} = ${k}" for k in props) if props else "r.rel_type = $rel_type"
                if props:
                    props["rel_type"] = relationship.type
                else:
                    props = {"rel_type": relationship.type}
                cypher = f"""
                    MATCH (a {{node_id: $start_id}}), (b {{node_id: $end_id}})
                    MERGE (a)-[r:{relationship.type}]->(b)
                    SET {set_clause}
                """
                await session.run(
                    cypher,
                    start_id=relationship.start_node_id,
                    end_id=relationship.end_node_id,
                    **props,
                )
                self.logger.debug(
                    "Relationship created: (%s)-[%s]->(%s)",
                    relationship.start_node_id,
                    relationship.type,
                    relationship.end_node_id,
                )
                return True
        except Exception as exc:
            self.logger.error("Failed to add relationship: %s", exc)
            return False

    async def query_graph(
        self, cypher_query: str, parameters: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results as dicts.

        Args:
            cypher_query: A valid Cypher query string.
            parameters: Optional query parameters.

        Returns:
            List of result record dicts.
        """
        try:
            await self._ensure_connection()
            async with self.driver.session() as session:
                result: Any = await session.run(cypher_query, parameters or {})
                records: list[dict[str, Any]] = []
                async for record in result:
                    records.append(dict(record))
                self.logger.debug("Graph query returned %d records", len(records))
                return records
        except Exception as exc:
            self.logger.error("Graph query failed: %s", exc)
            return []

    async def get_neighbors(
        self,
        node_id: str,
        relationship_type: Optional[str] = None,
        direction: str = "both",
        depth: int = 1,
    ) -> list[GraphNode]:
        """Get neighbouring nodes of a given node.

        Args:
            node_id: The central node identifier.
            relationship_type: Optional filter on relationship type.
            direction: "both" (default), "in" (incoming), "out" (outgoing).
            depth: Traversal depth (default 1).

        Returns:
            List of neighbouring GraphNode objects.
        """
        try:
            await self._ensure_connection()
            arrow_in = "<" if direction in ("both", "in") else ""
            arrow_out = "->" if direction in ("both", "out") else ""
            rel_part = f"[r{':' + relationship_type if relationship_type else ''}]"
            cypher = f"""
                MATCH path = (a {{node_id: $node_id}}){arrow_in}-{rel_part}-{arrow_out}(b)
                WHERE b.node_id <> $node_id
                RETURN DISTINCT b.node_id AS node_id, labels(b) AS labels, properties(b) AS properties
                LIMIT 100
            """
            async with self.driver.session() as session:
                result = await session.run(cypher, node_id=node_id)
                nodes = []
                async for record in result:
                    props = dict(record["properties"])
                    props.pop("node_id", None)
                    nodes.append(
                        GraphNode(
                            id=str(record["node_id"]),
                            labels=list(record["labels"]),
                            properties=props,
                        )
                    )
                self.logger.debug(
                    "get_neighbors(%s, depth=%d) returned %d nodes",
                    node_id,
                    depth,
                    len(nodes),
                )
                return nodes
        except Exception as exc:
            self.logger.error("get_neighbors failed for %s: %s", node_id, exc)
            return []
