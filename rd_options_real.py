#!/usr/bin/env python3
"""
RD-Agent 期权执行工具 - 真实参数版
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, ".")

from scripts.rd_options_trading import (
    RDOptionsTrader,
    calculate_realistic_option
)

# 读取数据
with open('/tmp/market_data.json') as f:
    market_data = json.load(f)

# 用户真实持仓
with open('data/portfolio.json') as f:
    portfolio_data = json.load(f)

positions = {}
for symbol, pos in portfolio_data['positions'].items():
    positions[symbol] = {
        'quantity': pos['quantity'],
        'avg_price': pos['avg_price'],
        'market_value': pos['quantity'] * pos['current_price']
    }

print("="*70)
print("📊 RD-AGENT 期权分析 (真实参数)")
print("="*70)

trader = RDOptionsTrader(50000)
strategies = trader.analyze_all(market_data)
strategies.sort(key=lambda x: -x.rd_score)

# 只分析用户持有的股票
print("\n💼 你的持仓分析")
print("-"*70)
for symbol, pos in positions.items():
    if symbol in market_data:
        data = market_data[symbol]
        print(f"  {symbol}: {pos['quantity']:.1f}股 @ ${pos['avg_price']:.0f} = ${pos['market_value']:,.0f}")

# 分析并显示真实期权参数
print(f"\n📈 期权信号")
print("-"*70)

for s in strategies:
    symbol = s.symbol
    if symbol not in positions:
        continue
    
    data = market_data[symbol]
    price = data['price']
    
    # 真实期权参数
    option = calculate_realistic_option(symbol, s.strategy_type, price)
    
    print(f"\n{symbol} ({s.strategy_type.upper()})")
    print(f"  持仓: {positions[symbol]['market_value']:,.0f}")
    print(f"  现价: ${price:.2f}")
    print(f"  ─────────────────────────────────────────────")
    print(f"  期权代码: {option['option_code']}")
    print(f"  行权价: ${option['strike']:.0f}")
    print(f"  到期日: {option['expiration']}")
    print(f"  权利金: ${option['premium']:.2f}")
    print(f"  成本: ${option['total_cost']:.2f}")
    print(f"  ─────────────────────────────────────────────")
    print(f"  RD Score: {s.rd_score:.2f} | 置信度: {s.confidence:.0%}")
    print(f"  理由: {s.reasoning}")

print("\n" + "="*70)
print("💡 建议期权")
print("="*70)

# TOP 推荐
for s in strategies[:3]:
    symbol = s.symbol
    if symbol not in positions:
        continue
    
    data = market_data[symbol]
    option = calculate_realistic_option(symbol, s.strategy_type, data['price'])
    
    print(f"""
{symbol} - {s.strategy_type.upper()}

  代码: {option['option_code']}
  行权价: ${option['strike']:.0f} | 到期: {option['expiration']}
  权利金: ${option['premium']:.2f} | 总成本: ${option['total_cost']:.2f}
  RD Score: {s.rd_score:.2f} | 置信度: {s.confidence:.0%}
""")

print("="*70)
print("📝 执行命令")
print("="*70)
print("""
# 查看真实期权参数
python rd_options_tool.py --analyze

# 执行 (需要先删除旧持仓)
# rm data/options_portfolio.json
# python rd_options_tool.py --execute NVDA
""")
