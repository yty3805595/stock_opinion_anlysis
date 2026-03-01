#!/usr/bin/env python3
"""
美股持仓持续监控系统
功能:
1. 定时检查持仓价格
2. 触发止损时提醒
3. 监控期权保护效果
4. 生成交易报告
"""

import json
import time
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Longbridge API
from longbridge.openapi import Config, QuoteContext, TradeContext

# 配置
WORKSPACE = Path(__file__).parent.parent
CONFIG_PATH = WORKSPACE / "skills/longbridge-trading/config/credentials.json"
PORTFOLIO_PATH = WORKSPACE / "data/portfolio.json"
LOG_PATH = WORKSPACE / "data/monitor.log"

# 风控参数
STOP_LOSS_PCT = 5.0  # 止损线 5%
PROFIT_TAKE_PCT = 10.0  # 止盈线 10%
CHECK_INTERVAL = 300  # 检查间隔 (秒) = 5分钟

# 持仓配置 (已更新 2026-02-28)
POSITIONS = {
    "TSLA.US": {"qty": 10, "cost": 416.67, "has_protection": True, "put_symbol": "TSLA260320P395000.US", "put_strike": 395},
    # NVDA.US 已止损 (2026-02-28)
    "MSFT.US": {"qty": 25, "cost": 401.78, "has_protection": False},
    "GOOGL.US": {"qty": 33, "cost": 309.00, "has_protection": False},
    "QQQ.US": {"qty": 68, "cost": 600.64, "has_protection": False},
}


def load_credentials():
    """加载 Longbridge 凭证"""
    with open(CONFIG_PATH) as f:
        creds = json.load(f)["credentials"]
    return Config(
        app_key=creds["app_key"],
        app_secret=creds["app_secret"],
        access_token=creds["access_token"],
    )


def get_quotes(symbols, quote_ctx):
    """获取实时报价"""
    return quote_ctx.quote(symbols)


def check_position(symbol, current_price, config):
    """检查单个持仓状态"""
    if symbol not in POSITIONS:
        return None
    
    pos = POSITIONS[symbol]
    cost = pos["cost"]
    qty = pos["qty"]
    
    pnl = (current_price - cost) * qty
    pnl_pct = (current_price - cost) / cost * 100
    
    # 计算止损价
    stop_price = cost * (1 - STOP_LOSS_PCT / 100)
    profit_price = cost * (1 + PROFIT_TAKE_PCT / 100)
    
    # 状态判断
    status = "🟢 OK"
    alert = None
    
    if pnl_pct <= -STOP_LOSS_PCT:
        status = "🔴 止损"
        alert = f"触发止损! 亏损 {pnl_pct:.2f}%"
    elif pnl_pct <= -3.0:
        status = "🟡 警告"
        alert = f"接近止损线! 亏损 {pnl_pct:.2f}%"
    elif pnl_pct >= PROFIT_TAKE_PCT:
        status = "🟢 止盈"
        alert = f"达到止盈线! 盈利 {pnl_pct:.2f}%"
    
    return {
        "symbol": symbol,
        "qty": qty,
        "cost": cost,
        "current": current_price,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "stop_price": stop_price,
        "profit_price": profit_price,
        "status": status,
        "alert": alert,
        "has_protection": pos.get("has_protection", False),
    }


def check_option_protection(symbol, quote_ctx):
    """检查期权保护"""
    if symbol not in POSITIONS:
        return None
    
    pos = POSITIONS[symbol]
    if not pos.get("has_protection"):
        return None
    
    try:
        put_symbol = pos["put_symbol"]
        put = quote_ctx.quote([put_symbol])[0]
        put_price = float(put.last_done)
        
        # 获取正股价格
        stock = quote_ctx.quote([symbol])[0]
        stock_price = float(stock.last_done)
        
        put_strike = pos["put_strike"]
        distance_to_strike = (stock_price - put_strike) / put_strike * 100
        
        return {
            "symbol": put_symbol,
            "strike": put_strike,
            "put_price": put_price,
            "stock_price": stock_price,
            "distance_pct": distance_to_strike,
            "protected": distance_to_strike > 0,
        }
    except Exception as e:
        return {"error": str(e)}


def generate_report(positions_data, option_data, total_pnl):
    """生成监控报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""
=================================================================
📊 美股持仓监控报告 - {now}
=================================================================

📈 持仓概况:
"""
    
    alerts = []
    for p in positions_data:
        emoji = "🟢" if p["pnl_pct"] >= 0 else "🔴"
        report += f"\n{emoji} {p['symbol']}: {p['qty']}股 @ ${p['current']:.2f}"
        report += f"\n   成本: ${p['cost']:.2f} | 盈亏: ${p['pnl']:.2f} ({p['pnl_pct']:+.2f}%)"
        report += f"\n   止损: ${p['stop_price']:.2f} | 状态: {p['status']}"
        
        if p.get("has_protection"):
            opt = option_data.get(p["symbol"])
            if opt and "error" not in opt:
                report += f"\n   🛡️ 期权保护: Put ${opt['strike']} @ ${opt['put_price']:.2f}"
                if opt["protected"]:
                    report += f" (距行权价 +{opt['distance_pct']:.1f}%)"
                else:
                    report += f" ⚠️ 已跌破行权价!"
        
        if p["alert"]:
            alerts.append(f"   ⚠️ {p['symbol']}: {p['alert']}")
    
    report += f"\n\n💰 总盈亏: ${total_pnl:,.2f}"
    
    # 期权保护总览
    report += "\n\n🛡️ 期权保护状态:"
    for sym, opt in option_data.items():
        if "error" in opt:
            report += f"\n   {sym}: 获取失败"
        elif opt.get("protected"):
            report += f"\n   {sym}: ✅ 安全 (距行权价 +{opt['distance_pct']:.1f}%)"
        else:
            report += f"\n   {sym}: ⚠️ 危险 (跌破行权价)"
    
    # 警报
    if alerts:
        report += "\n\n🚨 风险警报:"
        report += "\n" + "\n".join(alerts)
    
    report += "\n\n=================================================================\n"
    
    return report


def monitor_once():
    """执行一次监控"""
    config = load_credentials()
    quote_ctx = QuoteContext(config)
    trade_ctx = TradeContext(config)
    
    # 获取所有股票报价
    symbols = list(POSITIONS.keys())
    quotes = get_quotes(symbols, quote_ctx)
    
    # 检查持仓
    positions_data = []
    total_pnl = 0
    
    for q in quotes:
        result = check_position(q.symbol, float(q.last_done), config)
        if result:
            positions_data.append(result)
            total_pnl += result["pnl"]
    
    # 检查期权保护
    option_data = {}
    for sym in POSITIONS.keys():
        opt = check_option_protection(sym, quote_ctx)
        if opt:
            option_data[sym] = opt
    
    # 生成报告
    report = generate_report(positions_data, option_data, total_pnl)
    print(report)
    
    # 写入日志
    with open(LOG_PATH, "a") as f:
        f.write(report)
    
    # 检查是否需要发送警报
    alerts = [p for p in positions_data if p["alert"]]
    if alerts:
        print("\n🚨 需要关注!")
        for a in alerts:
            print(f"   {a['symbol']}: {a['alert']}")
        return True  # 有警报
    
    return False  # 无警报


def main():
    """主循环"""
    print("🚀 美股持仓监控系统启动...")
    print(f"检查间隔: {CHECK_INTERVAL}秒")
    print("按 Ctrl+C 停止\n")
    
    while True:
        try:
            monitor_once()
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            print("\n👋 监控系统已停止")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    # 支持命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        monitor_once()
    else:
        main()
