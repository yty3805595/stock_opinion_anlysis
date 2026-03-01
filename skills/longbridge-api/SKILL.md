---
name: longbridge-api
description: Longbridge OpenAPI for programmatic quote trading. Use for: (1) Getting real-time and historical market quotes, (2) Submitting, amending, and canceling orders, (3) Querying account balances, positions, and trade history, (4) Subscribing to real-time market data推送, (5) LLM integration via MCP or llms.txt, (6) Automated trading strategies. Supports Python, Node.js, Rust, Go, Java SDKs across HK, US, and CN markets.
---

# Longbridge OpenAPI

## Overview

Longbridge OpenAPI provides programmatic trading and market data interfaces for investors. Covers HK, US, and CN markets with real-time quotes, order management, and portfolio tracking.

## Core Features

- **Trading**: Create, amend, cancel orders; query today's/historical orders and executions
- **Quotes**: Real-time quotes, historical candlesticks, market depth, broker bids
- **Portfolio**: Account balance, positions, cash flow, margin ratios
- **Real-time Subscription**: Push notifications for quotes and order status changes
- **LLM Integration**: MCP server and llms.txt for AI-powered trading assistance

## Supported Markets

| Market | Securities | ETFs | Warrants/CBBCs | Options | Indices |
|--------|-----------|------|----------------|---------|---------|
| HK     | ✓         | ✓    | ✓              |         | ✓ (HSI) |
| US     | ✓         | ✓    | ✓              | ✓       | ✓ (NDX) |
| CN     | ✓         | ✓    |                |         | ✓       |

## Quick Start

### Environment Setup

**Required Environment Variables:**

```bash
export LONGPORT_APP_KEY="your-app-key"
export LONGPORT_APP_SECRET="your-app-secret"
export LONGPORT_ACCESS_TOKEN="your-access-token"
export LONGPORT_REGION="hk"  # or "cn" for mainland China
export LONGPORT_ENABLE_OVERNIGHT="true"  # for US after-hours trading
```

**Getting Credentials:**
1. Download Longbridge App and complete account opening
2. Visit https://open.longbridge.com and log in
3. Go to "Developer Center" → "Personal Center" to get App Key, Secret, and Token

**⚠️ Security Note:** Protect your Access Token—anyone with it can trade on your behalf!

### Basic SDK Usage

**Python:**
```python
from longport.openapi import QuoteContext, TradeContext, Config

config = Config.from_env()
quote_ctx = QuoteContext(config)
trade_ctx = TradeContext(config)

# Get real-time quote
quote = quote_ctx.quote(["AAPL.US"])
print(quote)

# Submit order
from longport.openapi import OrderSide, OrderType, TimeInForceType
order = trade_ctx.submit_order(
    side=OrderSide.Buy,
    symbol="AAPL.US",
    order_type=OrderType.LO,
    submitted_price=150.0,
    submitted_quantity=10,
    time_in_force=TimeInForceType.Day,
)
```

**Node.js:**
```javascript
const { Config, QuoteContext, TradeContext } = require('longport')

const config = Config.fromEnv()
const quoteCtx = await QuoteContext.new(config)
const tradeCtx = await TradeContext.new(config)
```

## Common Operations

### Market Quotes

```python
# Real-time quote (snapshot)
quote = quote_ctx.quote(["700.HK", "AAPL.US", "TSLA.US"])

# Static info (company name, lot size, EPS, etc.)
info = quote_ctx.static_info(["700.HK"])

# Historical candlesticks
candles = quote_ctx.candlesticks("700.HK", CandlestickType.Day, 100)

# Market depth (order book)
depth = quote_ctx.depth("700.HK")

# Intraday ticks
ticks = quote_ctx.intraday("700.HK")
```

### Order Management

```python
# Submit order
order = trade_ctx.submit_order(
    side=OrderSide.Buy,
    symbol="700.HK",
    order_type=OrderType.LO,  # LO=Limit Order, MO=Market Order
    submitted_price=50.0,
    submitted_quantity=100,
    time_in_force=TimeInForceType.Day,  # Day, GTC, IOC, FOK
    remark="API order",
)

# Replace order
trade_ctx.replace_order(order_id="123", submitted_price=51.0)

# Cancel order
trade_ctx.cancel_order(order_id="123")

# Query orders
today_orders = trade_ctx.today_orders()
history_orders = trade_ctx.history_orders(start="2024-01-01", end="2024-12-31")
```

### Portfolio & Assets

```python
# Account balance
balance = trade_ctx.account_balance()

# Stock positions
positions = trade_ctx.stock_positions()

# Fund positions
funds = trade_ctx.fund_positions()

# Cash flow
cashflow = trade_ctx.cashflow(start="2024-01-01", end="2024-12-31")
```

### Real-time Subscriptions

```python
from longport.openapi import SubType

def on_quote(symbol, quote):
    print(f"{symbol}: {quote.last_done}")

def on_order(order):
    print(f"Order {order.order_id}: {order.status}")

quote_ctx.set_on_quote(on_quote)
trade_ctx.set_on_order(on_order)

# Subscribe to real-time quotes
quote_ctx.subscribe(
    symbols=["700.HK", "AAPL.US"],
    subtypes=[SubType.Quote, SubType.Depth, SubType.Trade],
    is_first_push=True,
)

import time
time.sleep(60)  # Keep connection alive
```

## LLM Integration

### Option 1: MCP Server

**Installation:**
```bash
# macOS/Linux
curl -sSL https://raw.githubusercontent.com/longportapp/openapi/main/mcp/install | bash

# Windows
# Download from https://github.com/longportapp/openapi/releases
```

**Configuration (Cursor):**
1. Press `Cmd+Shift+P` → "Add new global MCP server"
2. Edit `mcp.json`:
```json
{
  "mcpServers": {
    "longport-mcp": {
      "command": "/usr/local/bin/longport-mcp",
      "env": {
        "LONGPORT_APP_KEY": "your-key",
        "LONGPORT_APP_SECRET": "your-secret",
        "LONGPORT_ACCESS_TOKEN": "your-token",
        "LONGPORT_REGION": "cn"
      }
    }
  }
}
```

**Example LLM Prompts:**
- "What's the current price of AAPL and TSLA?"
- "How has Tesla performed in the past month?"
- "Show me HK/US market index data"
- "Compare TSLA, AAPL, and NVDA performance over 3 months"
- "Generate a portfolio chart and return data table + pie chart"
- "Check my positions, if any stock drops >3%, sell one-third at market price"

### Option 2: llms.txt for Context

Add to Cursor/AI:
```
https://open.longbridge.com/llms.txt
```

Each doc also available as `.md`:
- `https://open.longbridge.com/docs/getting-started.md`
- `https://open.longbridge.com/docs/quote/pull/static.md`

## Rate Limits

| Category | Limit |
|----------|-------|
| Quote API | Max 500 subscriptions per connection; ≤10 calls/sec; ≤5 concurrent |
| Trade API | ≤30 calls per 30sec; ≥0.02s between calls |

**Note:** SDK handles rate limiting automatically for Quote APIs. Trade APIs require manual rate control.

## SDK References

| Language | Installation | Documentation |
|----------|--------------|---------------|
| Python | `pip3 install longport` | https://longportapp.github.io/openapi/python |
| Node.js | `npm install longport` | https://longportapp.github.io/openapi/nodejs |
| Rust | `cargo add longport` | https://longportapp.github.io/openapi/rust |
| Java | Maven: `com.longport:longport` | https://longportapp.github.io/openapi/java |
| Go | `go get github.com/longportapp/openapi-go` | https://pkg.go.dev/github.com/longportapp/openapi-go |

## API Hosts

| Service | Hong Kong | Mainland China |
|---------|-----------|----------------|
| HTTP API | `https://openapi.longportapp.com` | `https://openapi.longportapp.cn` |
| WebSocket Quotes | `wss://openapi-quote.longportapp.com` | `wss://openapi-quote.longportapp.cn` |
| WebSocket Trade | `wss://openapi-trade.longportapp.com` | `wss://openapi-trade.longportapp.cn` |

## Symbol Format

- Format: `{ticker}.{region}` (e.g., `700.HK`, `AAPL.US`, `TSLA.US`)
- HK market: `.HK` suffix
- US market: `.US` suffix
- CN market: `.CN` suffix

## Error Handling

**Common Error Codes:**

| Code | Description | Solution |
|------|-------------|----------|
| 301600 | Invalid request | Check parameters |
| 301602 | Server error | Retry or contact support |
| 301606 | Rate limited | Reduce request frequency |
| 301607 | Symbol limit exceeded | Reduce symbols per request |

## Code Examples

**Full Trading Workflow:**
```python
from decimal import Decimal
from longport.openapi import QuoteContext, TradeContext, Config, OrderSide, OrderType, TimeInForceType

config = Config.from_env()
quote_ctx = QuoteContext(config)
trade_ctx = TradeContext(config)

# 1. Check positions
positions = trade_ctx.stock_positions()
print("Current positions:", positions)

# 2. Get market quote
quote = quote_ctx.quote(["AAPL.US"])[0]
print(f"AAPL price: {quote.last_done}")

# 3. Submit order if conditions met
if quote.last_done < 150:
    order = trade_ctx.submit_order(
        side=OrderSide.Buy,
        symbol="AAPL.US",
        order_type=OrderType.LO,
        submitted_price=Decimal(str(quote.last_done)),
        submitted_quantity=Decimal("10"),
        time_in_force=TimeInForceType.Day,
        remark="Buying the dip",
    )
    print(f"Order submitted: {order.order_id}")
```

**Real-time Monitoring:**
```python
from longport.openapi import QuoteContext, Config, SubType

config = Config.from_env()
ctx = QuoteContext(config)

def on_quote(symbol, quote):
    print(f"[{symbol}] Price: {quote.last_done}, Volume: {quote.volume}")

ctx.set_on_quote(on_quote)
ctx.subscribe(["700.HK", "AAPL.US"], [SubType.Quote], True)

import time
while True:
    time.sleep(1)
```

## Resources

- **Main Docs**: https://open.longbridge.com/docs
- **SDK API**: https://longportapp.github.io/openapi
- **GitHub**: https://github.com/longportapp/openapi
- **Examples**: https://github.com/longportapp/openapi/tree/master/examples
