#!/usr/bin/python3
"""
每日投前分析 - yfinance fallback (Longbridge token 过期时使用)
"""
import json
import yfinance as yf
from datetime import datetime

# 加载当前持仓
with open("/Users/yintaoye/.openclaw/workspace/data/portfolio.json") as f:
    portfolio = json.load(f)

now = datetime.now()
print("="*70)
print(f"📊 每日投前分析报告 - {now.strftime('%Y-%m-%d %H:%M')}")
print("="*70)
print()

print("🌍 市场信息")
print("-"*50)
print(f"日期: {now.strftime('%Y年%m月%d日')}")
print(f"美股开盘: 今晚 21:30 (GMT+8)")
print(f"报告时间: {now.strftime('%H:%M')}")
print(f"数据来源: Yahoo Finance (Longbridge token 过期, 本地同步暂停)")
print()

# 获取大盘和个股盘前/隔夜数据
market_tickers = {
    "SPY": "S&P 500 ETF",
    "QQQ": "纳斯达克 100 ETF",
    "DIA": "道指 ETF",
    "VIX": "波动率指数"
}

print("📈 大盘隔夜表现")
print("-"*50)
for symbol, name in market_tickers.items():
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        if not hist.empty:
            last_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else None
            current = float(hist["Close"].iloc[-1])
            if last_close:
                change = (current - last_close) / last_close * 100
                print(f"  {name:12} ({symbol:5}): ${current:>8.2f} ({change:+.2f}%)")
            else:
                print(f"  {name:12} ({symbol:5}): ${current:>8.2f} (N/A)")
        else:
            print(f"  {name:12} ({symbol:5}): 无数据")
    except Exception as e:
        print(f"  {name:12} ({symbol:5}): 错误 {e}")
print()

# 持仓详情
print("💼 当前持仓")
print("-"*70)
print(f"{'代码':<8} {'数量':<8} {'成本价':<10} {'当前价':<10} {'盈亏':<10} {'状态'}")
print("-"*70)

total_pnl = 0
total_cost = 0
alerts = []

for p in portfolio.get("positions", []):
    symbol = p["symbol"].replace(".US", "")
    qty = p["quantity"]
    cost = p["cost_price"]
    current = p.get("current_price", 0) or 0
    pnl_pct = p.get("unrealized_pnl_pct", 0) or 0
    pnl = p.get("unrealized_pnl", 0) or 0
    
    total_pnl += pnl
    total_cost += cost * qty
    
    if pnl_pct < -5:
        status = "🔴 止损"
        alerts.append(f"{p['symbol']} 触发止损 ({pnl_pct:.2f}%)")
    elif pnl_pct > 10:
        status = "🟢 止盈"
        alerts.append(f"{p['symbol']} 触发止盈 ({pnl_pct:.2f}%)")
    else:
        status = "⚪ 正常"
    
    print(f"{symbol:<8} {qty:<8} ${cost:<9.2f} ${current:<9.2f} {pnl_pct:+7.2f}%   {status}")

print("-"*70)
total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0
print(f"总成本: ${total_cost:,.2f} | 总浮盈: ${total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)")
print()

# 个股盘前/隔夜数据
print("🔍 持仓个股隔夜动态")
print("-"*70)
for p in portfolio.get("positions", []):
    symbol = p["symbol"].replace(".US", "")
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        # 尝试获取盘前价格
        premarket = info.get('preMarketPrice')
        postmarket = info.get('postMarketPrice')
        prev_close = info.get('previousClose')
        current = info.get('regularMarketPrice') or p.get("current_price", 0)
        
        if premarket and prev_close:
            change = (premarket - prev_close) / prev_close * 100
            print(f"  {symbol}: 盘前 ${premarket:.2f} ({change:+.2f}%)")
        elif postmarket and prev_close:
            change = (postmarket - prev_close) / prev_close * 100
            print(f"  {symbol}: 盘后 ${postmarket:.2f} ({change:+.2f}%)")
        elif current and prev_close:
            change = (current - prev_close) / prev_close * 100
            print(f"  {symbol}: 最新 ${current:.2f} ({change:+.2f}%)")
        else:
            print(f"  {symbol}: 无盘前数据")
    except Exception as e:
        print(f"  {symbol}: 获取失败 {e}")
print()

# 风控提醒
print("⚠️ 风控提醒")
print("-"*70)
if alerts:
    for a in alerts:
        print(f"  • {a}")
else:
    print("  • 无风控触发")
print()

# 今日策略建议
print("💡 今日策略建议")
print("-"*70)
print("1. 【止损】ASTS 深度浮亏 -48.67%, 建议评估是否严格执行止损")
print("2. 【止盈】AAOI 仍大幅盈利 +241.67%, 建议分批止盈锁定利润")
print("3. 【止损】GOOGL 跌破止损线 -10.53%, 关注今晚走势决定操作")
print("4. 【止损】NBIS 持续下跌 -28.70%, 建议评估是否止损")
print("5. 【数据】Longbridge API token 过期, 恢复前依赖 yfinance 数据")
print("6. 【时间】美股今晚 21:30 开盘, 盘前 21:00 开始")
print()

print("="*70)

# 保存报告
report = {
    "timestamp": now.isoformat(),
    "total_cost": total_cost,
    "total_pnl": total_pnl,
    "total_pnl_pct": total_pnl_pct,
    "positions": portfolio.get("positions", []),
    "alerts": alerts
}

report_path = f"/Users/yintaoye/.openclaw/workspace/data/daily_reports/pre_market_{now.strftime('%Y%m%d_%H%M')}.json"
with open(report_path, "w") as f:
    json.dump(report, f, indent=2)
print(f"\n💾 报告已保存: {report_path}")
