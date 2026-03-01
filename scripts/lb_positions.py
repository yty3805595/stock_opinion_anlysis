#!/usr/bin/env python3
"""
Longbridge 持仓风控监控脚本
增强版：多维度风控检查
"""

import json
from datetime import datetime
from decimal import Decimal
from longbridge.openapi import Config, QuoteContext as Quote, TradeContext as Trade

CREDENTIALS_FILE = '/Users/yintaoye/.openclaw/workspace/skills/longbridge-trading/config/credentials.json'

# 风控参数
STOP_LOSS_PCT = -5.0       # 止损线
TAKE_PROFIT_PCT = 10.0     # 止盈线
TRAILING_STOP_PCT = 3.0    # 移动止损

def load_credentials():
    with open(CREDENTIALS_FILE) as f:
        data = json.load(f)
        return data.get('credentials', {})

def get_current_price(quote, symbol):
    """获取实时价格"""
    try:
        q = quote.quote([symbol])[0]
        return float(q.last_done) if q.last_done else float(q.prev_close)
    except:
        return None

def check_positions():
    creds = load_credentials()
    
    trade = Trade(Config(
        app_key=creds['app_key'],
        app_secret=creds['app_secret'],
        access_token=creds['access_token']
    ))
    
    quote = Quote(Config(
        app_key=creds['app_key'],
        app_secret=creds['app_secret'],
        access_token=creds['access_token']
    ))
    
    symbols = ["QQQ.US", "NVDA.US", "TSLA.US", "GOOGL.US", "MSFT.US"]
    positions = trade.stock_positions(symbols)
    
    print(f"\n🛡️ 持仓风控 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("="*75)
    
    # 收集数据
    holdings = []
    total_value = Decimal('0')
    total_cost = Decimal('0')
    
    position_list = positions.channels[0].positions if positions.channels else []
    
    for pos in position_list:
        if pos.quantity == 0:
            continue
        
        symbol = pos.symbol
        shares = int(pos.quantity)
        avg_cost = Decimal(str(pos.cost_price))
        
        # 获取当前价
        current_price = get_current_price(quote, symbol)
        if current_price is None:
            current_price = float(avg_cost)
        
        current_price = Decimal(str(current_price))
        
        value = shares * current_price
        cost = shares * avg_cost
        pnl = value - cost
        pct = float(pnl / cost * 100) if cost > 0 else 0
        
        # 计算距止损/止盈距离
        stop_loss_price = float(avg_cost) * (1 + STOP_LOSS_PCT / 100)
        take_profit_price = float(avg_cost) * (1 + TAKE_PROFIT_PCT / 100)
        
        distance_to_stop = (float(current_price) - stop_loss_price) / stop_loss_price * 100
        distance_to_tp = (take_profit_price - float(current_price)) / take_profit_price * 100
        
        holdings.append({
            'symbol': symbol.replace('.US', ''),
            'shares': shares,
            'avg_cost': float(avg_cost),
            'current_price': float(current_price),
            'pnl': float(pnl),
            'pct': pct,
            'stop_loss_price': stop_loss_price,
            'take_profit_price': take_profit_price,
            'distance_to_stop': distance_to_stop,
            'distance_to_tp': distance_to_tp
        })
        
        total_value += value
        total_cost += cost
    
    # 打印持仓详情
    print("\n📊 持仓明细:")
    print("-"*75)
    print(f"{'股票':<8} {'股数':<6} {'成本':<10} {'当前':<10} {'盈亏':<14} {'距止损':<8} {'距止盈':<8}")
    print("-"*75)
    
    alerts = []
    
    for h in holdings:
        emoji = '🟢' if h['pct'] > 0 else '🔴'
        
        # 检查是否触发风控
        if h['pct'] <= STOP_LOSS_PCT:
            alerts.append(f"🔴 {h['symbol']} 触发止损! ({h['pct']:.1f}%)")
        elif h['pct'] >= TAKE_PROFIT_PCT:
            alerts.append(f"🟢 {h['symbol']} 触发止盈! ({h['pct']:.1f}%)")
        elif h['distance_to_stop'] < 1:
            alerts.append(f"⚠️ {h['symbol']} 接近止损 ({h['distance_to_stop']:.1f}%)")
        
        # 打印
        print(f"{h['symbol']:<8} {h['shares']:<6} ${h['avg_cost']:<9.2f} ${h['current_price']:<9.2f} "
              f"{emoji} ${h['pnl']:>+10,.0f} ({h['pct']:>+6.1f}%)  {h['distance_to_stop']:>+6.1f}%  {h['distance_to_tp']:>+6.1f}%")
    
    # 汇总
    total_pnl = float(total_value - total_cost)
    total_pct = float(total_pnl / float(total_cost) * 100) if total_cost > 0 else 0
    
    print("-"*75)
    print(f"💰 总市值: ${float(total_value):,.2f}")
    print(f"📈 总盈亏: ${total_pnl:+,.2f} ({total_pct:+.2f}%)")
    
    # 风控规则检查
    print("\n🛡️ 风控检查:")
    print("-"*75)
    
    # 1. 止损检查
    stop_loss_triggered = [h for h in holdings if h['pct'] <= STOP_LOSS_PCT]
    if stop_loss_triggered:
        print(f"🔴 止损触发: {', '.join([h['symbol'] for h in stop_loss_triggered])}")
    else:
        print(f"✅ 止损: 未触发")
    
    # 2. 止盈检查
    take_profit_triggered = [h for h in holdings if h['pct'] >= TAKE_PROFIT_PCT]
    if take_profit_triggered:
        print(f"🟢 止盈触发: {', '.join([h['symbol'] for h in take_profit_triggered])}")
    else:
        print(f"✅ 止盈: 未触发")
    
    # 3. 接近止损预警 (1%以内)
    near_stop = [h for h in holdings if 0 < h['distance_to_stop'] < 1]
    if near_stop:
        print(f"⚠️ 接近止损: {', '.join([h['symbol'] for h in near_stop])}")
    
    # 4. 总账户风控
    if total_pct <= STOP_LOSS_PCT:
        alerts.append(f"🔴 总账户触发止损! ({total_pct:.1f}%)")
    
    # 告警汇总
    print("\n" + "="*75)
    if alerts:
        print("🚨 告警:")
        for alert in alerts:
            print(f"  {alert}")
    else:
        print("✅ 风控正常 - 无告警")
    
    print("="*75)

if __name__ == '__main__':
    try:
        check_positions()
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
