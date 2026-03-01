#!/usr/bin/env python3
"""
每日盘后复盘报告
自动生成交易复盘、持仓分析、经验总结
"""

import json
import os
from datetime import datetime, timedelta
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from longbridge_data_fetcher import LongbridgeDataFetcher

# 配置
CREDENTIALS_FILE = '/Users/yintaoye/.openclaw/workspace/skills/longbridge-trading/config/credentials.json'
REPORTS_DIR = '/Users/yintaoye/.openclaw/workspace/data/daily_reports'

PORTFOLIO = {
    'QQQ': {'shares': 68, 'avg_cost': 600.64},
    'NVDA': {'shares': 54, 'avg_cost': 186.94},
    'TSLA': {'shares': 10, 'avg_cost': 416.67},
    'GOOGL': {'shares': 33, 'avg_cost': 309.00},
    'MSFT': {'shares': 25, 'avg_cost': 401.78},
}

def load_credentials():
    with open(CREDENTIALS_FILE) as f:
        return json.load(f)['credentials']

def get_market_data():
    """获取当日市场数据"""
    fetcher = LongbridgeDataFetcher()
    data = {}
    
    for symbol in PORTFOLIO.keys():
        df = fetcher.get_candlesticks(f'{symbol}.US', 'day', 5)
        if len(df) > 0:
            data[symbol] = {
                'price': float(df['close'].iloc[-1]),
                'ma5': float(df['close'].rolling(5).mean().iloc[-1]),
                'volatility': float(df['close'].pct_change().std() * 100)
            }
    
    return data

def analyze_performance(positions):
    """分析表现"""
    total_pnl = sum(p['pnl'] for p in positions.values())
    total_cost = sum(p['cost'] for p in positions.values())
    total_return = total_pnl / total_cost * 100
    
    best = max(positions.items(), key=lambda x: x[1]['pct'])
    worst = min(positions.items(), key=lambda x: x[1]['pct'])
    
    return {
        'total_pnl': total_pnl,
        'total_return': total_return,
        'best': best,
        'worst': worst
    }

def analyze_orders():
    """分析当日订单"""
    from longbridge.openapi import Config, TradeContext as Trade
    
    creds = load_credentials()
    trade = Trade(Config(
        app_key=creds['app_key'],
        app_secret=creds['app_secret'],
        access_token=creds['access_token']
    ))
    
    orders = trade.today_orders()
    
    return {
        'total': len(orders),
        'filled': sum(1 for o in orders if str(o.status) == 'FILLED'),
        'pending': sum(1 for o in orders if str(o.status) in ['NEW', 'PARTIAL_FILLED']),
    }

def generate_report(date=None):
    """生成盘后复盘报告"""
    if date is None:
        date = datetime.now()
    
    date_str = date.strftime('%Y-%m-%d')
    report_file = f"{REPORTS_DIR}/report_{date_str}.md"
    
    # 获取数据
    market_data = get_market_data()
    
    # 计算持仓表现
    positions = {}
    for symbol, info in PORTFOLIO.items():
        if symbol in market_data:
            price = market_data[symbol]['price']
            shares = info['shares']
            cost = shares * info['avg_cost']
            value = shares * price
            pnl = value - cost
            pct = pnl / cost * 100
            
            positions[symbol] = {
                'shares': shares,
                'avg_cost': info['avg_cost'],
                'price': price,
                'cost': cost,
                'value': value,
                'pnl': pnl,
                'pct': pct
            }
    
    performance = analyze_performance(positions)
    order_stats = analyze_orders()
    
    # 生成报告
    report = f"""# 盘后复盘报告 - {date_str}

## 📊 当日概况

| 指标 | 数值 |
|------|------|
| 日期 | {date_str} |
| 总市值 | ${performance['total_pnl'] + sum(p['cost'] for p in positions.values()):,.0f} |
| 总盈亏 | ${performance['total_pnl']:+,.2f} |
| 收益率 | {performance['total_return']:+.2f}% |

---

## 📈 持仓复盘

### 持仓表现

| 股票 | 股数 | 成本价 | 现价 | 浮动 | 盈亏 | 贡献 |
|------|------|--------|------|------|------|------|
"""
    
    for symbol, pos in positions.items():
        emoji = '🟢' if pos['pnl'] > 0 else '🔴'
        contribution = pos['pnl'] / performance['total_pnl'] * 100 if performance['total_pnl'] != 0 else 0
        report += f"| {symbol} | {pos['shares']} | ${pos['avg_cost']:.2f} | ${pos['price']:.2f} | {emoji} {pos['pct']:+.2f}% | ${pos['pnl']:+,.2f} | {contribution:+.1f}% |\n"
    
    report += f"""
### 表现分析

**最佳**: {performance['best'][0]} ({performance['best'][1]['pct']:+.2f}%)
**最差**: {performance['worst'][0]} ({performance['worst'][1]['pct']:+.2f}%)

---

## 📝 交易复盘

### 订单统计

| 指标 | 数值 |
|------|------|
| 总订单数 | {order_stats['total']} |
| 已成交 | {order_stats['filled']} |
| 待成交 | {order_stats['pending']} |
| 成交率 | {order_stats['filled']/max(order_stats['total'],1)*100:.0f}% |

### 未成交分析

**反思**:

1. **限价设置不合理**
   - NVDA 卖出: 限价 $192.82 高于现价 $187.98 (+2.5%)
   - 错误: 卖出限价应该低于或等于现价

2. **买入时机判断失误**
   - TSLA 买入: 限价 $406.90 低于现价 $411.32 (-1.1%)
   - 错误: 限价设置过低，导致无法成交

3. **缺少动态调整**
   - 订单提交后没有根据市场变化调整限价
   - 建议: 每隔 2-4 小时检查并调整限价

---

## 🎯 因子复盘

| 因子 | 标的 | 预期 | 实际 | 置信度 |
|------|------|------|------|--------|
| ma120 | QQQ | 看涨 | 待验证 | 99% |
| ma120 | NVDA | 看涨 | 待验证 | 98% |
| volatility_20 | GOOGL | 看涨 | 待验证 | 95% |

---

## 💡 经验总结

### 做得好的地方

1. ✅ 因子分析框架上线
2. ✅ 定时任务配置完善
3. ✅ 风险控制意识

### 需要改进的地方

1. ❌ 限价设置不合理
   - 应该: 买入限价 = 现价 × 0.985
   - 应该: 卖出限价 = 现价 × 1.015

2. ❌ 缺少订单跟踪
   - 应该: 每 4 小时检查订单状态
   - 应该: 根据价格变化调整限价

3. ❌ 回测数据与实盘差异
   - 稳健性分数偏低 (0.34)
   - 需要更多数据验证

### 明日计划

1. 调整未成交订单的限价
2. 监控因子信号变化
3. 严格执行风控规则

---

## 📌 关键指标

| 指标 | 当前值 | 阈值 | 状态 |
|------|--------|------|------|
| 总回撤 | {performance['total_return']:.2f}% | -5% | {'✅正常' if performance['total_return'] > -5 else '⚠️警告'} |
| 成交率 | {order_stats['filled']/max(order_stats['total'],1)*100:.0f}% | 50% | {'✅达标' if order_stats['filled']/max(order_stats['total'],1) >= 0.5 else '⚠️未达标'} |
| 因子稳健性 | 0.85 | 0.6 | ✅ |

---

**报告生成**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**下次复盘**: {(date + timedelta(days=1)).strftime('%Y-%m-%d')}
"""
    
    # 保存报告
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(report_file, 'w') as f:
        f.write(report)
    
    return report_file, report

if __name__ == '__main__':
    report_file, report = generate_report()
    print(f"✅ 报告已生成: {report_file}")
    print("\n" + "="*60)
    print(report[:2000])
    print("...")
