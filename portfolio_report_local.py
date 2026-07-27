#!/usr/bin/python3
"""
持仓监控报告 - 使用本地数据 (Longbridge API token 过期时使用)
"""
import json
from datetime import datetime

with open("/Users/yintaoye/.openclaw/workspace/data/portfolio.json") as f:
    portfolio = json.load(f)

print("="*60)
print(f"📊 持仓监控报告 ({portfolio.get('last_update', 'N/A')})")
print("="*60)

positions = portfolio.get("positions", [])

# 简单统计
total_pnl = sum(p.get("unrealized_pnl", 0) or 0 for p in positions)
total_cost = sum(p.get("cost_price", 0) * p.get("quantity", 0) for p in positions)
total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0

print(f"\n总成本: ${total_cost:,.2f}")
print(f"总浮盈: ${total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)")
print("-"*60)

alerts = []
for p in positions:
    symbol = p["symbol"].replace(".US", "")
    qty = p["quantity"]
    cost = p["cost_price"]
    current = p.get("current_price", 0) or 0
    pnl_pct = p.get("unrealized_pnl_pct", 0) or 0
    
    if pnl_pct < -5:
        status = "🔴 止损"
        alerts.append(f"{p['symbol']} 触发止损 ({pnl_pct:.2f}%)")
    elif pnl_pct > 10:
        status = "🟢 止盈"
        alerts.append(f"{p['symbol']} 触发止盈 ({pnl_pct:.2f}%)")
    else:
        status = "⚪ 正常"
    
    print(f"  {symbol:6} | {qty:4}股 | 成本 ${cost:7.2f} | 现价 ${current:7.2f} | {pnl_pct:+7.2f}% | {status}")

print("-"*60)
if alerts:
    print("\n⚠️ 风控提醒:")
    for a in alerts:
        print(f"  - {a}")
else:
    print("\n✅ 无风控触发")

# 写入报告
report_path = f"/Users/yintaoye/.openclaw/workspace/data/daily_reports/portfolio_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
report = {
    "timestamp": datetime.now().isoformat(),
    "total_cost": total_cost,
    "total_pnl": total_pnl,
    "total_pnl_pct": total_pnl_pct,
    "positions": positions,
    "alerts": alerts
}
with open(report_path, "w") as f:
    json.dump(report, f, indent=2)
print(f"\n💾 报告已保存: {report_path}")
print("="*60)
