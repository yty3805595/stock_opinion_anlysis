#!/usr/bin/env python3
"""
RD-Agent 期权交易工具 v2.0

用法:
    python3 rd_options_tool.py --analyze    # 分析期权信号
    python3 rd_options_tool.py --execute    # 执行最佳期权
    python3 rd_options_tool.py --monitor    # 监控期权持仓
    python3 rd_options_tool.py --fetch      # 获取实时价格
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, "scripts")
from rd_options_trading import (
    RDOptionsTrader,
    calculate_realistic_option,
    get_longbridge_option_code
)

# 路径配置
PORTFOLIO_PATH = "data/options_portfolio.json"
MARKET_DATA_PATH = "/tmp/market_data.json"


def analyze():
    """分析期权信号"""
    print("="*70)
    print("🤖 RD-Agent 期权信号分析")
    print("="*70)
    
    # 加载市场数据
    if Path(MARKET_DATA_PATH).exists():
        with open(MARKET_DATA_PATH) as f:
            market_data = json.load(f)
    else:
        # 使用默认数据
        market_data = {
            'NVDA': {'price': 184.97, 'ma20': 183.50, 'rsi': 42, 'volatility': 0.35},
            'TSLA': {'price': 410.63, 'ma20': 415.00, 'rsi': 40, 'volatility': 0.42},
            'QQQ': {'price': 601.30, 'ma20': 605.00, 'rsi': 48, 'volatility': 0.32},
            'MSFT': {'price': 396.86, 'ma20': 400.00, 'rsi': 47, 'volatility': 0.28},
            'GOOGL': {'price': 302.02, 'ma20': 308.00, 'rsi': 44, 'volatility': 0.30},
        }
    
    trader = RDOptionsTrader(50000)
    strategies = trader.analyze_all(market_data)
    strategies.sort(key=lambda x: -x.rd_score)
    
    print("\n📊 期权信号排名")
    print("-"*70)
    
    for i, s in enumerate(strategies[:5], 1):
        symbol = s.symbol
        data = market_data[symbol]
        price = data['price']
        
        option = calculate_realistic_option(symbol, s.strategy_type, price)
        
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        
        print(f"\n{emoji} #{i} {symbol} - {s.strategy_type.upper()}")
        print(f"   RD Score: {s.rd_score:.3f} | 置信度: {s.confidence:.0%}")
        print(f"   现价: ${price:.2f} | 行权价: ${option['strike']:.0f}")
        print(f"   🏷️ 期权: {option['option_code']}")
        print(f"   💰 权利金: ${option['premium']:.2f} × 100 = ${option['total_cost']:.2f}")
        print(f"   📅 到期: {option['expiration']} ({option['days']}天)")
        print(f"   理由: {s.reasoning}")
        
        if 'intrinsic_value' in option:
            print(f"   📊 内在价值: ${option['intrinsic_value']} | 时间价值: ${option['time_value']}")
    
    print("\n" + "="*70)
    print("💡 建议")
    print("="*70)
    
    if strategies:
        best = strategies[0]
        option = calculate_realistic_option(best.symbol, best.strategy_type, market_data[best.symbol]['price'])
        print(f"\n首选: {best.symbol} - {best.strategy_type.upper()}")
        print(f"  期权: {option['option_code']}")
        print(f"  成本: ${option['total_cost']:.2f}")
        print(f"  执行: python3 rd_options_tool.py --execute {best.symbol}")


def execute(symbol=None):
    """执行期权交易"""
    print("="*70)
    print("🛡️ RD-Agent 期权执行")
    print("="*70)
    
    # 加载市场数据
    if Path(MARKET_DATA_PATH).exists():
        with open(MARKET_DATA_PATH) as f:
            market_data = json.load(f)
    else:
        market_data = {
            'NVDA': {'price': 184.97, 'ma20': 183.50, 'rsi': 42, 'volatility': 0.35},
        }
    
    trader = RDOptionsTrader(50000)
    strategies = trader.analyze_all(market_data)
    strategies.sort(key=lambda x: -x.rd_score)
    
    if not strategies:
        print("❌ 无可用策略")
        return
    
    # 选择策略
    if symbol:
        target = next((s for s in strategies if s.symbol == symbol), strategies[0])
    else:
        target = strategies[0]
    
    price = market_data[target.symbol]['price']
    
    print(f"\n📝 执行: {target.symbol} - {target.strategy_type.upper()}")
    print(f"   RD Score: {target.rd_score:.3f}")
    print(f"   置信度: {target.confidence:.0%}")
    print(f"   理由: {target.reasoning}")
    
    # 计算期权参数
    option = calculate_realistic_option(target.symbol, target.strategy_type, price)
    
    print(f"\n📊 期权详情:")
    print(f"   代码: {option['option_code']}")
    print(f"   行权价: ${option['strike']:.0f}")
    print(f"   到期日: {option['expiration']}")
    print(f"   权利金: ${option['premium']:.2f}")
    print(f"   总成本: ${option['total_cost']:.2f}")
    
    # 注意：实际下单需要 Longbridge App
    print(f"\n⚠️ 请在 Longbridge App 中手动下单:")
    print(f"   标的: {option['option_code']}")
    print(f"   类型: Put (看跌)")
    print(f"   价格: ${option['premium']}")
    print(f"   数量: 1 张")


def monitor():
    """监控期权持仓"""
    print("="*70)
    print("📊 期权持仓监控")
    print("="*70)
    
    portfolio_path = Path(PORTFOLIO_PATH)
    
    if not portfolio_path.exists():
        print("\n📭 无期权持仓")
        return
    
    with open(portfolio_path) as f:
        data = json.load(f)
    
    positions = data.get('positions', {})
    
    if not positions:
        print("\n📭 无期权持仓")
        return
    
    print(f"\n💰 现金: ${data.get('cash', 0):,.2f}")
    print(f"📈 持仓数: {len(positions)}")
    
    total_value = 0
    total_pnl = 0
    
    for code, pos in positions.items():
        value = pos.get('market_value', pos.get('cost', 0))
        pnl = pos.get('unrealized_pnl', 0)
        total_value += value
        total_pnl += pnl
        
        emoji = "🟢" if pnl >= 0 else "🔴"
        
        print(f"\n{emoji} {code}")
        print(f"   标的: {pos.get('symbol', 'N/A')}")
        print(f"   行权价: ${pos.get('strike_price', 0)}")
        print(f"   到期: {pos.get('expiration', 'N/A')}")
        print(f"   成本: ${pos.get('premium', 0):.2f}")
        print(f"   盈亏: ${pnl:+.2f}")
    
    print(f"\n💵 总价值: ${total_value:,.2f}")
    print(f"📈 总盈亏: ${total_pnl:+.2f}")
    
    print("\n" + "="*70)


def main():
    """CLI 入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RD-Agent 期权交易工具 v2.0")
    parser.add_argument('--analyze', action='store_true', help='分析期权信号')
    parser.add_argument('--execute', nargs='?', const='NVDA', help='执行期权交易')
    parser.add_argument('--monitor', action='store_true', help='监控期权持仓')
    parser.add_argument('--fetch', nargs='?', const='NVDA', help='获取实时期权价格')
    
    args = parser.parse_args()
    
    if args.analyze:
        analyze()
    elif args.execute is not None:
        execute(args.execute)
    elif args.monitor:
        monitor()
    elif args.fetch is not None:
        from rd_options_trading import fetch_real_option_price
        data = {'price': 184.97, 'volatility': 0.35}
        result = fetch_real_option_price(args.fetch, 'hedge', data['price'], data['volatility'])
        print(f"期权价格: {result}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
