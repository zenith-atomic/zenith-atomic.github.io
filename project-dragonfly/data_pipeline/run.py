"""Main entry point for Project Dragonfly data pipeline."""
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_pipeline.ingestion.market_data_fetcher import MarketDataFetcher
from data_pipeline.streaming.stream_manager import StreamManager
from data_pipeline.storage.questdb_writer import QuestDBWriter
from data_pipeline.storage.clickhouse_writer import ClickHouseWriter
from data_pipeline.quality.data_quality import DataQualityChecker
from data_pipeline.normalizer import OHLCV, OrderBook, Trade

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class PipelineConfig:
    """Pipeline configuration loaded from YAML."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._raw: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load config from YAML file."""
        with open(self.config_path) as f:
            self._raw = yaml.safe_load(f)
        logger.info("Loaded config from %s", self.config_path)

    @property
    def ohlcv_intervals(self) -> List[str]:
        return self._raw.get("pipeline", {}).get("ohlcv_intervals", ["1m", "5m", "1h"])

    @property
    def orderbook_depth(self) -> int:
        return self._raw.get("pipeline", {}).get("orderbook_depth", 20)

    @property
    def trade_aggregation(self) -> str:
        return self._raw.get("pipeline", {}).get("trade_aggregation", "100ms")

    @property
    def questdb_host(self) -> str:
        return self._raw.get("pipeline", {}).get("questdb", {}).get("host", "localhost")

    @property
    def questdb_port(self) -> int:
        return self._raw.get("pipeline", {}).get("questdb", {}).get("port", 9000)

    @property
    def questdb_batch_size(self) -> int:
        return self._raw.get("pipeline", {}).get("questdb", {}).get("batch_size", 100)

    @property
    def questdb_flush_interval_ms(self) -> int:
        return self._raw.get("pipeline", {}).get("questdb", {}).get("flush_interval_ms", 1000)

    @property
    def clickhouse_host(self) -> str:
        return self._raw.get("pipeline", {}).get("clickhouse", {}).get("host", "localhost")

    @property
    def clickhouse_port(self) -> int:
        return self._raw.get("pipeline", {}).get("clickhouse", {}).get("port", 9000)

    @property
    def clickhouse_database(self) -> str:
        return self._raw.get("pipeline", {}).get("clickhouse", {}).get("database", "dragonfly")

    @property
    def nats_url(self) -> str:
        return self._raw.get("pipeline", {}).get("nats", {}).get("url", "nats://localhost:4222")

    @property
    def exchanges(self) -> List[Dict[str, Any]]:
        return self._raw.get("exchanges", [])


class DataPipeline:
    """
    Main data pipeline orchestrator.

    Coordinates data fetching, streaming, storage, and quality checks.
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self._queue: Optional[asyncio.Queue] = None
        self._fetcher: Optional[MarketDataFetcher] = None
        self._stream_manager: Optional[StreamManager] = None
        self._questdb: Optional[QuestDBWriter] = None
        self._clickhouse: Optional[ClickHouseWriter] = None
        self._quality: Optional[DataQualityChecker] = None
        self._running = False
        self._tasks: List[asyncio.Task] = []

    async def start(self) -> None:
        """Start all pipeline components."""
        logger.info("Starting Project Dragonfly data pipeline...")

        # Create shared queue
        self._queue = asyncio.Queue(maxsize=10000)

        # Exchange config for fetcher
        exchange_config = {}
        for ex in self.config.exchanges:
            exchange_config[ex["id"]] = {"symbols": ex.get("symbols", [])}

        # Create components
        self._fetcher = MarketDataFetcher(
            exchange_ids=[ex["id"] for ex in self.config.exchanges if ex.get("enabled", True)],
            queue=self._queue,
            config=exchange_config,
        )

        self._stream_manager = StreamManager(nats_url=self.config.nats_url)
        connected = await self._stream_manager.connect()
        if not connected:
            logger.warning("StreamManager: no NATS/Redis available, running in-memory only")

        self._questdb = QuestDBWriter(
            host=self.config.questdb_host,
            port=self.config.questdb_port,
            batch_size=self.config.questdb_batch_size,
            flush_interval_ms=self.config.questdb_flush_interval_ms,
        )

        self._clickhouse = ClickHouseWriter(
            host=self.config.clickhouse_host,
            port=self.config.clickhouse_port,
            database=self.config.clickhouse_database,
        )

        self._quality = DataQualityChecker(window_size=100)

        # Start storage
        await self._questdb.start()
        await self._clickhouse.connect()
        await self._clickhouse.start()

        # Start stream consumers
        await self._stream_manager.start_consumers(self._queue)

        # Start queue processor
        self._tasks.append(asyncio.create_task(self._process_queue()))

        # Start fetcher
        asyncio.create_task(self._fetcher.start())

        self._running = True
        logger.info("Pipeline started successfully")

    async def _process_queue(self) -> None:
        """Process messages from the shared queue."""
        while self._running:
            try:
                msg_type, data = await asyncio.wait_for(self._queue.get(), timeout=1.0)

                # Quality checks
                if msg_type == "ohlcv":
                    from data_pipeline.normalizer import normalize_ohlcv
                    ohlcv_obj = normalize_ohlcv(data.get("exchange", ""), data, data.get("symbol", ""), data.get("timeframe", "1m"))
                    result = self._quality.check_ohlcv(ohlcv_obj)
                    if result.passed:
                        await self._questdb.write_ohlcv(data)
                        await self._clickhouse.write_ohlcv(data)
                elif msg_type == "orderbook":
                    from data_pipeline.normalizer import normalize_orderbook
                    ob_obj = normalize_orderbook(
                        data.get("exchange", ""),
                        data.get("symbol", ""),
                        data.get("bids", []),
                        data.get("asks", []),
                    )
                    result = self._quality.check_orderbook(ob_obj)
                    if result.passed:
                        await self._questdb.write_orderbook(data.get("symbol", ""), data.get("bids", []), data.get("asks", []))
                        await self._clickhouse.write_orderbook(data.get("symbol", ""), data.get("bids", []), data.get("asks", []))
                elif msg_type == "trade":
                    await self._questdb.write_trade(data)
                    await self._clickhouse.write_trade(data)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("Queue processor error: %s", e)

    async def run(self) -> None:
        """Run the pipeline until shutdown."""
        await self.start()
        try:
            while self._running:
                await asyncio.sleep(5)
                metrics = self._quality.get_metrics()
                logger.info("Quality metrics: %s", metrics)
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        """Stop all pipeline components gracefully."""
        logger.info("Stopping pipeline...")
        self._running = False

        for task in self._tasks:
            task.cancel()

        if self._fetcher:
            await self._fetcher.stop()
        if self._stream_manager:
            await self._stream_manager.close()
        if self._questdb:
            await self._questdb.stop()
        if self._clickhouse:
            await self._clickhouse.stop()

        logger.info("Pipeline stopped")


async def main() -> None:
    """Main entry point."""
    base_dir = Path(__file__).parent.parent
    config = PipelineConfig(base_dir / "configs" / "pipeline.yaml")

    pipeline = DataPipeline(config)

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(pipeline.stop()))

    try:
        await pipeline.run()
    except KeyboardInterrupt:
        pass
    finally:
        await pipeline.stop()


if __name__ == "__main__":
    asyncio.run(main())
