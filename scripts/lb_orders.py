#!/usr/bin/env python3
"""
Longbridge 订单状态检查脚本
修复版：从绝对路径加载凭证
"""

import json
from datetime import datetime
from longbridge.openapi import Config, TradeContext as Trade

CREDENTIALS_FILE = '/Users/yintaoye/.openclaw/workspace/skills/longbridge-trading/config/credentials.json'

def load_credentials():
    with open(CREDENTIALS_FILE) as f:
        data = json.load(f)
        return data.get('credentials', {})

def check_orders():
    creds = load_credentials()
    trade = Trade(Config(
        app_key=creds['app_key'],
        app_secret=creds['app_secret'],
        access_token=creds['access_token']
    ))
    
    orders = trade.today_orders()
    print(f"\n📊 订单状态 ({datetime.now().strftime('%H:%M')})")
    print("="*50)
    
    for order in orders:
        print(f"{order.symbol}: {order.side} {order.quantity} @ ${order.price} ({order.status})")
    
    print(f"\n共 {len(orders)} 个订单")

if __name__ == '__main__':
    try:
        check_orders()
    except Exception as e:
        print(f"错误: {e}")
