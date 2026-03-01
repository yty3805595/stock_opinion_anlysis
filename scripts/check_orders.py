#!/usr/bin/env python3
"""
Longbridge 订单状态检查脚本
从配置文件加载凭证，正确连接 API
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from longbridge.openapi import Config, TradeContext as Trade


def load_credentials():
    """从配置文件加载凭证"""
    # 尝试多个可能的路径
    possible_paths = [
        '/Users/yintaoye/.openclaw/workspace/skills/longbridge-trading/config/credentials.json',
        '/Users/yintaoye/.openclaw/skills/longbridge-trading/config/credentials.json',
        os.path.expanduser('~/.longbridge/credentials.json')
    ]
    
    for config_file in possible_paths:
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    return data.get('credentials', {})
        except Exception as e:
            continue
    
    print(f"❌ 无法找到凭证文件")
    return None


def check_orders():
    """检查订单状态"""
    credentials = load_credentials()
    if not credentials:
        print("无法加载凭证")
        return
    
    config = Config(
        app_key=credentials.get('app_key', ''),
        app_secret=credentials.get('app_secret', ''),
        access_token=credentials.get('access_token', '')
    )
    
    try:
        trade = Trade(config)
        print("✅ Longbridge 连接成功！")
        
        # 获取今日订单
        orders = trade.today_orders()
        print(f"\n📊 订单状态检查 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
        print("="*60)
        
        if len(orders) == 0:
            print("今日无订单")
            return
        
        print(f"总订单数: {len(orders)}\n")
        
        for order in orders:
            status_emoji = {
                'NEW': '🟡',
                'FILLED': '🟢',
                'PARTIAL_FILLED': '🟠',
                'CANCELLED': '🔴',
                'REJECTED': '🔴'
            }.get(str(order.status), '⚪')
            
            print(f"{status_emoji} {order.symbol}")
            print(f"   {order.side} {order.quantity}股 @ ${order.price}")
            print(f"   状态: {order.status}")
            print(f"   成交: {order.executed_quantity}")
            print()
        
        # 统计
        filled = sum(1 for o in orders if str(o.status) == 'FILLED')
        pending = sum(1 for o in orders if str(o.status) in ['NEW', 'PARTIAL_FILLED'])
        
        print("="*60)
        print(f"📈 统计: 已成交 {filled}, 待成交 {pending}")
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")


if __name__ == '__main__':
    check_orders()
