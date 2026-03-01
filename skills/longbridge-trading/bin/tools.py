#!/usr/bin/env python3
"""
Longbridge Trading Skill - Core Tools

Usage:
    python3 tools.py quote <symbol>
    python3 tools.py positions
    python3 tools.py balance
    python3 tools.py buy <symbol> <qty> [price]
    python3 tools.py sell <symbol> <qty> [price]
    python3 tools.py orders
    python3 tools.py cancel <order_id>
"""

import sys
import json
from longbridge.openapi import Config, TradeContext, QuoteContext, OrderType, OrderSide, TimeInForceType

# Load credentials
CREDENTIALS_FILE = "~/.openclaw/longbridge_tokens.json"

def load_credentials():
    import os
    path = os.path.expanduser(CREDENTIALS_FILE)
    with open(path) as f:
        return json.load(f)

def get_contexts():
    creds = load_credentials()
    config = Config(
        app_key=creds["app_key"],
        app_secret=creds["app_secret"],
        access_token=creds["access_token"]
    )
    return TradeContext(config=config), QuoteContext(config=config)

def cmd_quote(symbols):
    trade_ctx, quote_ctx = get_contexts()
    quotes = quote_ctx.quote(symbols)
    
    for q in quotes:
        print(f"{q.symbol}: ${q.last_done}")
        print(f"  Open: ${q.open} | High: ${q.high} | Low: ${q.low}")
        print(f"  Volume: {q.volume:,}")

def cmd_positions():
    trade_ctx, _ = get_contexts()
    positions = trade_ctx.stock_positions()
    
    for ch in positions.channels:
        print(f"\nAccount: {ch.account_channel}")
        for pos in ch.positions:
            print(f"  {pos.symbol}: {pos.quantity} shares")
            print(f"    Cost: ${pos.cost_price} | Value: ${pos.market_value}")

def cmd_balance():
    trade_ctx, _ = get_contexts()
    balance = trade_ctx.account_balance()[0]
    cash = balance.cash_infos[0].available_cash
    print(f"Available Cash: ${cash}")

def cmd_buy(symbol, quantity, price=None):
    trade_ctx, quote_ctx = get_contexts()
    
    if price is None:
        # Market order
        q = quote_ctx.quote([symbol])[0]
        price = float(q.last_done)
    
    order = trade_ctx.submit_order(
        symbol=symbol,
        order_type=OrderType.MO if price is None else OrderType.LO,
        side=OrderSide.Buy,
        submitted_quantity=int(quantity),
        submitted_price=float(price) if price else None
    )
    print(f"Order submitted: {order.order_id}")

def cmd_sell(symbol, quantity, price=None):
    trade_ctx, quote_ctx = get_contexts()
    
    if price is None:
        q = quote_ctx.quote([symbol])[0]
        price = float(q.last_done)
    
    order = trade_ctx.submit_order(
        symbol=symbol,
        order_type=OrderType.MO if price is None else OrderType.LO,
        side=OrderSide.Sell,
        submitted_quantity=int(quantity),
        submitted_price=float(price) if price else None
    )
    print(f"Order submitted: {order.order_id}")

def cmd_orders():
    trade_ctx, _ = get_contexts()
    orders = trade_ctx.today_orders()
    
    for order in orders:
        print(f"{order.symbol}: {order.status}")
        print(f"  {order.side} {order.quantity} @ ${order.price}")

def cmd_cancel(order_id):
    trade_ctx, _ = get_contexts()
    trade_ctx.cancel_order(order_id)
    print(f"Order {order_id} cancelled")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == "quote" and len(sys.argv) >= 3:
        cmd_quote(sys.argv[2:])
    elif cmd == "positions":
        cmd_positions()
    elif cmd == "balance":
        cmd_balance()
    elif cmd == "buy" and len(sys.argv) >= 4:
        price = float(sys.argv[4]) if len(sys.argv) > 4 else None
        cmd_buy(sys.argv[2], sys.argv[3], price)
    elif cmd == "sell" and len(sys.argv) >= 4:
        price = float(sys.argv[4]) if len(sys.argv) > 4 else None
        cmd_sell(sys.argv[2], sys.argv[3], price)
    elif cmd == "orders":
        cmd_orders()
    elif cmd == "cancel" and len(sys.argv) >= 3:
        cmd_cancel(sys.argv[2])
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
