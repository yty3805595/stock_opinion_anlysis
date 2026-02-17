#!/usr/bin/env python3
"""
期权交易命令行工具
"""

import sys
import argparse
from datetime import datetime

# 添加路径
sys.path.insert(0, ".")

from scripts.options_trading import (
    OptionsTradingSystem,
    OptionsAnalyzer,
    OptionsPortfolioManager
)


def main():
    parser = argparse.ArgumentParser(description="期权交易工具")
    parser.add_argument("--analysis", action="store_true",
                       help="运行分析，生成信号")
    parser.add_argument("--buy", type=str, metavar="SYMBOL",
                       help="买入看跌期权")
    parser.add_argument("--sell", type=str, metavar="SYMBOL",
                       help="卖出/平仓期权")
    parser.add_argument("--strategy", type=str, default="hedge",
                       choices=["hedge", "bottom_fish", "speculate"],
                       help="策略类型")
    parser.add_argument("--strike", type=float,
                       help="行权价")
    parser.add_argument("--expiration", type=str,
                       help="到期日 (YYYY-MM-DD)")
    parser.add_argument("--quantity", type=int, default=1,
                       help="合约数量")
    parser.add_argument("--premium", type=float,
                       help="权利金")
    parser.add_argument("--portfolio", action="store_true",
                       help="查看持仓")
    parser.add_argument("--initial-cash", type=float, default=50000,
                       help="初始资金")
    
    args = parser.parse_args()
    
    # 创建系统
    system = OptionsTradingSystem({"initial_cash": args.initial_cash})
    
    if args.analysis:
        print("\n" + "="*70)
        print("📊 期权信号分析")
        print("="*70)
        
        # 测试数据
        test_data = {
            "QQQ": {"price": 580, "ma20": 600, "rsi": 25, "volatility": 0.35},
            "NVDA": {"price": 180, "ma20": 185, "rsi": 45, "volatility": 0.40},
            "TSLA": {"price": 400, "ma20": 420, "rsi": 30, "volatility": 0.50},
            "GOOGL": {"price": 170, "ma20": 175, "rsi": 40, "volatility": 0.30},
            "MSFT": {"price": 400, "ma20": 405, "rsi": 35, "volatility": 0.25},
        }
        
        signals = system.run_analysis(test_data)
        system.print_signals(signals)
        
        # 打印持仓
        system.portfolio.print_portfolio()
    
    elif args.buy:
        symbol = args.buy.upper()
        
        print(f"\n📈 买入 {symbol} 看跌期权")
        print("-"*50)
        
        # 获取参数
        if not args.strike:
            # 自动计算
            base_price = 400  # 假设基准价
            if args.strategy == "hedge":
                args.strike = base_price * 0.95
            elif args.strategy == "bottom_fish":
                args.strike = base_price * 0.90
            else:
                args.strike = base_price
            
            # 四舍五入到5的倍数
            args.strike = round(args.strike / 5) * 5
            print(f"   自动计算行权价: ${args.strike}")
        
        if not args.expiration:
            args.expiration = OptionsAnalyzer.calculate_expiration(args.strategy)
            print(f"   使用默认到期日: {args.expiration}")
        
        if not args.premium:
            # 估算
            time_to_expiry = 30
            args.premium = OptionsAnalyzer.estimate_premium(100, args.strike, time_to_expiry)
            print(f"   估算权利金: ${args.premium:.2f}")
        
        # 执行
        success, msg = system.portfolio.open_position(
            symbol=symbol,
            option_type="put",
            strike_price=args.strike,
            expiration=args.expiration,
            quantity=args.quantity,
            premium=args.premium
        )
        
        print(f"   {msg}")
        
        if success:
            system.portfolio.print_portfolio()
    
    elif args.sell:
        symbol = args.sell.upper()
        
        print(f"\n📉 平仓 {symbol} 相关期权")
        print("-"*50)
        
        # 查找持仓
        found = False
        positions_to_close = []
        for option_symbol, contract in list(system.portfolio.portfolio.positions.items()):
            if contract.symbol == symbol:
                positions_to_close.append(option_symbol)
        
        for option_symbol in positions_to_close:
            success, msg = system.portfolio.close_position(option_symbol)
            print(f"   {msg}")
            found = True
        
        if not found:
            print(f"   ❌ 未找到 {symbol} 相关持仓")
        
        if found:
            system.portfolio.print_portfolio()
    
    elif args.portfolio:
        system.portfolio.print_portfolio()
    
    else:
        print("""
🛠️ 期权交易工具

用法:
  # 运行分析，查看信号
  python options_trade.py --analysis
  
  # 买入看跌期权
  python options_trade.py --buy QQQ --strike 550 --quantity 2
  
  # 平仓
  python options_trade.py --sell QQQ
  
  # 查看持仓
  python options_trade.py --portfolio

参数:
  --buy SYMBOL      买入标的
  --strike PRICE    行权价
  --expiration DATE 到期日 (YYYY-MM-DD)
  --quantity NUM    合约数量
  --strategy TYPE   策略: hedge, bottom_fish, speculate
  --premium PRICE   权利金 (可选，自动估算)

示例:
  # 买入 QQQ 看跌期权对冲
  python options_trade.py --buy QQQ --strategy hedge
  
  # 买入 TSLA 抄底期权
  python options_trade.py --buy TSLA --strategy bottom_fish
  
  # 指定行权价和到期日
  python options_trade.py --buy NVDA --strike 170 --expiration 2026-04-15
""")


if __name__ == "__main__":
    main()
