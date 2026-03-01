#!/usr/bin/env python3
"""
快速交易记录工具

使用方法:
  python3 scripts/record_trade.py --buy MSTR 120.50 100 --strategy MSTR趋势 --stop 108 --take 132
  python3 scripts/record_trade.py --sell QQQ 610.00 68 --reason 获利了结
  python3 scripts/record_trade.py --status
  python3 scripts/record_trade.py --close MSTR 125.00
"""

import argparse
import sys
from datetime import datetime

# 导入交易记录器
sys.path.insert(0, '/Users/yintaoye/.openclaw/workspace/scripts')
from trade_monitor import TradeLogger

def format_trade_signal(strategy: str, symbol: str, direction: str, price: float, size: int, 
                        stop_loss: float = None, take_profit: float = None) -> str:
    """格式化交易信号"""
    
    signal = f"""
{'🟢' if direction == 'buy' else '🔴'} **{direction.upper()}信号**

**标的**: {symbol}
**价格**: ${price:.2f}
**数量**: {size} 股
**策略**: {strategy}
"""
    
    if stop_loss and take_profit:
        risk = abs(price - stop_loss)
        reward = abs(take_profit - price)
        rr_ratio = reward / risk if risk > 0 else 0
        
        signal += f"""
**止损**: ${stop_loss:.2f} ({risk/price*100:.1f}%)
**止盈**: ${take_profit:.2f} ({reward/price*100:.1f}%)
**盈亏比**: {rr_ratio:.2f}R
"""
    
    return signal

def main():
    parser = argparse.ArgumentParser(description='快速交易记录工具')
    
    # 买方命令
    parser.add_argument('--buy', nargs=3, metavar=('SYMBOL', 'PRICE', 'SIZE'),
                       help='记录买入: --buy MSTR 120.50 100')
    
    # 卖方命令
    parser.add_argument('--sell', nargs=3, metavar=('SYMBOL', 'PRICE', 'SIZE'),
                       help='记录卖出: --sell MSTR 125.00 100')
    
    # 平仓命令
    parser.add_argument('--close', nargs=2, metavar=('SYMBOL', 'PRICE'),
                       help='平仓: --close MSTR 125.00')
    
    # 查看状态
    parser.add_argument('--status', action='store_true',
                       help='查看当前状态')
    
    # 参数
    parser.add_argument('--strategy', '-s', default='manual',
                       help='策略名称')
    parser.add_argument('--stop', '-st', type=float,
                       help='止损价')
    parser.add_argument('--take', '-tp', type=float,
                       help='止盈价')
    parser.add_argument('--reason', '-r', default='手动平仓',
                       help='平仓原因')
    
    args = parser.parse_args()
    
    logger = TradeLogger("/Users/yintaoye/.openclaw/workspace/trades.json")
    
    # 记录买入
    if args.buy:
        symbol, price, size = args.buy
        price = float(price)
        size = int(size)
        
        trade = logger.add_trade(
            symbol=symbol,
            direction='buy',
            entry_price=price,
            size=size,
            strategy=args.strategy,
            stop_loss=args.stop,
            take_profit=args.take,
            notes='用户手动下单'
        )
        
        print(format_trade_signal(args.strategy, symbol, 'buy', price, size, args.stop, args.take))
        print(f"\n✅ 已记录: {symbol} @ ${price} x {size}")
        print(f"💾 保存到: /Users/yintaoye/.openclaw/workspace/trades.json")
    
    # 记录卖出
    elif args.sell:
        symbol, price, size = args.sell
        price = float(price)
        size = int(size)
        
        trade = logger.add_trade(
            symbol=symbol,
            direction='sell',
            entry_price=price,
            size=size,
            strategy=args.strategy,
            stop_loss=args.stop,
            take_profit=args.take,
            notes='用户手动下单'
        )
        
        print(format_trade_signal(args.strategy, symbol, 'sell', price, size, args.stop, args.take))
        print(f"\n✅ 已记录: {symbol} @ ${price} x {size}")
        print(f"💾 保存到: /Users/yintaoye/.openclaw/workspace/trades.json")
    
    # 平仓
    elif args.close:
        symbol, price = args.close
        price = float(price)
        
        trade = logger.close_trade(symbol, price, args.reason)
        
        if trade:
            print(f"\n✅ 已平仓: {symbol} @ ${price}")
            print(f"💰 盈亏: ${trade['pnl']:.2f} ({trade['pnl_percent']:.2f}%)")
            print(f"📝 原因: {args.reason}")
        else:
            print(f"\n❌ 未找到 {symbol} 的未平仓仓位")
    
    # 查看状态
    elif args.status:
        logger.print_status()
    
    else:
        parser.print_help()
        print("\n" + "=" * 80)
        print("📖 使用示例")
        print("=" * 80)
        print("""
# 记录买入
python3 scripts/record_trade.py --buy MSTR 120.50 100 -s "MSTR趋势" -st 108 -tp 132

# 记录卖出
python3 scripts/record_trade.py --sell MSTR 125.00 100 -r "获利了结"

# 查看状态
python3 scripts/record_trade.py --status

# 平仓
python3 scripts/record_trade.py --close MSTR 125.00 -r "获利了结"
        """)


if __name__ == "__main__":
    main()
