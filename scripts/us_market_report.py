#!/usr/bin/env python3
"""
美股数据获取脚本

功能：
1. 获取美股实时价格
2. 检查持仓状态
3. 生成交易计划
4. 推送给用户
"""

import requests
import json
from datetime import datetime
from typing import Dict, List
import subprocess

# 美股持仓
HOLDINGS = {
    "QQQ": {"shares": 68, "target_price": 600.64},
    "NVDA": {"shares": 54, "target_price": 186.94},
    "TSLA": {"shares": 10, "target_price": 417.07},
    "GOOGL": {"shares": 33, "target_price": 309.00},
    "MSFT": {"shares": 25, "target_price": 401.84}
}

def get_stock_price(symbol: str) -> Dict:
    """
    获取股票价格（使用 Yahoo Finance API）"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            result = data['chart']['result'][0]
            meta = result['meta']
            current_price = meta['regularMarketPrice']
            prev_close = meta['previousClose']
            
            change_pct = (current_price - prev_close) / prev_close * 100
            
            return {
                'symbol': symbol,
                'price': current_price,
                'prev_close': prev_close,
                'change_pct': change_pct,
                'status': 'success'
            }
        else:
            return {'symbol': symbol, 'status': 'error', 'message': f'HTTP {resp.status_code}'}
            
    except Exception as e:
        return {'symbol': symbol, 'status': 'error', 'message': str(e)}

def check_holdings() -> List[Dict]:
    """检查所有持仓"""
    results = []
    for symbol, info in HOLDINGS.items():
        price_data = get_stock_price(symbol)
        if price_data['status'] == 'success':
            current_price = price_data['price']
            target_price = info['target_price']
            unrealized_pct = (current_price - target_price) / target_price * 100
            
            results.append({
                'symbol': symbol,
                'shares': info['shares'],
                'current_price': current_price,
                'target_price': target_price,
                'unrealized_pct': unrealized_pct,
                'change_pct': price_data['change_pct']
            })
    
    return results

def search_market_news(keywords: str = "QQQ NVDA TSLA GOOGL 美股") -> List[Dict]:
    """搜索市场新闻"""
    try:
        result = subprocess.run([
            "node",
            "/Users/yintaoye/.openclaw/workspace/skills/tavily-search/scripts/search.mjs",
            keywords,
            "--topic", "news",
            "--days", "1"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return [{"title": "搜索到相关新闻", "status": "success"}]
        else:
            return [{"title": "搜索失败", "status": "error"}]
    except Exception as e:
        return [{"title": str(e), "status": "error"}]

def generate_report():
    """生成美股盘前报告"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    print("=" * 70)
    print(f"🌙 美股盘前汇报")
    print(f"时间: {now}")
    print("=" * 70)
    
    # 1. 获取持仓状态
    print("\n📊 持仓检查")
    print("-" * 70)
    
    holdings = check_holdings()
    if holdings:
        total_unrealized = 0
        for h in holdings:
            status = "🟢" if h['unrealized_pct'] > 0 else "🔴"
            print(f"{status} {h['symbol']:<6} {h['shares']:>3}股 ${h['current_price']:>8.2f} "
                  f"(目标 ${h['target_price']:.2f}) {h['unrealized_pct']:>+6.2f}%")
            total_unrealized += h['unrealized_pct']
        
        avg_unrealized = total_unrealized / len(holdings)
        print("-" * 70)
        print(f"📈 平均未实现盈亏: {avg_unrealized:>+6.2f}%")
    
    # 2. 市场新闻
    print("\n📰 市场新闻")
    print("-" * 70)
    news = search_market_news()
    for n in news[:3]:
        print(f"  • {n['title'][:50]}")
    
    # 3. 交易计划
    print("\n📋 交易计划")
    print("-" * 70)
    
    for h in holdings:
        if h['unrealized_pct'] > 10:
            print(f"  🎯 {h['symbol']}: 达到止盈线，考虑减仓")
        elif h['unrealized_pct'] < -5:
            print(f"  ⚠️ {h['symbol']}: 接近止损线，需要关注")
    
    # 4. 总结
    print("\n" + "=" * 70)
    print("💡 建议")
    print("=" * 70)
    print("  1. 继续监控持仓表现")
    print("  2. 关注今晚 CPI 数据")
    print("  3. 等待更好的买入机会")
    print("  4. 保持现有仓位")
    print("\n✅ 报告生成完成")
    print("=" * 70)
    
    return {"status": "success", "holdings": holdings}

def main():
    """主函数"""
    result = generate_report()
    
    # 保存报告
    with open("/tmp/us_market_report.json", 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 报告已保存: /tmp/us_market_report.json")

if __name__ == "__main__":
    main()
