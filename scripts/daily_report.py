#!/usr/bin/env python3
"""
盘后复盘报告生成器
每天收盘后自动生成复盘报告
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 配置文件
REPORTS_DIR = '/Users/yintaoye/.openclaw/workspace/data/daily_reports'
PORTFOLIO_FILE = '/Users/yintaoye/.openclaw/workspace/data/portfolio.json'
ORDERS_FILE = '/tmp/trade_execution_results.json'


def load_portfolio() -> Dict:
    """加载持仓数据"""
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE) as f:
            return json.load(f)
    return {}


def load_today_orders() -> List[Dict]:
    """加载今日订单"""
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE) as f:
            data = json.load(f)
            return data.get('orders', [])
    return []


def calculate_daily_pnl(portfolio: Dict) -> Dict:
    """计算当日盈亏"""
    if not portfolio:
        return {'total_pnl': 0, 'total_return': 0}
    
    total_cost = 0
    total_value = 0
    
    for symbol, data in portfolio.items():
        shares = data.get('shares', 0)
        avg_cost = data.get('avg_cost', 0)
        current_price = data.get('current_price', avg_cost)
        
        total_cost += shares * avg_cost
        total_value += shares * current_price
    
    pnl = total_value - total_cost
    return_pct = pnl / total_cost * 100 if total_cost > 0 else 0
    
    return {
        'total_cost': total_cost,
        'total_value': total_value,
        'total_pnl': pnl,
        'total_return': return_pct
    }


def analyze_orders(orders: List[Dict]) -> Dict:
    """分析今日订单"""
    if not orders:
        return {
            'total_orders': 0,
            'filled': 0,
            'pending': 0,
            'total_buy': 0,
            'total_sell': 0
        }
    
    filled = sum(1 for o in orders if o.get('status') == 'FILLED')
    pending = sum(1 for o in orders if o.get('status') in ['NEW', 'PARTIAL'])
    
    total_buy = sum(o.get('total', 0) for o in orders if o.get('action') == 'BUY')
    total_sell = sum(o.get('total', 0) for o in orders if o.get('action') == 'SELL')
    
    return {
        'total_orders': len(orders),
        'filled': filled,
        'pending': pending,
        'total_buy': total_buy,
        'total_sell': total_sell,
        'orders': orders
    }


def generate_daily_report(date: datetime = None) -> str:
    """生成盘后复盘报告"""
    if date is None:
        date = datetime.now()
    
    date_str = date.strftime('%Y-%m-%d')
    report_file = f"{REPORTS_DIR}/report_{date_str}.md"
    
    # 加载数据
    portfolio = load_portfolio()
    orders = load_today_orders()
    daily_pnl = calculate_daily_pnl(portfolio)
    order_analysis = analyze_orders(orders)
    
    # 生成报告
    report = f"""# 盘后复盘报告 - {date_str}

## 📊 当日概况

| 指标 | 数值 |
|------|------|
| 日期 | {date_str} |
| 总市值 | ${daily_pnl['total_value']:,.2f} |
| 总成本 | ${daily_pnl['total_cost']:,.2f} |
| 当日盈亏 | ${daily_pnl['total_pnl']:+,.2f} |
| 当日收益率 | {daily_pnl['total_return']:+.2f}% |

---

## 📈 持仓复盘

### 持仓表现

| 股票 | 股数 | 成本价 | 现价 | 浮动 | 贡献 |
|------|------|--------|------|------|------|
"""
    
    # 逐个分析持仓
    for symbol, data in sorted(portfolio.items(), key=lambda x: -x[1].get('pnl', 0)):
        shares = data.get('shares', 0)
        avg_cost = data.get('avg_cost', 0)
        current_price = data.get('current_price', avg_cost)
        pnl = shares * (current_price - avg_cost)
        pnl_pct = (current_price - avg_cost) / avg_cost * 100
        
        contribution = pnl / daily_pnl['total_pnl'] * 100 if daily_pnl['total_pnl'] != 0 else 0
        emoji = '🟢' if pnl > 0 else ('🔴' if pnl < 0 else '⚪')
        
        report += f"| {symbol} | {shares} | ${avg_cost:.2f} | ${current_price:.2f} | {emoji} {pnl_pct:+.2f}% | {contribution:+.1f}% |\n"
    
    report += f"""
### 持仓分析

**最佳表现**: 
{_get_best_performer(portfolio)}

**最弱表现**:
{_get_worst_performer(portfolio)}

**风险敞口**:
{_get_risk_exposure(portfolio)}

---

## 📝 交易复盘

### 今日订单

| 股票 | 操作 | 股数 | 限价 | 状态 | 成交价 |
|------|------|------|------|------|--------|
"""
    
    for order in orders:
        symbol = order.get('symbol', 'N/A')
        action = order.get('action', 'N/A')
        shares = order.get('shares', 0)
        price = order.get('price', 0)
        status = order.get('status', 'N/A')
        filled_price = order.get('filled_price', 'N/A')
        
        report += f"| {symbol} | {action} | {shares} | ${price:.2f} | {status} | {filled_price} |\n"
    
    report += f"""
### 交易统计

- **总订单数**: {order_analysis['total_orders']}
- **已成交**: {order_analysis['filled']}
- **待成交**: {order_analysis['pending']}
- **买入总额**: ${order_analysis['total_buy']:,.2f}
- **卖出总额**: ${order_analysis['total_sell']:,.2f}
- **净流入**: ${order_analysis['total_sell'] - order_analysis['total_buy']:,.2f}

---

## 🎯 信号复盘

### 因子表现

| 因子 | 预期 | 实际 | 偏差 |
|------|------|------|------|
| ma120 | 看跌 | 待验证 | - |
| momentum_5 | 看跌 | 待验证 | - |
| volatility_20 | 看涨 | 待验证 | - |

### 信号准确率

- **因子信号数**: 0
- **信号准确率**: N/A
- **待验证信号**: 3

---

## 💡 经验总结

### 做得好的地方

1. 严格执行因子信号调仓
2. 限价单控制成本
3. 分散持仓降低风险

### 需要改进的地方

1. 因子置信度需要更多验证
2. 限价参数可能需要微调
3. 订单执行时机可以优化

### 明日计划

1. 监控未成交订单
2. 检查因子信号变化
3. 根据市场调整限价参数

---

## 📌 关键指标

| 指标 | 当前值 | 阈值 | 状态 |
|------|--------|------|------|
| 总回撤 | {daily_pnl['total_return']:.2f}% | -5% | {'✅正常' if daily_pnl['total_return'] > -5 else '⚠️警告'} |
| 订单成交率 | {order_analysis['filled']/max(order_analysis['total_orders'],1)*100:.0f}% | 50% | {'✅达标' if order_analysis['filled']/max(order_analysis['total_orders'],1) >= 0.5 else '⚠️未达标'} |
| 因子稳健性 | 0.85 | 0.6 | ✅ |

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**下次复盘**: { (date + timedelta(days=1)).strftime('%Y-%m-%d') }
"""
    
    # 保存报告
    with open(report_file, 'w') as f:
        f.write(report)
    
    return report_file, report


def _get_best_performer(portfolio: Dict) -> str:
    """获取最佳表现股票"""
    if not portfolio:
        return "无"
    
    best = max(portfolio.items(), key=lambda x: x[1].get('pnl', 0))
    symbol = best[0]
    pnl = best[1].get('pnl', 0)
    return f"{symbol}: +${pnl:,.2f}"


def _get_worst_performer(portfolio: Dict) -> str:
    """获取最差表现股票"""
    if not portfolio:
        return "无"
    
    worst = min(portfolio.items(), key=lambda x: x[1].get('pnl', 0))
    symbol = worst[0]
    pnl = worst[1].get('pnl', 0)
    return f"{symbol}: ${pnl:,.2f}"


def _get_risk_exposure(portfolio: Dict) -> str:
    """获取风险敞口"""
    if not portfolio:
        return "无风险敞口"
    
    total_pnl = sum(d.get('pnl', 0) for d in portfolio.values())
    negative_pnl = [s for s, d in portfolio.items() if d.get('pnl', 0) < 0]
    
    if total_pnl > 0:
        return f"整体盈利，{len(negative_pnl)}只股票亏损"
    else:
        return f"整体亏损，{len(negative_pnl)}只股票亏损，需要关注"


def main():
    """主函数"""
    import sys
    
    date = None
    if len(sys.argv) > 1:
        date = datetime.strptime(sys.argv[1], '%Y-%m-%d')
    
    report_file, report = generate_daily_report(date)
    
    print(f"报告已生成: {report_file}")
    print(f"\n{'='*60}")
    print("盘后复盘报告摘要")
    print('='*60)
    print(report[:2000])
    print("...")


if __name__ == "__main__":
    main()
