"""Vector store manager using Qdrant for financial embeddings."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from llama_index.core.embeddings import resolve_embed_model
from llama_index.core.schema import TextNode
from llama_index.vector_stores.qdrant import QdrantVectorStore
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

if TYPE_CHECKING:
    from llama_index.core.vector_stores.types import VectorStoreQuery

logger = logging.getLogger(__name__)


class FinancialEmbedding(BaseModel):
    """Structured financial document for vector storage."""

    text: str = Field(description="Text content of the embedding")
    symbol: Optional[str] = Field(default=None, description="Ticker symbol e.g. BTC, ETH")
    timestamp: Optional[float] = Field(default=None, description="Unix timestamp of the data")
    source: Optional[str] = Field(
        default=None,
        description="Data source type: news, on-chain, report, social, technical",
    )


class VectorStoreManager:
    """Manages Qdrant vector storage for financial documents and embeddings."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "trading_knowledge",
        dim: int = 1536,
        force_recreate: bool = False,
    ):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.dim = dim
        self.force_recreate = force_recreate
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
        )
        # Default to ada-002; replace with a specialised financial embedder in production
        self.embed_model = resolve_embed_model("openai:text-embedding-ada-002")
        self.logger = logging.getLogger(self.__class__.__name__)

    async def initialize(self) -> None:
        """Ensure the Qdrant collection exists and is correctly configured."""
        self.logger.info(
            "Initialising Qdrant collection '%s' at %s:%d",
            self.collection_name,
            self.client.host,
            self.client.port,
        )
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name in collections:
            if self.force_recreate:
                self.logger.warning("Force-recreating collection '%s'", self.collection_name)
                self.client.delete_collection(collection_name=self.collection_name)
            else:
                self.logger.info("Collection '%s' already exists, skipping creation", self.collection_name)
                return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
        )
        self.logger.info("Collection '%s' created successfully", self.collection_name)

    async def add_document(self, embedding_data: FinancialEmbedding) -> bool:
        """Add a single financial document to the vector store.

        Args:
            embedding_data: The structured financial embedding to store.

        Returns:
            True on success, False on failure.
        """
        try:
            node = TextNode(
                text=embedding_data.text,
                metadata={
                    "symbol": embedding_data.symbol,
                    "timestamp": embedding_data.timestamp,
                    "source": embedding_data.source,
                },
            )
            from llama_index.core import Document

            doc = Document(text=embedding_data.text, metadata=node.metadata)
            from llama_index.core import VectorStoreIndex

            index = VectorStoreIndex.from_vector_store(
                self.vector_store,
                embed_model=self.embed_model,
            )
            index.insert(doc)
            self.logger.debug(
                "Document added: symbol=%s, source=%s",
                embedding_data.symbol,
                embedding_data.source,
            )
            return True
        except Exception as exc:
            self.logger.error("Failed to add document: %s", exc)
            return False

    async def add_documents(self, embeddings: list[FinancialEmbedding]) -> int:
        """Add multiple financial documents.

        Args:
            embeddings: List of structured financial embeddings.

        Returns:
            Number of successfully added documents.
        """
        from llama_index.core import Document, VectorStoreIndex

        index = VectorStoreIndex.from_vector_store(
            self.vector_store,
            embed_model=self.embed_model,
        )
        docs = []
        for emb in embeddings:
            node = TextNode(
                text=emb.text,
                metadata={
                    "symbol": emb.symbol,
                    "timestamp": emb.timestamp,
                    "source": emb.source,
                },
            )
            docs.append(Document(text=emb.text, metadata=node.metadata))

        try:
            for doc in docs:
                index.insert(doc)
            self.logger.info("Bulk-inserted %d documents", len(docs))
            return len(docs)
        except Exception as exc:
            self.logger.error("Bulk insert failed: %s", exc)
            return 0

    async def query_documents(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[TextNode]:
        """Query the vector store with optional metadata filters.

        Args:
            query: Natural-language query string.
            top_k: Number of results to retrieve.
            filters: Optional metadata filter dict (e.g. {"symbol": "BTC"}).

        Returns:
            List of matching TextNode objects.
        """
        try:
            from llama_index.core import VectorStoreIndex

            index = VectorStoreIndex.from_vector_store(
                self.vector_store,
                embed_model=self.embed_model,
            )
            if filters:
                from llama_index.core.vector_stores.types import MetadataFilters, ExactFilter

                meta_filters = MetadataFilters(
                    filters=[ExactFilter(key=k, value=v) for k, v in filters.items()]
                )
            else:
                meta_filters = None

            query_vec = self.embed_model.get_text_embedding(query)
            results = self.vector_store.query(
                query_vector=query_vec,
                top_k=top_k,
                filter=meta_filters,
            )
            nodes = []
            for res in results.nodes or []:
                if isinstance(res, TextNode):
                    nodes.append(res)
            self.logger.debug("Query '%s' returned %d results", query, len(nodes))
            return nodes
        except Exception as exc:
            self.logger.error("Query failed: %s", exc)
            return []
