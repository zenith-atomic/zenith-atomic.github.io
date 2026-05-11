"""Test entry point for the Project Dragonfly knowledge system.

Loads config, initialises all managers, and runs mock queries.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import yaml
from llama_index.core.embeddings import resolve_embed_model
from llama_index.llms.openai import OpenAI

# Add project root to path for local imports
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from knowledge.knowledge_graph import GraphNode, GraphRelationship, KnowledgeGraphManager
from knowledge.rag_pipeline import RAGPipeline
from knowledge.vector_store import FinancialEmbedding, VectorStoreManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("dragonfly.knowledge.run")


def load_config() -> dict:
    """Load the knowledge system YAML configuration."""
    config_path = BASE_DIR / "configs" / "knowledge.yaml"
    if not config_path.exists():
        logger.error("Config file not found: %s", config_path)
        sys.exit(1)
    with open(config_path) as f:
        return yaml.safe_load(f)


async def main() -> None:
    config = load_config()
    ks_cfg = config.get("knowledge_system", {})
    vector_cfg = ks_cfg.get("vector_db", {})
    kg_cfg = ks_cfg.get("knowledge_graph", {})
    rag_cfg = ks_cfg.get("rag", {})

    # ── Vector Store ──────────────────────────────────────────────────────────
    vsm = VectorStoreManager(
        host=vector_cfg.get("host", "localhost"),
        port=vector_cfg.get("port", 6333),
        collection_name=vector_cfg.get("collection_name", "trading_knowledge"),
    )
    await vsm.initialize()
    logger.info("VectorStoreManager initialised")

    # ── Knowledge Graph ────────────────────────────────────────────────────────
    kgm = KnowledgeGraphManager(
        uri=kg_cfg.get("uri", "neo4j://localhost:7687"),
        user=kg_cfg.get("user", "neo4j"),
        password=kg_cfg.get("password", "password"),
    )
    try:
        # Quick connectivity check (will skip gracefully if Neo4j is not running)
        await kgm._ensure_connection()
        logger.info("KnowledgeGraphManager connected: %s", kg_cfg.get("uri"))
    except Exception as exc:
        logger.warning("Neo4j not reachable (%s); graph operations will be skipped", exc)
        kgm = None

    # ── Mock Data ─────────────────────────────────────────────────────────────
    mock_embeddings = [
        FinancialEmbedding(
            text="Bitcoin ETF sees record inflows of $1.2B as institutional demand surges.",
            symbol="BTC",
            timestamp=1700000000.0,
            source="news",
        ),
        FinancialEmbedding(
            text="Ethereum staking yield drops to 3.8% following the latest protocol upgrade.",
            symbol="ETH",
            timestamp=1700000100.0,
            source="on-chain",
        ),
        FinancialEmbedding(
            text="Goldman Sachs initiates coverage of BlackRock's spot Bitcoin ETF with buy rating.",
            symbol="BTC",
            timestamp=1700000200.0,
            source="report",
        ),
        FinancialEmbedding(
            text="Solana network TPS hits 4,500 during peak trading, outpacing Ethereum L2s.",
            symbol="SOL",
            timestamp=1700000300.0,
            source="technical",
        ),
        FinancialEmbedding(
            text="Federal Reserve signals potential rate cuts in Q1 2026, boosting risk assets.",
            symbol=None,
            timestamp=1700000400.0,
            source="news",
        ),
    ]

    logger.info("Ingesting %d mock financial documents...", len(mock_embeddings))
    success_count = await vsm.add_documents(mock_embeddings)
    logger.info("Successfully ingested %d/%d documents", success_count, len(mock_embeddings))

    # ── Vector Queries ────────────────────────────────────────────────────────
    logger.info("\n=== Vector Store Queries ===")

    # Query 1: general
    nodes = await vsm.query_documents("What happened with Bitcoin ETFs?", top_k=3)
    logger.info("Query 1 results (%d):", len(nodes))
    for n in nodes:
        logger.info("  - %s  (symbol=%s, source=%s)", n.text[:80], n.metadata.get("symbol"), n.metadata.get("source"))

    # Query 2: filtered by symbol
    nodes = await vsm.query_documents(
        "Ethereum staking developments",
        top_k=3,
        filters={"symbol": "ETH"},
    )
    logger.info("Query 2 results (ETH filter, %d):", len(nodes))
    for n in nodes:
        logger.info("  - %s", n.text[:80])

    # ── Knowledge Graph ────────────────────────────────────────────────────────
    if kgm is not None:
        logger.info("\n=== Knowledge Graph Operations ===")

        # Add nodes
        nodes_to_add = [
            GraphNode(id="BTC", labels=["Asset", "Cryptocurrency"], properties={"name": "Bitcoin", "price_usd": 67500}),
            GraphNode(id="ETH", labels=["Asset", "Cryptocurrency"], properties={"name": "Ethereum", "price_usd": 3800}),
            GraphNode(id="SOL", labels=["Asset", "Cryptocurrency"], properties={"name": "Solana", "price_usd": 185}),
            GraphNode(id="ETF_EVENT_001", labels=["Event"], properties={"type": "Record Inflows", "amount": "1.2B"}),
            GraphNode(id="MACRO_EVENT_001", labels=["Event"], properties={"type": "Fed Rate Signal"}),
        ]
        for node in nodes_to_add:
            await kgm.add_node(node)
        logger.info("Added %d graph nodes", len(nodes_to_add))

        # Add relationships
        rels_to_add = [
            GraphRelationship(start_node_id="ETF_EVENT_001", end_node_id="BTC", type="IMPACTS", properties={}),
            GraphRelationship(start_node_id="BTC", end_node_id="ETF_EVENT_001", type="CAUSED_BY", properties={}),
            GraphRelationship(start_node_id="MACRO_EVENT_001", end_node_id="BTC", type="AFFECTS", properties={}),
            GraphRelationship(start_node_id="MACRO_EVENT_001", end_node_id="ETH", type="AFFECTS", properties={}),
        ]
        for rel in rels_to_add:
            await kgm.add_relationship(rel)
        logger.info("Added %d graph relationships", len(rels_to_add))

        # Traverse: get neighbours of ETF_EVENT_001
        neighbours = await kgm.get_neighbors("ETF_EVENT_001", direction="out", depth=1)
        logger.info("Neighbours of ETF_EVENT_001 (outgoing): %s", [n.id for n in neighbours])

        # Cypher query: find all events that impact BTC
        results = await kgm.query_graph(
            """
            MATCH (e:Event)-[r:IMPACTS]->(a:Asset {node_id: 'BTC'})
            RETURN e.node_id AS event_id, e.properties AS props
            """
        )
        logger.info("Events impacting BTC: %s", results)

        await kgm.close()
    else:
        logger.info("\n=== Knowledge Graph (skipped — Neo4j not available) ===")

    # ── RAG Pipeline ───────────────────────────────────────────────────────────
    logger.info("\n=== RAG Pipeline ===")
    try:
        embed_model = resolve_embed_model(vector_cfg.get("embedding_model", "openai:text-embedding-ada-002"))
        llm = OpenAI(model=rag_cfg.get("llm_model", "gpt-4o-mini"))
        pipeline = RAGPipeline(
            vector_store_manager=vsm,
            llm=llm,
            embed_model=embed_model,
            similarity_top_k=rag_cfg.get("similarity_top_k", 10),
            num_queries=rag_cfg.get("num_queries", 3),
            reranker_model=rag_cfg.get("reranker_model", "BAAI/bge-reranker-base"),
        )
        await pipeline.initialize()
        logger.info("RAGPipeline initialised")

        # Ingest a market data document
        ingested = await pipeline.ingest_market_data(
            FinancialEmbedding(
                text="JP Morgan upgrades Bitcoin to overweight citing ETF demand and macro tailwinds.",
                symbol="BTC",
                timestamp=1700000500.0,
                source="report",
            )
        )
        logger.info("Market data ingest result: %s", ingested)

        # Execute a mock RAG query
        answer = await pipeline.query("What are the latest developments affecting Bitcoin price?")
        logger.info("RAG answer:\n%s", answer)

    except Exception as exc:
        logger.error("RAG pipeline failed: %s", exc)

    logger.info("\n=== All tests complete ===")


if __name__ == "__main__":
    asyncio.run(main())
