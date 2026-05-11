import ccxt
from ccxt import Exchange
from typing import Dict, List, Optional, Order, Position, Any
from pydantic import BaseModel, Field
from enum import Enum
import asyncio
import logging
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OrderSide(str, Enum): BUY = "buy"; SELL = "sell"
class OrderType(str, Enum): MARKET = "market"; LIMIT = "limit"; STOP_LOSS = "stop_loss"; TAKE_PROFIT = "take_profit"
class OrderStatus(str, Enum): OPEN = "open"; FILLED = "filled"; PARTIAL = "partial"; CANCELLED = "cancelled"; REJECTED = "rejected"

class OrderRequest(BaseModel):
    """
    Represents a request to create an order on an exchange.
    """
    exchange_id: str = Field(..., description="ID of the exchange (e.g., 'binance', 'kraken')")
    symbol: str = Field(..., description="Trading pair symbol (e.g., 'BTC/USDT')")
    side: OrderSide = Field(..., description="Side of the order (buy or sell)")
    order_type: OrderType = Field(OrderType.MARKET, description="Type of order (market, limit, stop_loss, take_profit)")
    size: float = Field(..., gt=0, description="Amount of base currency to trade (for market orders, this is in quote currency if not explicitly set by exchange)")
    price: Optional[float] = Field(None, gt=0, description="Price for limit or stop orders")
    stop_price: Optional[float] = Field(None, gt=0, description="Stop price for stop loss or take profit orders")
    reduce_only: bool = Field(False, description="True if the order is to reduce an existing position")
    client_order_id: Optional[str] = Field(None, description="Optional client-assigned order ID")

class OrderResult(BaseModel):
    """
    Represents the result of an order placement.
    """
    exchange_id: str
    symbol: str
    client_order_id: Optional[str]
    exchange_order_id: str
    status: OrderStatus
    side: OrderSide
    order_type: OrderType
    price: float
    amount: float
    filled: float
    remaining: float
    cost: float
    datetime: str
    timestamp: int
    info: Dict[str, Any]

class Ticker(BaseModel):
    """
    Represents a ticker snapshot for a trading pair.
    """
    exchange_id: str
    symbol: str
    timestamp: int
    datetime: str
    high: Optional[float]
    low: Optional[float]
    bid: Optional[float]
    bid_volume: Optional[float]
    ask: Optional[float]
    ask_volume: Optional[float]
    vwap: Optional[float]
    open: Optional[float]
    close: Optional[float]
    last: Optional[float]
    previous_close: Optional[float]
    change: Optional[float]
    percentage: Optional[float]
    average: Optional[float]
    base_volume: Optional[float]
    quote_volume: Optional[float]
    info: Dict[str, Any]

class OrderBook(BaseModel):
    """
    Represents an order book snapshot.
    """
    exchange_id: str
    symbol: str
    timestamp: int
    datetime: str
    nonce: Optional[int]
    bids: List[List[float]] = [] # [[price, amount], ...]
    asks: List[List[float]] = [] # [[price, amount], ...]
    info: Dict[str, Any]

class CCXTInterface:
    """
    Unified CCXT interface for all exchange operations.
    Handles exchange initialization, order management, market data fetching,
    and basic websocket connection management.
    """
    def __init__(self, config: Dict):
        self.exchanges: Dict[str, Exchange] = {}
        self.symbol_map: Dict[str, Dict[str, str]] = {}  # exchange_id -> {symbol: ccxt_symbol}
        self._wsConnections: Dict[str, asyncio.Queue] = {}
        self.config = config # Store the initial config

    async def initialize(self, exchange_configs: List[Dict]) -> None:
        """
        Initializes exchange instances from provided configurations.
        Each configuration dict should contain 'id' and any API keys/secrets.
        """
        for cfg in exchange_configs:
            exchange_id = cfg['id']
            try:
                exchange_class = getattr(ccxt.pro, exchange_id) # Use ccxt.pro for async
                exchange = exchange_class({
                    'apiKey': cfg.get('apiKey'),
                    'secret': cfg.get('secret'),
                    'password': cfg.get('password'),
                    'enableRateLimit': True,
                    **cfg.get('options', {})
                })
                await exchange.load_markets()
                self.exchanges[exchange_id] = exchange
                logger.info(f"Initialized exchange: {exchange_id}")
            except Exception as e:
                logger.error(f"Failed to initialize exchange {exchange_id}: {e}")
                raise

    async def create_order(self, req: OrderRequest) -> OrderResult:
        """
        Submits an order to the specified exchange.
        """
        exchange = self._get_exchange(req.exchange_id)
        try:
            params = {'clientOrderId': req.client_order_id} if req.client_order_id else {}
            if req.reduce_only:
                params['reduceOnly'] = True
            if req.stop_price:
                params['stopPrice'] = req.stop_price

            ccxt_order = await exchange.create_order(
                symbol=req.symbol,
                type=req.order_type.value,
                side=req.side.value,
                amount=req.size,
                price=req.price,
                params=params
            )
            return OrderResult(
                exchange_id=req.exchange_id,
                symbol=req.symbol,
                client_order_id=ccxt_order.get('clientOrderId'),
                exchange_order_id=ccxt_order['id'],
                status=OrderStatus(ccxt_order['status']),
                side=OrderSide(ccxt_order['side']),
                order_type=OrderType(ccxt_order['type']),
                price=ccxt_order.get('price', 0.0),
                amount=ccxt_order.get('amount', 0.0),
                filled=ccxt_order.get('filled', 0.0),
                remaining=ccxt_order.get('remaining', 0.0),
                cost=ccxt_order.get('cost', 0.0),
                datetime=ccxt_order['datetime'],
                timestamp=ccxt_order['timestamp'],
                info=ccxt_order['info']
            )
        except ccxt.NetworkError as e:
            logger.error(f"Network error creating order on {req.exchange_id} for {req.symbol}: {e}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error creating order on {req.exchange_id} for {req.symbol}: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred creating order on {req.exchange_id} for {req.symbol}: {e}")
            raise

    async def cancel_order(self, exchange_id: str, order_id: str, symbol: str) -> bool:
        """
        Cancels an open order on the specified exchange.
        """
        exchange = self._get_exchange(exchange_id)
        try:
            await exchange.cancel_order(order_id, symbol)
            logger.info(f"Cancelled order {order_id} on {exchange_id} for {symbol}")
            return True
        except ccxt.NetworkError as e:
            logger.error(f"Network error cancelling order {order_id} on {exchange_id}: {e}")
            return False
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error cancelling order {order_id} on {exchange_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred cancelling order {order_id} on {exchange_id}: {e}")
            return False

    async def get_balance(self, exchange_id: str, asset: str) -> float:
        """
        Fetches the available balance for a specific asset on an exchange.
        """
        exchange = self._get_exchange(exchange_id)
        try:
            balance = await exchange.fetch_balance()
            if asset in balance and 'free' in balance[asset]:
                return float(balance[asset]['free'])
            return 0.0
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching balance for {asset} on {exchange_id}: {e}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching balance for {asset} on {exchange_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching balance for {asset} on {exchange_id}: {e}")
            raise

    async def get_position(self, exchange_id: str, symbol: str) -> Position:
        """
        Fetches the current position for a given symbol on an exchange.
        Note: CCXT's Position type is not directly exposed as a class,
        so we'll return the raw dictionary structure and let Pydantic handle validation
        if a Position BaseModel is later defined. For now, using Any.
        """
        exchange = self._get_exchange(exchange_id)
        try:
            positions = await exchange.fetch_positions([symbol])
            if positions:
                return positions[0] # Assuming first match is the desired position
            return {} # Return empty dict if no position
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching position for {symbol} on {exchange_id}: {e}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching position for {symbol} on {exchange_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching position for {symbol} on {exchange_id}: {e}")
            raise

    async def get_open_orders(self, exchange_id: str, symbol: str) -> List[Order]:
        """
        Fetches all open orders for a given symbol on an exchange.
        Note: CCXT's Order type is not directly exposed as a class,
        so we'll return the raw dictionary structure.
        """
        exchange = self._get_exchange(exchange_id)
        try:
            orders = await exchange.fetch_open_orders(symbol)
            return orders
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching open orders for {symbol} on {exchange_id}: {e}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching open orders for {symbol} on {exchange_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching open orders for {symbol} on {exchange_id}: {e}")
            raise

    async def get_ticker(self, exchange_id: str, symbol: str) -> Ticker:
        """
        Fetches the ticker information for a specific trading pair.
        """
        exchange = self._get_exchange(exchange_id)
        try:
            ticker = await exchange.fetch_ticker(symbol)
            return Ticker(
                exchange_id=exchange_id,
                symbol=symbol,
                timestamp=ticker['timestamp'],
                datetime=ticker['datetime'],
                high=ticker.get('high'),
                low=ticker.get('low'),
                bid=ticker.get('bid'),
                bid_volume=ticker.get('bidVolume'),
                ask=ticker.get('ask'),
                ask_volume=ticker.get('askVolume'),
                vwap=ticker.get('vwap'),
                open=ticker.get('open'),
                close=ticker.get('close'),
                last=ticker.get('last'),
                previous_close=ticker.get('previousClose'),
                change=ticker.get('change'),
                percentage=ticker.get('percentage'),
                average=ticker.get('average'),
                base_volume=ticker.get('baseVolume'),
                quote_volume=ticker.get('quoteVolume'),
                info=ticker['info']
            )
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching ticker for {symbol} on {exchange_id}: {e}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching ticker for {symbol} on {exchange_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching ticker for {symbol} on {exchange_id}: {e}")
            raise

    async def get_orderbook(self, exchange_id: str, symbol: str, limit: int = 20) -> OrderBook:
        """
        Fetches the order book for a specific trading pair.
        """
        exchange = self._get_exchange(exchange_id)
        try:
            orderbook = await exchange.fetch_order_book(symbol, limit=limit)
            return OrderBook(
                exchange_id=exchange_id,
                symbol=symbol,
                timestamp=orderbook['timestamp'],
                datetime=orderbook['datetime'],
                nonce=orderbook.get('nonce'),
                bids=orderbook['bids'],
                asks=orderbook['asks'],
                info=orderbook['info']
            )
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching orderbook for {symbol} on {exchange_id}: {e}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching orderbook for {symbol} on {exchange_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching orderbook for {symbol} on {exchange_id}: {e}")
            raise

    async def get_ohlcv(self, exchange_id: str, symbol: str, timeframe: str = '1m', limit: int = 100) -> List[List[float]]:
        """
        Fetches OHLCV data for a trading pair.
        Returns a list of lists: [[timestamp, open, high, low, close, volume], ...]
        """
        exchange = self._get_exchange(exchange_id)
        try:
            ohlcv_data = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            return ohlcv_data
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching OHLCV for {symbol} on {exchange_id}: {e}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching OHLCV for {symbol} on {exchange_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching OHLCV for {symbol} on {exchange_id}: {e}")
            raise

    def set_websocket_handler(self, exchange_id: str, queue: asyncio.Queue):
        """
        Set an asyncio Queue for receiving websocket messages from a specific exchange.
        """
        self._wsConnections[exchange_id] = queue
        logger.info(f"WebSocket handler set for {exchange_id}")

    async def start_websocket(self, exchange_id: str, symbols: List[str]):
        """
        Starts a websocket connection for an exchange to subscribe to market data or user data.
        This is a placeholder; actual CCXT Pro websocket implementation will go here.
        For now, it will simulate receiving messages.
        """
        if exchange_id not in self.exchanges:
            logger.error(f"Exchange {exchange_id} not initialized.")
            return

        if exchange_id not in self._wsConnections:
            logger.warning(f"No websocket handler (asyncio.Queue) set for {exchange_id}. Cannot start websocket.")
            return

        exchange = self.exchanges[exchange_id]
        queue = self._wsConnections[exchange_id]

        logger.info(f"Starting websocket for {exchange_id} for symbols: {symbols}")
        # In a real scenario, you'd use exchange.watch_trades, exchange.watch_orders, etc.
        # For this example, we'll just put a dummy message in the queue.
        try:
            # Example: watch_ohlcv (simplified for demonstration)
            # This part would typically be more complex, handling different streams
            # and feeding them into the queue.
            # For now, let's assume we're just "starting" and the ConnectionManager will manage actual subscriptions.
            logger.warning(f"Websocket connection for {exchange_id} started (simulated). "
                           "Actual CCXT Pro watch methods need to be integrated here.")
            await asyncio.sleep(1) # Simulate connection time
            await queue.put({"exchange": exchange_id, "type": "connection_established", "symbols": symbols})

        except Exception as e:
            logger.error(f"Error starting websocket for {exchange_id}: {e}")


    async def stop_websocket(self, exchange_id: str):
        """
        Stops the websocket connection for the specified exchange.
        """
        if exchange_id not in self.exchanges:
            logger.warning(f"Exchange {exchange_id} not initialized. Nothing to stop.")
            return

        # In a real CCXT Pro scenario, you might have specific ways to close the connection.
        # For now, we'll just log and remove the queue.
        if exchange_id in self._wsConnections:
            del self._wsConnections[exchange_id]
            logger.info(f"WebSocket connection stopped and handler removed for {exchange_id}")
        else:
            logger.warning(f"No active websocket connection found for {exchange_id}.")


    def _get_exchange(self, exchange_id: str) -> Exchange:
        """Helper to retrieve an initialized exchange instance."""
        if exchange_id not in self.exchanges:
            raise ValueError(f"Exchange {exchange_id} not initialized.")
        return self.exchanges[exchange_id]
