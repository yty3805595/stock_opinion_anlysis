#!/usr/bin/env python3
"""
加密货币与 MSTR 分析系统

目标：
1. MicroStrategy (MSTR) 关联分析
2. 比特币走势分析
3. Polymarket 预测市场研究
4. 套利机会识别
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional

# 配置
MSTR_API = {
    'finnhub': os.getenv('FINNHUB_API_KEY', ''),
    'yahoo': 'MSTR'  # Yahoo Finance
}

BTC_API = {
    'binance': 'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT',
    'coingecko': 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true'
}


def get_btc_price() -> Dict:
    """获取比特币价格"""
    try:
        # CoinGecko API (免费，无需 key)
        resp = requests.get(BTC_API['coingecko'], timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                'source': 'CoinGecko',
                'price': data['bitcoin']['usd'],
                'change_24h': data['bitcoin']['usd_24h_change']
            }
    except Exception as e:
        print(f"❌ 获取 BTC 价格失败: {e}")
    
    return None


def get_mstr_info() -> Dict:
    """获取 MSTR 信息"""
    try:
        # 使用 Yahoo Finance
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{MSTR_API['yahoo']}"
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                result = data['chart']['result'][0]
                meta = result['meta']
                
                return {
                    'symbol': 'MSTR',
                    'price': meta.get('regularMarketPrice'),
                    'change': meta.get('regularMarketChangePercent'),
                    'volume': meta.get('regularMarketVolume'),
                    'timestamp': datetime.fromtimestamp(meta.get('regularMarketTime', 0)).strftime('%Y-%m-%d %H:%M:%S')
                }
    except Exception as e:
        print(f"❌ 获取 MSTR 信息失败: {e}")
    
    return None


def analyze_mstr_btc_correlation() -> Dict:
    """分析 MSTR 与 BTC 的关联性"""
    btc = get_btc_price()
    mstr = get_mstr_info()
    
    if not btc or not mstr:
        return {
            'status': 'failed',
            'error': '无法获取数据'
        }
    
    return {
        'status': 'success',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'btc': btc,
        'mstr': mstr,
        'correlation_analysis': {
            'mstr_btc_exposure': 'MicroStrategy 持有大量 BTC',
            'strategy': '通过 MSTR 间接持有 BTC，同时获得股票敞口',
            'premium': 'MSTR vs BTC 溢价分析需要更多数据'
        }
    }


def get_polymarket_info() -> Dict:
    """获取 Polymarket 信息"""
    # Polymarket 是预测市场，主要通过事件概率交易
    # API: https://api.polymarket.com/
    
    try:
        # 获取热门市场
        url = "https://api.polymarket.com/markets?limit=10&order=volume&ascending=false"
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            return {
                'status': 'success',
                'markets': data[:5] if isinstance(data, list) else []
            }
    except Exception as e:
        pass
    
    return {
        'status': 'info',
        'message': 'Polymarket 数据需要进一步开发',
        'url': 'https://polymarket.com/',
        'strategy': '事件驱动交易，预测概率与实际结果'
    }


def identify_arbitrage() -> List[Dict]:
    """识别套利机会"""
    opportunities = []
    
    # 1. MSTR vs BTC 套利
    analysis = analyze_mstr_btc_correlation()
    if analysis['status'] == 'success':
        opportunities.append({
            'type': 'MSTR vs BTC',
            'description': '通过持有 MSTR 获得 BTC 敞口',
            'status': '需要更多数据',
            'risk': '中等',
            'action': '等待研究员完成深度分析'
        })
    
    # 2. 跨交易所套利
    opportunities.append({
        'type': '跨交易所',
        'description': '币安 vs Coinbase 比特币价差',
        'status': '需要交易所 API',
        'risk': '低',
        'action': '配置交易所 API'
    })
    
    # 3. Polymarket 套利
    opportunities.append({
        'type': '预测市场',
        'description': '事件概率 vs 实际结果',
        'status': '研究中',
        'risk': '中高',
        'action': '等待研究员完成分析'
    })
    
    return opportunities


def generate_report() -> str:
    """生成分析报告"""
    btc = get_btc_price()
    mstr = get_mstr_info()
    polymarket = get_polymarket_info()
    arbitrage = identify_arbitrage()
    
    report = f"""# 📊 加密货币与 MSTR 分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} GMT+8

---

## 🌟 核心标的

### 1. MicroStrategy (MSTR)

**状态**: {'✅ 数据获取成功' if mstr else '❌ 数据获取失败'}

"""

    if mstr:
        report += f"""| 指标 | 数值 |
|------|------|
| 价格 | ${mstr.get('price', 'N/A')} |
| 涨跌幅 | {mstr.get('change', 'N/A')}% |
| 成交量 | {mstr.get('volume', 'N/A'):,} |
| 更新时间 | {mstr.get('timestamp', 'N/A')} |

**策略**: MSTR 持有大量 BTC，通过股票账户间接持有 BTC敞口

"""

    report += f"""### 2. 比特币 (BTC)

**状态**: {'✅ 数据获取成功' if btc else '❌ 数据获取失败'}

"""

    if btc:
        report += f"""| 指标 | 数值 |
|------|------|
| 价格 | ${btc['price']:,} |
| 24h 涨跌 | {btc['change_24h']:.2f}% |
| 数据源 | {btc['source']} |

"""

    report += f"""### 3. Polymarket (预测市场)

**状态**: {polymarket['status']}

**说明**: {polymarket.get('message', '数据获取成功')}

---

## 🎯 套利机会

"""

    for i, opp in enumerate(arbitrage, 1):
        report += f"""### {i}. {opp['type']}

- **描述**: {opp['description']}
- **状态**: {opp['status']}
- **风险**: {opp['risk']}
- **建议**: {opp['action']}

"""

    report += f"""---

## 📋 Agent 任务

### Researcher
- [ ] MSTR 深度研究报告
- [ ] Polymarket 机制研究

### Analyst
- [ ] MSTR vs BTC 相关性分析
- [ ] 加密货币市场概览

### Astra
- [ ] MSTR 交易策略
- [ ] 套利策略框架

---

## 🎯 月收益目标

| 策略 | 预期月收益 |
|------|-----------|
| MSTR 趋势 | 3-5% |
| Polymarket | 2-5% |
| 套利 | 0.5-1% |
| **合计** | **5.5-11%** |

---

*报告由 OpenClaw Agent Team 自动生成*
"""
    
    return report


def main():
    """主函数"""
    print("=" * 80)
    print("📊 加密货币与 MSTR 分析系统")
    print("=" * 80)
    
    print("\n🔍 分析 MSTR...")
    mstr = get_mstr_info()
    if mstr:
        print(f"✅ MSTR: ${mstr.get('price', 'N/A')}")
    else:
        print("❌ MSTR 数据获取失败")
    
    print("\n🔍 分析 BTC...")
    btc = get_btc_price()
    if btc:
        print(f"✅ BTC: ${btc['price']:,} ({btc['change_24h']:.2f}%)")
    else:
        print("❌ BTC 数据获取失败")
    
    print("\n🔍 分析 Polymarket...")
    polymarket = get_polymarket_info()
    print(f"   Status: {polymarket['status']}")
    
    # 生成报告
    report = generate_report()
    
    # 保存报告
    filename = f"github_reports/crypto_mstr_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ 报告已保存: {filename}")
    
    # 打印报告预览
    print("\n" + "=" * 80)
    print("📄 报告预览")
    print("=" * 80)
    print(report[:1000] + "...")


if __name__ == "__main__":
    main()
