#!/usr/bin/env python3
"""
RD-Agent 每日交易系统
用法: python3 scripts/rd_agent_daily.py
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.longbridge_data_fetcher import LongbridgeDataFetcher
from longbridge.openapi import Config, TradeContext as Trade


def main():
    # 加载凭证
    workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    creds_path = os.path.join(workspace, 'skills/longbridge-trading/config/credentials.json')
    with open(creds_path) as f:
        creds = json.load(f)['credentials']

    fetcher = LongbridgeDataFetcher()
    trade = Trade(Config(
        app_key=creds['app_key'],
        app_secret=creds['app_secret'],
        access_token=creds['access_token']
    ))

    stocks = ['QQQ', 'NVDA', 'TSLA', 'GOOGL', 'MSFT']

    print("="*60)
    print("🎯 RD-Agent 每日交易报告")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*60)

    # 获取持仓
    positions = trade.stock_positions([f'{s}.US' for s in stocks])
    pos_map = {}
    for ch in positions.channels:
        for p in ch.positions:
            sym = p.symbol.replace('.US', '')
            pos_map[sym] = {'qty': int(p.quantity), 'cost': float(p.cost_price)}

    # 获取价格
    prices = {}
    for sym in stocks:
        df = fetcher.get_candlesticks(f'{sym}.US', 'day', 1)
        if len(df) > 0:
            prices[sym] = float(df['close'].iloc[-1])

    # 持仓
    print("\n📊 当前持仓:")
    total = 0
    for sym, pos in pos_map.items():
        price = prices.get(sym, 0)
        value = pos['qty'] * price
        total += value
        pnl = (price / pos['cost'] - 1) * 100 if pos['cost'] > 0 else 0
        print(f"  {sym}: {pos['qty']}股 @ ${price:.2f} ({pnl:+.1f}%)")

    print(f"\n💰 总市值: ${total:.2f}")

    # 因子分析
    print("\n🔬 因子分析:")
    for sym in stocks:
        df = fetcher.get_candlesticks(f'{sym}.US', 'day', 150)
        if len(df) < 50:
            continue
        
        close = df['close'].astype(float)
        ma60 = close.iloc[-30:].mean() / close.iloc[-90:-30].mean() - 1
        ma120 = close.iloc[-30:].mean() / close.iloc[-150:-30].mean() - 1
        
        direction = "long" if ma60 > 0 else "short"
        emoji = "🟢" if direction == "long" else "🔴"
        print(f"  {emoji} {sym}: {direction} (ma60={ma60*100:+.1f}%)")

    print("\n" + "="*60)
    print("✅ 每日分析完成")
    print("="*60)

    # 保存报告
    result = {
        'timestamp': datetime.now().isoformat(),
        'positions': pos_map,
        'prices': prices
    }
    with open('/tmp/rdagent_daily_report.json', 'w') as f:
        json.dump(result, f, indent=2)


if __name__ == '__main__':
    main()
