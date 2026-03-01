#!/usr/bin/env python3
"""
NVDA 期权每小时监控脚本
"""

import json
from datetime import datetime
from longbridge.openapi import Config, QuoteContext as Quote

CREDENTIALS_FILE = '/Users/yintaoye/.openclaw/workspace/skills/longbridge-trading/config/credentials.json'
OPTION_SYMBOL = "NVDA260306C195000.US"
ENTRY_PRICE = 6.78  # 建仓价格

def load_credentials():
    with open(CREDENTIALS_FILE) as f:
        data = json.load(f)
        return data.get('credentials', {})

def main():
    creds = load_credentials()
    quote = Quote(Config(
        app_key=creds['app_key'],
        app_secret=creds['app_secret'],
        access_token=creds['access_token']
    ))
    
    print("="*70)
    print(f"📊 NVDA 期权每小时监控")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    try:
        opt_q = quote.option_quote([OPTION_SYMBOL])[0]
        
        current_price = float(opt_q.last_done)
        prev_close = float(opt_q.prev_close)
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else 0
        
        # 正股价格
        stock_q = quote.quote(['NVDA.US'])[0]
        stock_price = float(stock_q.last_done) if stock_q.last_done else float(stock_q.prev_close)
        
        print(f"\n📈 期权: {OPTION_SYMBOL}")
        print(f"  当前价格: ${current_price:.2f}")
        print(f"  昨收: ${prev_close:.2f}")
        print(f"  涨跌: ${change:+.2f} ({change_pct:+.2f}%)")
        
        print(f"\n📈 正股: NVDA")
        print(f"  当前价格: ${stock_price:.2f}")
        print(f"  Strike: $195.00")
        print(f"  状态: {'ITM (价内)' if stock_price > 195 else 'OTM (价外)'}")
        
        # 盈亏
        pnl = current_price - ENTRY_PRICE
        pnl_pct = (pnl / ENTRY_PRICE) * 100
        
        print(f"\n💰 建仓成本: ${ENTRY_PRICE:.2f}")
        print(f"💵 当前盈亏: ${pnl:+.2f} ({pnl_pct:+.1f}%)")
        
        # 告警
        print(f"\n🛡️ 状态:")
        if pnl_pct < -30:
            print(f"  🔴 权利金下跌超过30%! 建议考虑平仓")
        elif pnl_pct < -20:
            print(f"  ⚠️ 权利金下跌超过20%")
        elif pnl > 0:
            print(f"  ✅ 盈利中")
        else:
            print(f"  📊 正常范围")
        
        print("="*70)
        
    except Exception as e:
        print(f"❌ 获取失败: {e}")

if __name__ == '__main__':
    main()
