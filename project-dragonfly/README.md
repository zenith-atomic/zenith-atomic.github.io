# Project Dragonfly — Production Crypto Trading Bot

## Architecture

- **Data Pipeline** (`data_pipeline/`): Real-time market data ingestion → QuestDB (hot) + ClickHouse (warm)
- **Execution** (`execution/`): CCXT-based unified multi-exchange interface
- **Strategies** (`strategies/`): Momentum, Arbitrage, Market Making, Mean Reversion, ML Signal
- **Risk** (`risk/`): Position management, pre-trade gate, drawdown control, circuit breakers
- **Knowledge** (`knowledge/`): Qdrant vector store + Neo4j knowledge graph + RAG pipeline
- **Dashboard** (`dashboard/`): Flask + Socket.IO real-time monitoring UI

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start infrastructure

```bash
docker compose up -d
```

### 3. Run the bot

```bash
python main.py
```

### 4. Open dashboard

```
http://localhost:5000
```

## Testing

```bash
python tests/test_imports.py
```

## Configuration

All config files are in `configs/`. Update YAML files to change strategy parameters, risk thresholds, and exchange credentials.

## Environment Variables

```env
# Exchange API keys (sandbox/testnet recommended for paper trading)
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
BYBIT_API_KEY=your_key
BYBIT_API_SECRET=your_secret

# OpenAI (for LLM-based strategies and RAG)
OPENAI_API_KEY=your_key

# Neo4j (knowledge graph)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Qdrant (vector store)
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

## Module Overview

| Module | Responsibility |
|--------|---------------|
| `data_pipeline/` | Ingest, normalize, and quality-check market data; write to QuestDB (hot) and ClickHouse (warm) |
| `execution/` | Unified CCXT interface for multi-exchange order execution and market data |
| `strategies/` | Trading strategies: Momentum, Arbitrage, Market Making, Mean Reversion, ML Signal |
| `risk/` | Position sizing, pre-trade risk gates, drawdown control, circuit breakers |
| `knowledge/` | Vector store (Qdrant), knowledge graph (Neo4j), and RAG pipeline for informed decisions |
| `dashboard/` | Flask + Socket.IO monitoring UI with real-time trade log and P&L charts |