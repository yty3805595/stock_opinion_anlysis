#!/usr/bin/env python3
"""
Longbridge 实时持仓监控脚本
从 Longbridge API 获取实时数据
"""

import os
import sys
import json
import logging
from datetime import datetime

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.longbridge_data_fetcher import LongbridgeDataFetcher

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def get_portfolio():
    """获取当前持仓"""
    return {
        'QQQ': {'shares': 68, 'avg_cost': 600.64},
        'NVDA': {'shares': 54, 'avg_cost': 186.94},
        'TSLA': {'shares': 10, 'avg_cost': 416.67},
        'GOOGL': {'shares': 33, 'avg_cost': 309.00},
        'MSFT': {'shares': 25, 'avg_cost': 401.78},
    }


def monitor_portfolio():
    """监控持仓并生成报告"""
    portfolio = get_portfolio()
    fetcher = LongbridgeDataFetcher()
    
    total_value = 0
    total_cost = 0
    positions = []
    
    for symbol, info in portfolio.items():
        try:
            # 从 Longbridge 获取实时数据
            df = fetcher.get_candlesticks(f'{symbol}.US', 'day', 1)
            
            if len(df) == 0:
                logger.warning(f"无法获取 {symbol} 数据")
                continue
            
            current_price = float(df['close'].iloc[-1])
            shares = info['shares']
            avg_cost = info['avg_cost']
            
            market_value = shares * current_price
            cost_basis = shares * avg_cost
            pnl = market_value - cost_basis
            pnl_pct = (current_price - avg_cost) / avg_cost * 100
            
            total_value += market_value
            total_cost += cost_basis
            
            positions.append({
                'symbol': symbol,
                'shares': shares,
                'avg_cost': avg_cost,
                'current_price': current_price,
                'market_value': market_value,
                'pnl': pnl,
                'pnl_pct': pnl_pct
            })
            
        except Exception as e:
            logger.error(f"获取 {symbol} 数据失败: {e}")
    
    # 按盈亏排序
    positions.sort(key=lambda x: x['pnl'], reverse=True)
    
    return positions, total_value, total_cost


def generate_report():
    """生成监控报告"""
    positions, total_value, total_cost = monitor_portfolio()
    
    if not positions:
        return "❌ 无法获取持仓数据"
    
    total_pnl = total_value - total_cost
    total_pnl_pct = total_pnl / total_cost * 100 if total_cost > 0 else 0
    
    # 生成报告
    report = f"""
## 📊 实时持仓监控 ({datetime.now().strftime('%Y-%m-%d %H:%M')})

### 实时行情 (Longbridge API)

| 股票 | 股数 | 成本价 | 实时价 | 浮动 | 盈亏 |
|------|------|--------|--------|------|------|
"""
    
    for pos in positions:
        symbol = pos['symbol']
        shares = pos['shares']
        avg_cost = pos['avg_cost']
        current_price = pos['current_price']
        pnl = pos['pnl']
        pnl_pct = pos['pnl_pct']
        
        emoji = '🟢' if pnl > 0 else '🔴'
        report += f"| {symbol} | {shares} | ${avg_cost:.2f} | ${current_price:.2f} | {emoji} {pnl_pct:+.2f}% | ${pnl:+,.0f} |\n"
    
    # 汇总
    report += f"""
### 汇总

- 💰 **总市值**: ${total_value:,.0f}
- 📈 **总盈亏**: ${total_pnl:+,.0f} ({total_pnl_pct:+.2f}%)
"""
    
    # 风控检查
    max_loss = min(p['pnl_pct'] for p in positions)
    if max_loss < -5:
        report += f"\n⚠️ **风控警报**: {max_loss:.2f}% 触发止损线！"
    else:
        report += f"\n✅ **风控状态**: 正常 (最大亏损 {max_loss:.2f}%)"
    
    # 保存到文件
    report_file = '/tmp/live_portfolio_monitor.md'
    with open(report_file, 'w') as f:
        f.write(report)
    
    return report, total_pnl_pct, max_loss


if __name__ == '__main__':
    report, total_pnl_pct, max_loss = generate_report()
    print(report)
    
    # 发送告警
    if max_loss < -5:
        logger.warning(f"⚠️ 风控警报: 最大亏损 {max_loss:.2f}%")
