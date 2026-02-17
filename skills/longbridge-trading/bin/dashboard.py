#!/usr/bin/env python3
"""
Longbridge Trading Skill - Portfolio Dashboard

Real-time portfolio monitoring and analysis
"""

import json
from longbridge.openapi import Config, TradeContext, QuoteContext

def load_credentials():
    with open("~/.openclaw/longbridge_tokens.json") as f:
        return json.load(f)

def main():
    creds = load_credentials()
    config = Config(app_key=creds["app_key"], access_token=creds["access_token"])
    trade_ctx = TradeContext(config=config)
    quote_ctx = QuoteContext(config=config)
    
    print("=" * 60)
    print("📊 Portfolio Dashboard")
    print("=" * 60)
    
    # Balance
    balance = trade_ctx.account_balance()[0]
    cash = float(balance.cash_infos[0].available_cash)
    print(f"\n💰 Cash: ${cash:,.2f}")
    
    # Positions
    positions = trade_ctx.stock_positions()
    for ch in positions.channels:
        print(f"\n📈 Account: {ch.account_channel}")
        for pos in ch.positions:
            q = quote_ctx.quote([pos.symbol])[0]
            current = float(q.last_done)
            cost = float(pos.cost_price)
            pnl = (current - cost) / cost * 100
            
            emoji = "🟢" if pnl >= 0 else "🔴"
            print(f"{emoji} {pos.symbol}: {pos.quantity} shares")
            print(f"   ${current:.2f} | Cost: ${cost:.2f} | P&L: {pnl:+.1f}%")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
