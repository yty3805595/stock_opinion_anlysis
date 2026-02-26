#!/usr/bin/env python3
"""
Longbridge 持仓同步器
将持仓数据同步到 JSON 文件，供其他脚本使用
"""
import json
import os
from datetime import datetime
from decimal import Decimal

CREDENTIALS_PATH = "/Users/yintaoye/.openclaw/workspace/skills/longbridge-trading/config/credentials.json"
OUTPUT_DIR = "/Users/yintaoye/.openclaw/workspace/data"

def load_credentials():
    with open(CREDENTIALS_PATH) as f:
        return json.load(f)["credentials"]

def to_float(val):
    """Convert any numeric type to float"""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (int, float)):
        return float(val)
    return val

def get_positions():
    from longbridge.openapi import Config, TradeContext, QuoteContext
    
    creds = load_credentials()
    config = Config(
        app_key=creds["app_key"], 
        app_secret=creds["app_secret"],
        access_token=creds["access_token"]
    )
    
    trade_ctx = TradeContext(config)
    quote_ctx = QuoteContext(config)
    
    # Get positions
    positions_resp = trade_ctx.stock_positions()
    
    # Get quotes for all stock positions
    stock_symbols = []
    all_positions = []
    
    for channel in positions_resp.channels:
        if 'lb_papertrading' in channel.account_channel:
            for p in channel.positions:
                all_positions.append({
                    "symbol": p.symbol,
                    "name": p.symbol_name,
                    "quantity": to_float(p.quantity),
                    "cost_price": to_float(p.cost_price),
                    "market": str(p.market),
                    "type": "option" if "NVDA260" in p.symbol else "stock"
                })
                if "NVDA260" not in p.symbol:
                    stock_symbols.append(p.symbol)
    
    # Get current prices
    quotes = quote_ctx.quote(stock_symbols)
    quote_map = {q.symbol: to_float(q.last_done) for q in quotes}
    
    # Add current price to positions
    for pos in all_positions:
        if pos["symbol"] in quote_map:
            pos["current_price"] = quote_map[pos["symbol"]]
            pos["market_value"] = pos["quantity"] * quote_map[pos["symbol"]]
            pos["unrealized_pnl"] = pos["market_value"] - (pos["quantity"] * pos["cost_price"])
            pos["unrealized_pnl_pct"] = (pos["unrealized_pnl"] / (pos["quantity"] * pos["cost_price"]) * 100) if pos["cost_price"] else 0
        else:
            pos["current_price"] = None
            pos["market_value"] = None
            pos["unrealized_pnl"] = None
            pos["unrealized_pnl_pct"] = None
    
    # Get account balance
    balance_resp = trade_ctx.account_balance()
    
    account = {
        "total_assets": to_float(balance_resp[0].net_assets),
        "currency": balance_resp[0].currency,
        "total_cash": to_float(balance_resp[0].total_cash),
    }
    
    # Cash by currency
    cash_by_currency = {}
    for cash_info in balance_resp[0].cash_infos:
        cash_by_currency[cash_info.currency] = {
            "available": to_float(cash_info.available_cash),
            "frozen": to_float(cash_info.frozen_cash),
            "settling": to_float(cash_info.settling_cash)
        }
    account["cash_by_currency"] = cash_by_currency
    
    return {
        "timestamp": datetime.now().isoformat(),
        "account": account,
        "positions": all_positions
    }

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    data = get_positions()
    
    # Save full data
    with open(f"{OUTPUT_DIR}/portfolio.json", "w") as f:
        json.dump(data, f, indent=2)
    
    # Save stock-only for compatibility
    stock_positions = [p for p in data["positions"] if p["type"] == "stock"]
    with open(f"{OUTPUT_DIR}/stock_portfolio.json", "w") as f:
        json.dump({
            "timestamp": data["timestamp"],
            "positions": stock_positions,
            "account": data["account"]
        }, f, indent=2)
    
    # Save options-only (legacy format for rd_options_tool.py compatibility)
    option_positions = [p for p in data["positions"] if p["type"] == "option"]
    # Convert to legacy dict format
    options_legacy = {}
    for opt in option_positions:
        options_legacy[opt["symbol"]] = {
            "symbol": opt["symbol"],
            "quantity": opt["quantity"],
            "cost": opt["cost_price"] * abs(opt["quantity"]),
            "cost_price": opt["cost_price"],
            "strike_price": 195 if "NVDA260" in opt["symbol"] else 0,
            "expiry": "2026-03-06" if "NVDA260" in opt["symbol"] else "",
            "market_value": opt.get("market_value"),
            "unrealized_pnl": opt.get("unrealized_pnl"),
        }
    
    with open(f"{OUTPUT_DIR}/options_portfolio.json", "w") as f:
        json.dump({
            "timestamp": data["timestamp"],
            "positions": options_legacy,
            "cash": data["account"]["cash_by_currency"].get("USD", {}).get("available", 0),
            "account": data["account"]
        }, f, indent=2)
    
    print(f"✅ 持仓已同步")
    print(f"   股票: {len(stock_positions)} 只")
    print(f"   期权: {len(option_positions)} 只")
    print(f"   总资产: ${data['account']['total_assets']:,.2f}")

if __name__ == "__main__":
    main()
