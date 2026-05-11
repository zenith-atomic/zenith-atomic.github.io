"""NATS/Redis streaming layer for market data."""
import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StreamMessage:
    """Wrapper for streamed messages."""
    subject: str
    data: Dict[str, Any]
    timestamp: float


class StreamManager:
    """
    Manages streaming of normalized market data via NATS or Redis.

    Falls back to Redis Streams if NATS is unavailable.
    """

    SUBJECTS = ["market.ohlcv", "market.orderbook", "market.trades", "market.ticker"]

    def __init__(self, nats_url: str = "nats://localhost:4222", redis_url: Optional[str] = None):
        """
        Initialize StreamManager.

        Args:
            nats_url: NATS server URL
            redis_url: Redis URL for fallback
        """
        self.nats_url = nats_url
        self.redis_url = redis_url or "redis://localhost:6379"
        self._nats_conn = None
        self._redis_conn = None
        self._use_redis = False
        self._subscriptions: Dict[str, List[Callable]] = {}
        self._queue_task: Optional[asyncio.Task] = None
        self._source_queue: Optional[asyncio.Queue] = None

    async def connect(self) -> bool:
        """Connect to NATS or Redis. Returns True if connected."""
        try:
            import nats
            self._nats_conn = await nats.connect(self.nats_url, connect_timeout=5)
            logger.info("Connected to NATS at %s", self.nats_url)
            return True
        except Exception as e:
            logger.warning("NATS connection failed: %s. Trying Redis fallback.", e)
            try:
                import redis.asyncio as redis
                self._redis_conn = redis.from_url(self.redis_url, decode_responses=True)
                await self._redis_conn.ping()
                self._use_redis = True
                logger.info("Connected to Redis at %s", self.redis_url)
                return True
            except Exception as e2:
                logger.error("Redis fallback also failed: %s", e2)
                return False

    async def publish(self, subject: str, data: Dict[str, Any]) -> bool:
        """
        Publish data to a subject.

        Args:
            subject: NATS/Redis subject string
            data: Data dict to publish

        Returns:
            True if published successfully
        """
        try:
            if self._use_redis:
                import redis.asyncio as redis
                key = f"stream:{subject}"
                await self._redis_conn.xadd(key, {"data": json.dumps(data)})
            else:
                msg = StreamMessage(subject=subject, data=data, timestamp=asyncio.get_event_loop().time())
                await self._nats_conn.publish(subject, json.dumps(data).encode())
            return True
        except Exception as e:
            logger.error("Publish error on %s: %s", subject, e)
            return False

    async def subscribe(self, subject: str, callback: Callable) -> None:
        """
        Subscribe to a subject.

        Args:
            subject: Subject to subscribe to
            callback: Async callable invoked with dict data
        """
        if subject not in self._subscriptions:
            self._subscriptions[subject] = []
        self._subscriptions[subject].append(callback)

        if not self._use_redis:
            try:
                import nats
                sub = await self._nats_conn.subscribe(subject)
                asyncio.create_task(self._nats_reader(sub, subject))
            except Exception as e:
                logger.error("NATS subscribe error for %s: %s", subject, e)

    async def _nats_reader(self, sub: Any, subject: str) -> None:
        """Read messages from NATS subscription."""
        async for msg in sub.messages:
            try:
                data = json.loads(msg.data.decode())
                for cb in self._subscriptions.get(subject, []):
                    await cb(data)
            except Exception as e:
                logger.error("NATS reader error: %s", e)

    async def start_consumers(self, source_queue: asyncio.Queue) -> None:
        """
        Start consuming from source queue and distributing to subscribers.

        Args:
            source_queue: asyncio.Queue to consume from
        """
        self._source_queue = source_queue
        self._queue_task = asyncio.create_task(self._queue_consumer())

    async def _queue_consumer(self) -> None:
        """Consume messages from queue and publish to all subscribers."""
        while True:
            try:
                msg_type, data = await self._source_queue.get()
                subject_map = {
                    "ohlcv": "market.ohlcv",
                    "orderbook": "market.orderbook",
                    "trade": "market.trades",
                    "ticker": "market.ticker",
                }
                subject = subject_map.get(msg_type, "market.unknown")
                await self.publish(subject, data)

                # Also dispatch to local callbacks
                for cb in self._subscriptions.get(subject, []):
                    await cb(data)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Queue consumer error: %s", e)

    async def flush(self) -> None:
        """Flush any buffered data."""
        pass  # NATS/Redis handle their own buffering

    async def close(self) -> None:
        """Close all connections."""
        if self._queue_task:
            self._queue_task.cancel()
        if self._nats_conn:
            await self._nats_conn.close()
        if self._redis_conn:
            await self._redis_conn.close()
        logger.info("StreamManager closed")
