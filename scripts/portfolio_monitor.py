#!/usr/bin/env python3
"""
EOF 策略持仓监控系统

⚠️ 重要提示：
- 当前所有数据均为【模拟数据】
- 真实交易需要提供券商账号（Longbridge）
- 本系统仅用于策略回测和信号生成
"""

import requests
import json
from datetime import datetime
from typing import Dict, List

# ============ EOF 策略配置 ============
TRADING_STRATEGY = {
    "name": "EOF 策略 (Economic Output Factor)",
    "description": "经济产出因子策略",
    "status": "模拟中 ⚠️"
}

# ============ 模拟持仓 ⚠️ ============
# 注意：这是【模拟持仓】，用于策略回测
# 真实交易需要提供 Longbridge API 账号
SIMULATED_PORTFOLIO = {
    "QQQ": {
        "shares": 68,
        "target_price": 600.64,
        "status": "模拟持有 ⚠️"
    },
    "NVDA": {
        "shares": 54,
        "target_price": 186.94,
        "status": "模拟持有 ⚠️"
    },
    "TSLA": {
        "shares": 10,
        "target_price": 417.07,
        "status": "模拟持有 ⚠️"
    },
    "GOOGL": {
        "shares": 33,
        "target_price": 309.00,
        "status": "模拟持有 ⚠️"
    },
    "MSFT": {
        "shares": 25,
        "target_price": 401.84,
        "status": "模拟持有 ⚠️"
    }
}

# ============ 风控参数 ============
ALERT_LEVELS = {
    "stop_loss": -5.0,
    "take_profit": 10.0,
    "warning": -3.0,
    "opportunity": 5.0
}


def get_us_stock_price(symbol: str) -> Dict:
    """获取美股价格（真实价格，模拟仓位）"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            meta = data['chart']['result'][0]['meta']
            return {
                'symbol': symbol,
                'price': meta['regularMarketPrice'],
                'prev_close': meta['previousClose'],
                'status': 'success'
            }
        return {'symbol': symbol, 'status': 'error'}
    except Exception as e:
        return {'symbol': symbol, 'status': 'error', 'message': str(e)}


def calculate_metrics(holding: Dict, current_price: float) -> Dict:
    """计算指标"""
    target_price = holding['target_price']
    shares = holding['shares']
    
    unrealized_pct = (current_price - target_price) / target_price * 100
    unrealized_value = (current_price - target_price) * shares
    
    return {
        'current_price': current_price,
        'target_price': target_price,
        'unrealized_pct': unrealized_pct,
        'unrealized_value': unrealized_value
    }


def check_alert(metrics: Dict) -> List[str]:
    """检查警报"""
    alerts = []
    unrealized = metrics['unrealized_pct']
    
    if unrealized <= ALERT_LEVELS['stop_loss']:
        alerts.append("🔴 触发止损！")
    elif unrealized <= ALERT_LEVELS['warning']:
        alerts.append("⚠️ 接近止损线")
    elif unrealized >= ALERT_LEVELS['take_profit']:
        alerts.append("🟢 达到止盈！")
    
    return alerts


def analyze_portfolio() -> Dict:
    """分析模拟持仓"""
    print("\n" + "=" * 70)
    print("⚠️ EOF 策略模拟持仓分析")
    print("=" * 70)
    print("\n💡 提示: 这是模拟数据，用于策略回测")
    print("🔑 如需真实交易，请提供 Longbridge API 账号")
    print("-" * 70)
    
    results = {'holdings': [], 'summary': {}}
    total_unrealized = 0
    winning = 0
    
    print("\n📊 模拟持仓")
    print("-" * 70)
    
    for symbol, holding in SIMULATED_PORTFOLIO.items():
        price_data = get_us_stock_price(symbol)
        
        if price_data['status'] == 'success':
            current_price = price_data['price']
            metrics = calculate_metrics(holding, current_price)
            alerts = check_alert(metrics)
            
            total_unrealized += metrics['unrealized_value']
            if metrics['unrealized_pct'] > 0:
                winning += 1
            
            status = "🟢" if metrics['unrealized_pct'] > 0 else "🔴"
            
            print(f"{status} {symbol:<6} {holding['shares']:>3}股 "
                  f"${current_price:>8.2f} (目标 ${holding['target_price']:.2f}) "
                  f"{metrics['unrealized_pct']:>+6.2f}%")
            
            for alert in alerts:
                print(f"   {alert}")
            
            results['holdings'].append({
                'symbol': symbol,
                'current_price': current_price,
                'unrealized_pct': metrics['unrealized_pct'],
                'alerts': alerts
            })
    
    # 汇总
    print("\n" + "=" * 70)
    print("📈 模拟汇总")
    print("=" * 70)
    print(f"\n🎯 模拟盈亏: ${total_unrealized:,.2f}")
    print(f"📊 胜率: {winning}/{len(SIMULATED_PORTFOLIO)} ({winning/len(SIMULATED_PORTFOLIO)*100:.0f}%)")
    print("\n⚠️ 注意: 这是模拟数据，不代表真实收益")
    print("=" * 70)
    
    results['summary'] = {
        'total_unrealized': total_unrealized,
        'winning': winning,
        'is_simulated': True
    }
    
    return results


def main():
    """主函数"""
    result = analyze_portfolio()
    
    with open('/tmp/simulated_portfolio_report.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 模拟报告已保存")


if __name__ == "__main__":
    main()
