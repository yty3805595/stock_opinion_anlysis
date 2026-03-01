#!/usr/bin/env python3
"""
Longbridge 持仓风控监控脚本
使用预设持仓 + Longbridge 实时行情
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from longbridge.openapi import Config, QuoteContext as Quote


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


# 当前持仓配置
PORTFOLIO = {
    'QQQ': {'shares': 68, 'avg_cost': 600.64},
    'NVDA': {'shares': 54, 'avg_cost': 186.94},
    'TSLA': {'shares': 10, 'avg_cost': 416.67},
    'GOOGL': {'shares': 33, 'avg_cost': 309.00},
    'MSFT': {'shares': 25, 'avg_cost': 401.78},
}


def check_positions():
    """检查持仓风控"""
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
        quote = Quote(config)
        print("✅ Longbridge 连接成功！")
        
        print(f"\n🛡️ 持仓风控监控 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
        print("="*70)
        
        total_value = 0
        total_cost = 0
        positions_data = []
        
        for symbol, info in PORTFOLIO.items():
            try:
                # 获取实时行情
                data = quote.quote([f"{symbol}.US"])
                if data and len(data) > 0:
                    current_price = float(data[0].last_done)
                else:
                    print(f"⚠️ 无法获取 {symbol} 价格")
                    continue
                
                shares = info['shares']
                avg_cost = info['avg_cost']
                
                market_value = shares * current_price
                cost_basis = shares * avg_cost
                pnl = market_value - cost_basis
                pct = (current_price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0
                
                total_value += market_value
                total_cost += cost_basis
                
                positions_data.append({
                    'symbol': symbol,
                    'shares': shares,
                    'avg_cost': avg_cost,
                    'price': current_price,
                    'pnl': pnl,
                    'pct': pct
                })
                
                emoji = '🟢' if pnl > 0 else '🔴'
                print(f"{emoji} {symbol}")
                print(f"   {shares}股 @ ${avg_cost:.2f} → ${current_price:.2f}")
                print(f"   盈亏: {pct:+.2f}% (${pnl:+,.0f})")
                print()
                
            except Exception as e:
                print(f"⚠️ 获取 {symbol} 数据失败: {e}")
                continue
        
        total_pnl = total_value - total_cost
        total_pct = total_pnl / total_cost * 100 if total_cost > 0 else 0
        
        print("="*70)
        print(f"💰 总市值: ${total_value:,.0f}")
        print(f"📈 总盈亏: ${total_pnl:+,.0f} ({total_pct:+.2f}%)")
        
        # 风控检查
        print("\n🛡️ 风控状态:")
        max_loss = min(p['pct'] for p in positions_data) if positions_data else 0
        if max_loss < -5:
            print(f"   ⚠️ 触发止损线: {max_loss:.2f}%")
        else:
            print(f"   ✅ 正常 (最大亏损 {max_loss:.2f}%)")
        
    except Exception as e:
        import traceback
        print(f"❌ 连接失败: {e}")
        traceback.print_exc()


if __name__ == '__main__':
    check_positions()
