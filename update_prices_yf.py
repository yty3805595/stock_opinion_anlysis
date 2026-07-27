#!/usr/bin/python3
import json
import yfinance as yf
from datetime import datetime

# Load portfolio
with open("/Users/yintaoye/.openclaw/workspace/data/portfolio.json") as f:
    portfolio = json.load(f)

print("📈 更新持仓价格 (yfinance)...")
for pos in portfolio["positions"]:
    symbol = pos["symbol"]
    yf_symbol = symbol.replace(".US", "")
    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="2d")
        if not hist.empty:
            current = float(hist["Close"].iloc[-1])
            pos["current_price"] = current
            pos["unrealized_pnl"] = (current - pos["cost_price"]) * pos["quantity"]
            pos["unrealized_pnl_pct"] = (current / pos["cost_price"] - 1) * 100
            print(f"  {symbol}: ${current:.2f} ({pos['unrealized_pnl_pct']:+.2f}%)")
        else:
            print(f"  {symbol}: 无数据")
    except Exception as e:
        print(f"  {symbol}: 失败 {e}")

portfolio["last_update"] = datetime.now().isoformat()

with open("/Users/yintaoye/.openclaw/workspace/data/portfolio.json", "w") as f:
    json.dump(portfolio, f, indent=2)

print(f"\n💾 已保存: {portfolio['last_update']}")
