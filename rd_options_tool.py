#!/usr/bin/env python3
"""
RD-Agent 期权交易命令行工具
"""

import sys
import argparse

sys.path.insert(0, ".")

from scripts.rd_options_trading import (
    RDOptionsTrader,
    RDResearchAgent
)


def main():
    parser = argparse.ArgumentParser(description="RD-Agent 期权交易工具")
    parser.add_argument("--analyze", action="store_true",
                       help="运行 RD-Agent 分析")
    parser.add_argument("--execute", type=str, metavar="SYMBOL",
                       help="执行信号")
    parser.add_argument("--close", type=str, metavar="SYMBOL",
                       help="平仓")
    parser.add_argument("--portfolio", action="store_true",
                       help="查看持仓")
    parser.add_argument("--cash", type=float, default=50000,
                       help="初始资金")
    parser.add_argument("--data", type=str,
                       help="JSON 格式的市场数据")
    
    args = parser.parse_args()
    
    # 创建交易系统
    trader = RDOptionsTrader(args.cash)
    
    if args.analyze:
        # 市场数据
        if args.data:
            import json
            market_data = json.loads(args.data)
        else:
            # 默认测试数据
            market_data = {
                "QQQ": {"price": 580, "ma20": 600, "rsi": 25, "volatility": 0.35},
                "NVDA": {"price": 180, "ma20": 185, "rsi": 45, "volatility": 0.40},
                "TSLA": {"price": 400, "ma20": 420, "rsi": 28, "volatility": 0.50},
                "GOOGL": {"price": 170, "ma20": 175, "rsi": 40, "volatility": 0.30},
                "MSFT": {"price": 400, "ma20": 405, "rsi": 35, "volatility": 0.25},
                "AAPL": {"price": 185, "ma20": 190, "rsi": 42, "volatility": 0.25},
                "AMD": {"price": 180, "ma20": 175, "rsi": 48, "volatility": 0.35},
                "META": {"price": 500, "ma20": 510, "rsi": 40, "volatility": 0.35},
                "AMZN": {"price": 175, "ma20": 180, "rsi": 38, "volatility": 0.30},
                "PLTR": {"price": 70, "ma20": 75, "rsi": 25, "volatility": 0.55},
            }
        
        # 分析
        strategies = trader.analyze_all(market_data)
        trader.print_report(strategies)
    
    elif args.execute:
        # 执行单个信号
        symbol = args.execute.upper()
        
        print(f"\n📝 执行 {symbol} 信号...")
        
        # 获取最新数据
        market_data = {
            "QQQ": {"price": 580, "ma20": 600, "rsi": 25, "volatility": 0.35},
            "NVDA": {"price": 180, "ma20": 185, "rsi": 45, "volatility": 0.40},
            "TSLA": {"price": 400, "ma20": 420, "rsi": 28, "volatility": 0.50},
            "GOOGL": {"price": 170, "ma20": 175, "rsi": 40, "volatility": 0.30},
            "MSFT": {"price": 400, "ma20": 405, "rsi": 35, "volatility": 0.25},
            "AAPL": {"price": 185, "ma20": 190, "rsi": 42, "volatility": 0.25},
            "AMD": {"price": 180, "ma20": 175, "rsi": 48, "volatility": 0.35},
            "META": {"price": 500, "ma20": 510, "rsi": 40, "volatility": 0.35},
            "AMZN": {"price": 175, "ma20": 180, "rsi": 38, "volatility": 0.30},
            "PLTR": {"price": 70, "ma20": 75, "rsi": 25, "volatility": 0.55},
        }
        
        if symbol not in market_data:
            print(f"❌ 未找到 {symbol} 数据")
            return
        
        # 生成策略
        data = market_data[symbol]
        strategy = trader.analyze_symbol(
            symbol,
            data["price"],
            data["ma20"],
            data["rsi"],
            data["volatility"]
        )
        
        print(f"\n📊 {symbol} RD-Agent 分析结果:")
        print(f"   策略: {strategy.strategy_type.upper()}")
        print(f"   RD Score: {strategy.rd_score:.2f}")
        print(f"   置信度: {strategy.confidence:.0%}")
        print(f"   期权: Put @ ${strategy.strike_price:.0f}")
        print(f"   仓位: {strategy.position_size*100:.2f}%")
        print(f"   理由: {strategy.reasoning}")
        
        # 确认执行
        if strategy.rd_score > 0.4:
            print(f"\n✅ 执行交易? (y/n)")
            confirm = input("   > ").strip().lower()
            
            if confirm == "y":
                success, msg = trader.execute_strategy(strategy)
                print(f"   {msg}")
        else:
            print(f"\n⚠️ RD Score ({strategy.rd_score:.2f}) 低于阈值，不建议执行")
        
        trader.print_report([])
    
    elif args.close:
        symbol = args.close.upper()
        
        # 查找并平仓
        positions_to_close = []
        for underlying, pos in list(trader.positions.items()):
            if pos.symbol == symbol:
                positions_to_close.append(underlying)
        
        if positions_to_close:
            print(f"\n📉 平仓 {symbol} ({len(positions_to_close)} 个期权)")
            for underlying in positions_to_close:
                success, msg = trader.close_position(underlying)
                print(f"   {msg}")
        else:
            print(f"❌ 未找到 {symbol} 相关持仓")
        
        trader.print_report([])
    
    elif args.portfolio:
        trader.print_report([])
    
    else:
        print("""
🛠️ RD-Agent 期权交易工具

用法:
  # 分析所有标的
  python rd_options_tool.py --analyze
  
  # 执行特定信号
  python rd_options_tool.py --execute QQQ
  
  # 平仓
  python rd_options_tool.py --close QQQ
  
  # 查看持仓
  python rd_options_tool.py --portfolio

参数:
  --analyze    运行 RD-Agent 分析
  --execute    执行特定标的的信号
  --close      平仓指定标的
  --portfolio  查看当前持仓
  --cash       初始资金 (默认 50000)
  --data       JSON 格式市场数据

示例:
  # 分析并查看信号
  python rd_options_tool.py --analyze
  
  # 执行 QQQ 信号
  python rd_options_tool.py --execute QQQ
  
  # 带自定义资金
  python rd_options_tool.py --analyze --cash 100000
""")


if __name__ == "__main__":
    main()
