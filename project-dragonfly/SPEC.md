# Project Dragonfly — Production Crypto Trading Bot

## Overview
Production-grade crypto trading system combining the best patterns from top open-source repos with institutional-grade architecture for sub-second latency, modular strategies, and survival-first risk management.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      EXTERNAL DATA                         │
│   CEX APIs (Binance, Kraken, Bybit) ← CCXT Pro            │
│   DEX APIs (Hyperliquid, Uniswap) ← CCXT Pro               │
└─────────────────────┬─────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   DATA PIPELINE                            │
│   Ingestion → Normalize → Quality → QuestDB (hot)          │
│                               → ClickHouse (warm)          │
│                               → Dragonfly (cache)           │
└─────────────────────┬─────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 KNOWLEDGE SYSTEM                           │
│   Qdrant (vectors) + Neo4j (knowledge graph)               │
│   RAG pipeline via LlamaIndex + Gemini/GPT-4               │
│   Time-decay scoring on documents                           │
└─────────────────────┬─────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  STRATEGY LAYER                            │
│   Momentum | Arbitrage | Market Making | Mean Reversion | ML│
│   Strategy Ensemble + Risk-Adjusted Selection               │
└─────────────────────┬─────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 PRE-TRADE RISK GATE                        │
│   Position Limits | Drawdown | Correlation | Circuit Breakers│
└─────────────────────┬─────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  EXECUTION LAYER                            │
│   CCXT Interface | Smart Router | Slippage Optimizer       │
└─────────────────────┬─────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 RISK MANAGEMENT                           │
│   Real-time P&L | Portfolio Risk | Circuit Breakers         │
└─────────────────────┬─────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 OBSERVABILITY                              │
│   Dashboard (Flask/Socket.io) | Trade Log | P&L Graph      │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack
- **Language:** Python 3.11+
- **Exchange Layer:** CCXT Pro
- **Real-time Streaming:** NATS (or Redis Streams as fallback)
- **Time-Series DB:** QuestDB (hot) + ClickHouse (warm analytics)
- **Cache:** Dragonfly
- **Vector DB:** Qdrant
- **Knowledge Graph:** Neo4j
- **RAG:** LlamaIndex + Gemini
- **Dashboard:** Flask + Socket.IO + Chart.js
- **Strategy Framework:** Custom event-driven framework (inspired by Freqtrade/Jesse)
- **Backtesting:** Custom engine with market impact modeling
- **Container:** Docker + docker-compose

## Project Structure
```
project-dragonfly/
├── docker-compose.yml
├── requirements.txt
├── configs/
│   ├── exchanges.yaml
│   ├── strategies.yaml
│   └── risk.yaml
├── data-pipeline/
│   ├── ingestion/         # CCXT data fetching
│   ├── streaming/         # NATS/Redis publish
│   └── storage/           # QuestDB, ClickHouse writers
├── execution/
│   ├── ccxt_interface.py  # Unified exchange abstraction
│   ├── order_manager.py   # Order lifecycle
│   └── connection_mgr.py   # WebSocket/reconnect logic
├── strategies/
│   ├── base.py            # Abstract base class
│   ├── momentum.py
│   ├── arbitrage.py
│   ├── market_making.py
│   ├── mean_reversion.py
│   └── ml_signal.py
├── risk/
│   ├── position_mgr.py     # Position tracking
│   ├── pretrade_gate.py    # Pre-trade risk checks
│   ├── drawdown_ctrl.py   # Drawdown limits
│   └── circuit_breaker.py # Emergency stops
├── knowledge/
│   ├── vector_store.py     # Qdrant wrapper
│   ├── knowledge_graph.py  # Neo4j wrapper
│   └── rag_pipeline.py    # LlamaIndex pipeline
├── dashboard/
│   ├── app.py             # Flask + Socket.IO server
│   ├── trade_logger.py    # Trade log writer
│   └── charts.py          # Chart.js data endpoints
└── backtest/
    ├── engine.py
    ├── market_impact.py
    └── slippage.py
```

## Performance Targets
- Orderbook cache read: <0.2ms
- Time-series query (1hr ticks): <5ms
- Vector retrieval (filtered): <10ms
- Pre-trade risk gate: <10ms
- LLM RAG answer: 400–800ms
- Order execution: <50ms

## Setup
```bash
docker-compose up -d
python main.py --mode paper  # Paper trading
python main.py --mode live    # Live trading (requires keys)
python main.py --mode backtest  # Run backtest
```

## Strategies
1. **Momentum** — trend-following with RSI/MACD confirmation
2. **Arbitrage** — cross-exchange triangular/spread
3. **Market Making** — bid-ask spread capture with inventory management
4. **Mean Reversion** — Bollinger Bands + RSI reversion
5. **ML Signal** — feature-based prediction with online learning

## Risk Controls
- Max position size per asset: configurable % of portfolio
- Max drawdown threshold: stop trading if P&L drops below threshold
- Correlation risk: limit exposure to correlated assets
- Circuit breakers: auto-stop on abnormal volatility/volume
- Pre-trade gate: all orders pass through risk checks before execution
