"""Test entry point for strategy layer."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Any, Optional

import yaml

from strategies import (
    ArbitrageStrategy,
    MomentumStrategy,
    Signal,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def run_momentum_test() -> None:
    """Test momentum strategy with simulated market data."""
    config = {
        "mode": "paper",
        "short_period": 5,
        "long_period": 10,
        "size_percentage": 0.1,
        "symbol": "BTC/USDT",
    }
    strategy = MomentumStrategy("momentum_test", config)
    print(f"\n=== Momentum Strategy Test ===")
    print(f"Config: {config}")
    print(f"State: {strategy.get_state()}")

    prices = [100 + i * 0.5 + (i % 7 - 3) * 0.2 for i in range(30)]
    signals: list[Signal] = []

    for i, price in enumerate(prices):
        data = {"symbol": "BTC/USDT", "price": price, "timestamp": time.time()}
        signal = await strategy.on_market_data(data)
        if signal:
            signals.append(signal)
            print(f"  Signal #{len(signals)}: {signal.signal_type.value} at ${price:.2f}")

    print(f"\nTotal signals generated: {len(signals)}")
    print(f"Metrics: {strategy.get_metrics()}")


async def run_arbitrage_test() -> None:
    """Test arbitrage strategy with simulated cross-exchange data."""
    config = {
        "mode": "paper",
        "min_spread_bps": 10.0,
        "max_order_size": 0.05,
        "symbol": "ETH/USDT",
        "exchange_ids": ["binance", "hyperliquid"],
    }
    strategy = ArbitrageStrategy("arb_test", config)
    print(f"\n=== Arbitrage Strategy Test ===")
    print(f"Config: {config}")
    print(f"State: {strategy.get_state()}")

    events = [
        {"exchange_id": "binance", "symbol": "ETH/USDT", "price": 1800.0, "timestamp": 1},
        {"exchange_id": "hyperliquid", "symbol": "ETH/USDT", "price": 1802.5, "timestamp": 2},
        {"exchange_id": "binance", "symbol": "ETH/USDT", "price": 1801.0, "timestamp": 3},
        {"exchange_id": "hyperliquid", "symbol": "ETH/USDT", "price": 1803.0, "timestamp": 4},
    ]

    signals: list[Signal] = []
    for event in events:
        signal = await strategy.on_market_data(event)
        if signal:
            signals.append(signal)
            print(f"  Signal: {signal.signal_type.value} at ${signal.price:.2f}")

    print(f"\nTotal signals generated: {len(signals)}")
    print(f"Metrics: {strategy.get_metrics()}")


async def run_simulated_stream_test() -> None:
    """Simulate a market data stream and process with strategies."""
    print(f"\n=== Simulated Stream Test ===")

    momentum_config = {
        "mode": "paper",
        "short_period": 5,
        "long_period": 15,
        "size_percentage": 0.1,
        "symbol": "BTC/USDT",
    }
    momentum = MomentumStrategy("momentum_stream", momentum_config)

    queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
    results: list[Signal] = []

    async def producer() -> None:
        base_price = 50000.0
        for i in range(50):
            price = base_price + i * 50 + (i % 11 - 5) * 30
            await queue.put({"symbol": "BTC/USDT", "price": price, "timestamp": time.time()})
            await asyncio.sleep(0.01)

    async def consumer() -> None:
        while True:
            data = await queue.get()
            if data is None:
                break
            signal = await momentum.on_market_data(data)
            if signal:
                results.append(signal)
                print(f"  [{data['timestamp']:.0f}] {signal.signal_type.value} @ ${data['price']:.2f}")
            await asyncio.sleep(0.01)

    await asyncio.gather(producer(), consumer())

    print(f"\nProcessed {len(results)} signals from stream")
    for s in results:
        print(f"  {s.signal_type.value}: {s.symbol} @ ${s.price}")


async def main() -> None:
    """Run all tests."""
    print("=" * 50)
    print("Project Dragonfly - Strategy Layer Test")
    print("=" * 50)

    await run_momentum_test()
    await run_arbitrage_test()
    await run_simulated_stream_test()

    print("\n" + "=" * 50)
    print("All tests completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())