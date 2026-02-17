#!/usr/bin/env python3
"""
持仓监控定时任务
每小时检查持仓状态和止盈止损
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.portfolio_monitor_v2 import PortfolioManager


def main():
    """运行监控"""
    print("="*70)
    print("📊 定时持仓监控")
    print("="*70)
    
    manager = PortfolioManager()
    portfolios = manager.load_portfolios()
    
    # 检查警报
    stock_alerts = manager.check_stock_alerts(portfolios)
    option_alerts = manager.check_options_alerts(portfolios)
    
    if stock_alerts or option_alerts:
        print("\n⚠️ 发现警报:")
        for alert in stock_alerts + option_alerts:
            print(f"  {alert}")
    else:
        print("\n✅ 无警报")
    
    # 打印简要状态
    print("\n📊 持仓状态:")
    
    # 股票
    print("\n💼 股票:")
    for symbol, pos in portfolios.get("stocks", {}).items():
        pnl_pct = pos.get("pnl_pct", 0)
        emoji = "🟢" if pnl_pct >= 0 else "🔴"
        print(f"  {symbol}: {emoji} {pnl_pct:+.1f}%")
    
    # 期权
    print("\n📈 期权:")
    for code, pos in portfolios.get("options", {}).items():
        return_pct = pos.get("return_pct", 0)
        emoji = "🟢" if return_pct >= 0 else "🔴"
        print(f"  {code}: {emoji} {return_pct:+.1f}%")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
