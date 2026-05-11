"""Retrieval-Augmented Generation pipeline for financial trading research."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from llama_index.core import VectorStoreIndex
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms import LLM
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import ResponseSynthesizer
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.service_context import ServiceContext
from llama_index.postprocessor.cohere_rerank import CohereRerank

from knowledge.vector_store import FinancialEmbedding, VectorStoreManager

if TYPE_CHECKING:
    from llama_index.core.schema import TextNode

logger = logging.getLogger(__name__)


class RAGPipeline:
    """RAG pipeline combining vector search with a language model for financial research."""

    def __init__(
        self,
        vector_store_manager: VectorStoreManager,
        llm: LLM,
        embed_model: BaseEmbedding,
        similarity_top_k: int = 10,
        num_queries: int = 3,
        reranker_model: str = "BAAI/bge-reranker-base",
    ):
        self.vector_store_manager = vector_store_manager
        self.llm = llm
        self.embed_model = embed_model
        self.similarity_top_k = similarity_top_k
        self.num_queries = num_queries
        self.reranker_model = reranker_model

        self.service_context = ServiceContext.from_defaults(
            llm=llm,
            embed_model=embed_model,
        )
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store_manager.vector_store,
            service_context=self.service_context,
        )
        self.query_engine: Optional[RetrieverQueryEngine] = None
        self._initialised = False
        self.logger = logging.getLogger(self.__class__.__name__)

    async def initialize(self) -> None:
        """Build the query engine with fusion retrieval and optional re-ranking."""
        self.logger.info("Initialising RAG pipeline")
        retriever = QueryFusionRetriever(
            self.index.as_retriever(similarity_top_k=self.similarity_top_k),
            similarity_top_k=self.similarity_top_k,
            num_queries=self.num_queries,
        )

        # Attempt Cohere re-ranker; fall back gracefully if unavailable
        postprocessors: list[Any] = [
            MetadataReplacementPostProcessor(target_metadata_field="window"),
        ]
        try:
            cohere_rerank = CohereRerank(top_n=5, model=self.reranker_model)
            postprocessors.append(cohere_rerank)
        except Exception as exc:
            self.logger.warning("CohereRerank unavailable (%s); skipping re-rank", exc)

        self.query_engine = RetrieverQueryEngine.from_args(
            retriever=retriever,
            response_synthesizer=ResponseSynthesizer.from_args(response_mode="compact"),
            node_postprocessors=postprocessors,
        )
        self._initialised = True
        self.logger.info("RAG pipeline initialised successfully")

    async def query(
        self, natural_language_query: str, filters: Optional[dict[str, Any]] = None
    ) -> str:
        """Execute a RAG query and return the synthesised text response.

        Args:
            natural_language_query: A trading or market research question.
            filters: Optional metadata filters passed to the retriever.

        Returns:
            Synthesised response string.
        """
        if not self._initialised:
            await self.initialize()

        try:
            response = self.query_engine.query(natural_language_query)
            text = response.response if hasattr(response, "response") else str(response)
            self.logger.debug("RAG query answered (%d chars)", len(text))
            return text
        except Exception as exc:
            self.logger.error("RAG query failed: %s", exc)
            return f"Error answering query: {exc}"

    async def ingest_market_data(self, data: FinancialEmbedding) -> bool:
        """Ingest structured market data into the vector store for retrieval.

        Args:
            data: A structured financial embedding document.

        Returns:
            True on success, False on failure.
        """
        try:
            result = await self.vector_store_manager.add_document(data)
            self.logger.info(
                "Market data ingested: symbol=%s, source=%s, success=%s",
                data.symbol,
                data.source,
                result,
            )
            return result
        except Exception as exc:
            self.logger.error("Failed to ingest market data: %s", exc)
            return False
