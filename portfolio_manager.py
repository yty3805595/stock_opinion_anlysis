#!/usr/bin/env python3
"""
Astra 持仓管理系统 - 盘中实时监控、自动止盈止损
目标：月收益 3%，最大回撤控制在 5% 以内

策略规则：
1. 止损线：单只股票亏损 > 5% 立即止损
2. 止盈线：单只股票盈利 > 10% 部分减仓
3. 监控频率：盘中每 30 分钟检查一次
4. 风险控制：总仓位亏损 > 3% 停止开新仓
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from longbridge.openapi import Config, QuoteContext

# 路径配置
WORKSPACE = "/Users/yintaoye/.openclaw/workspace"
CONFIG_PATH = f"{WORKSPACE}/longbridge_tokens.json"
PORTFOLIO_PATH = f"{WORKSPACE}/data/portfolio.json"
LOG_PATH = f"{WORKSPACE}/data/portfolio_monitor.log"
ALERT_LOG = f"{WORKSPACE}/data/portfolio_alerts.json"

# 风险参数
STOP_LOSS_PCT = 5.0      # 止损线 (%)
TAKE_PROFIT_PCT = 10.0   # 止盈线 (%)
TRAILING_STOP = 3.0       # 移动止损 (%)
MAX_POSITION_PCT = 10.0   # 单只股票最大仓位 (%)
MAX_DAILY_LOSS = 3.0      # 单日最大亏损 (%)
REBALANCE_THRESHOLD = 5.0 # 再平衡阈值 (%)


def load_tokens():
    """加载 API 凭证"""
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_current_prices(symbols):
    """获取实时价格"""
    tokens = load_tokens()
    config = Config(
        app_key='a66815c327617b848e55f6714dfb809c',
        app_secret='a94e7a77710a06dcc7f7449b29ffa2adab9ccc2ab6f668d232d6304560813b8c',
        access_token=tokens['access_token']
    )
    
    quote_ctx = QuoteContext(config=config)
    
    try:
        # 尝试多种方式获取价格
        quotes = quote_ctx.quote(symbols)
        prices = {}
        for q in quotes:
            if q:
                prices[q.symbol] = getattr(q, 'last', None) or getattr(q, 'close', None)
        return prices
    except Exception as e:
        print(f"获取价格失败: {e}")
        return {}


def load_portfolio():
    """加载持仓数据"""
    if os.path.exists(PORTFOLIO_PATH):
        with open(PORTFOLIO_PATH) as f:
            return json.load(f)
    return {"positions": {}}


def save_portfolio(portfolio):
    """保存持仓数据"""
    portfolio["last_update"] = datetime.now().isoformat()
    with open(PORTFOLIO_PATH, 'w') as f:
        json.dump(portfolio, f, indent=2)


def calculate_pnl(position, current_price):
    """计算盈亏"""
    avg_price = position['avg_price']
    pnl = (current_price - avg_price) / avg_price * 100
    return round(pnl, 2)


def should_stop_loss(position, current_price):
    """判断是否应该止损"""
    pnl_pct = calculate_pnl(position, current_price)
    return pnl_pct <= -STOP_LOSS_PCT


def should_take_profit(position, current_price, high_price):
    """判断是否应该止盈（移动止盈）"""
    pnl_pct = calculate_pnl(position, current_price)
    
    # 静态止盈
    if pnl_pct >= TAKE_PROFIT_PCT:
        return "static"
    
    # 移动止盈：盈利回吐超过 TRAILING_STOP
    if high_price and pnl_pct > 0:
        trailing_pnl = calculate_pnl(position, high_price)
        if trailing_pnl - pnl_pct >= TRAILING_STOP:
            return "trailing"
    
    return False


def analyze_market_sentiment():
    """分析市场情绪（简化版）"""
    # 可以接入 Polymarket 或其他数据源
    # 返回: "bullish", "bearish", "neutral"
    return "neutral"


def generate_action(position, current_price, high_price, market_sentiment):
    """生成操作建议"""
    pnl_pct = calculate_pnl(position, current_price)
    action = {
        "action": "hold",
        "reason": "",
        "priority": 0
    }
    
    # 止损
    if should_stop_loss(position, current_price):
        action = {
            "action": "sell",
            "reason": f"止损触发 ({pnl_pct:.1f}% < -{STOP_LOSS_PCT}%)",
            "priority": 1
        }
    
    # 止盈
    elif tp := should_take_profit(position, current_price, high_price):
        if tp == "static":
            action = {
                "action": "sell_half",
                "reason": f"止盈触发 (+{pnl_pct:.1f}% >= {TAKE_PROFIT_PCT}%)",
                "priority": 2
            }
        elif tp == "trailing":
            action = {
                "action": "sell_half",
                "reason": f"移动止盈触发 (回吐 {TRAILING_STOP}%)",
                "priority": 2
            }
    
    # 市场情绪调整
    elif market_sentiment == "bearish" and pnl_pct < -2:
        action = {
            "action": "reduce",
            "reason": "市场偏弱，减仓保护利润",
            "priority": 3
        }
    
    return action


def generate_report(positions, prices, actions):
    """生成监控报告"""
    total_pnl = 0
    total_value = 0
    
    report = []
    report.append("=" * 60)
    report.append(f"📊 持仓监控报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 60)
    
    for symbol, pos in positions.items():
        current_price = prices.get(symbol, pos['current_price'])
        pnl_pct = calculate_pnl(pos, current_price)
        market_value = pos['quantity'] * current_price
        total_value += market_value
        total_pnl += pos.get('market_value', 0) - (pos['quantity'] * pos['avg_price'])
        
        status = "🟢" if pnl_pct >= 0 else "🔴"
        action_info = actions.get(symbol, {})
        action_str = f" [{action_info.get('action', 'hold')}]" if action_info.get('action') != 'hold' else ""
        
        report.append(f"{status} {symbol}: ${current_price:.2f} ({pnl_pct:+.2f}%){action_str}")
    
    report.append("-" * 60)
    total_pnl_pct = (total_pnl / (total_value - total_pnl)) * 100 if total_value != total_pnl else 0
    report.append(f"💰 总市值: ${total_value:,.2f}")
    report.append(f"{'📈' if total_pnl >= 0 else '📉'} 总盈亏: ${total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)")
    report.append("=" * 60)
    
    return "\n".join(report), total_pnl, total_value


def save_alerts(alerts):
    """保存告警到文件"""
    alert_data = {
        "timestamp": datetime.now().isoformat(),
        "alerts": alerts
    }
    with open(ALERT_LOG, 'w') as f:
        json.dump(alert_data, f, indent=2)


def monitor_portfolio():
    """主监控函数"""
    # 1. 加载数据
    portfolio = load_portfolio()
    positions = portfolio.get("positions", {})
    
    if not positions:
        print("无持仓")
        return []
    
    symbols = list(positions.keys())
    
    # 2. 获取实时价格
    prices = get_current_prices(symbols)
    
    # 更新持仓价格
    for symbol in symbols:
        if symbol in prices:
            positions[symbol]['current_price'] = prices[symbol]
            positions[symbol]['market_value'] = positions[symbol]['quantity'] * prices[symbol]
            positions[symbol]['pnl'] = positions[symbol]['market_value'] - (positions[symbol]['quantity'] * positions[symbol]['avg_price'])
            positions[symbol]['pnl_pct'] = calculate_pnl(positions[symbol], prices[symbol])
    
    # 3. 分析操作
    market_sentiment = analyze_market_sentiment()
    actions = {}
    alerts = []
    
    for symbol, pos in positions.items():
        current_price = prices.get(symbol, pos['current_price'])
        high_price = pos.get('high_price', current_price)
        
        # 更新最高价（用于移动止盈）
        if current_price > high_price:
            high_price = current_price
            pos['high_price'] = high_price
        
        action = generate_action(pos, current_price, high_price, market_sentiment)
        if action['action'] != 'hold':
            actions[symbol] = action
            alerts.append({
                "symbol": symbol,
                "action": action['action'],
                "reason": action['reason'],
                "price": current_price,
                "pnl_pct": calculate_pnl(pos, current_price)
            })
        
        # 保存 high_price
        pos['high_price'] = high_price
    
    # 4. 生成报告
    report, total_pnl, total_value = generate_report(positions, prices, actions)
    print(report)
    
    # 5. 记录日志
    with open(LOG_PATH, 'a') as f:
        f.write(report + "\n")
    
    # 6. 保存告警
    if alerts:
        save_alerts(alerts)
        print("\n⚠️ 需要关注:")
        for alert in alerts:
            print(f"  - {alert['symbol']}: {alert['reason']}")
    
    # 7. 保存更新后的持仓
    save_portfolio(portfolio)
    
    return actions


def main():
    """CLI 入口"""
    print(f"\n🕐 开始持仓监控: {datetime.now().isoformat()}")
    
    actions = monitor_portfolio()
    
    print(f"\n✅ 监控完成 (发现 {len(actions)} 个需要操作)")


if __name__ == "__main__":
    main()
