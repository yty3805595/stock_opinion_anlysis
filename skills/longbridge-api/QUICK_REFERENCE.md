# Longbridge API Quick Reference

## Environment Setup

```bash
export LONGPORT_APP_KEY="xxx"
export LONGPORT_APP_SECRET="xxx"
export LONGPORT_ACCESS_TOKEN="xxx"
export LONGPORT_REGION="hk"  # or "cn"
```

## Symbol Format
- HK: `700.HK`, `00700.HK`
- US: `AAPL.US`, `TSLA.US`, `NVDA.US`
- CN: `600519.SH`, `000001.SZ`

## Import Shortcuts

```python
from longport.openapi import (
    QuoteContext, TradeContext, Config,
    OrderSide, OrderType, TimeInForceType,
    CandlestickType, SubType,
)
```

## Quote Operations

| Operation | Code |
|-----------|------|
| Snapshot quote | `ctx.quote(["AAPL.US"])` |
| Static info | `ctx.static_info(["AAPL.US"])` |
| Candlesticks | `ctx.candlesticks("AAPL.US", CandlestickType.Day, 100)` |
| Depth/Book | `ctx.depth("AAPL.US")` |
| Intraday ticks | `ctx.intraday("AAPL.US")` |
| Brokers | `ctx.brokers("AAPL.US")` |
| Trade history | `ctx.trade("AAPL.US")` |

## Order Operations

```python
# Submit order
ctx.submit_order(
    side=OrderSide.Buy,           # Buy / Sell
    symbol="AAPL.US",
    order_type=OrderType.LO,      # LO=Limit, MO=Market
    submitted_price=150.0,
    submitted_quantity=10,
    time_in_force=TimeInForceType.Day,  # Day / GTC / IOC / FOK
)

# Cancel/Replace
ctx.cancel_order(order_id)
ctx.replace_order(order_id, submitted_price=155.0)

# Query orders
ctx.today_orders()
ctx.history_orders(start="2024-01-01", end="2024-12-31")
```

## Portfolio

```python
ctx.account_balance()      # Account balance
ctx.stock_positions()     # Stock positions
ctx.fund_positions()      # Fund positions
ctx.cashflow(start, end)  # Cash flow
ctx.margin_ratio("AAPL.US")  # Margin ratio
```

## Subscriptions

```python
ctx.set_on_quote(lambda s, q: print(s, q))
ctx.set_on_order(lambda o: print(o))

ctx.subscribe(
    symbols=["AAPL.US"],
    subtypes=[SubType.Quote, SubType.Depth, SubType.Trade],
    is_first_push=True,
)
```

**SubTypes:** `Quote`, `Depth`, `Trade`, `Brokers`, `Candle`, `QuoteRealtime`

## Rate Limits

| API | Limit |
|-----|-------|
| Quote | ≤10 calls/sec, ≤500 subscriptions |
| Trade | ≤30 calls/30sec, ≥0.02s gap |

## Error Codes

| Code | Meaning |
|------|---------|
| 301600 | Invalid request |
| 301606 | Rate limited |
| 301607 | Symbol limit |

## Useful Links

- Docs: https://open.longbridge.com/docs
- SDK API: https://longportapp.github.io/openapi
- GitHub: https://github.com/longportapp/openapi
- llms.txt: https://open.longbridge.com/llms.txt
