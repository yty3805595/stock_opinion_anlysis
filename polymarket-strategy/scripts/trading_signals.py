#!/usr/bin/env python3
"""
Polymarket 交易策略脚本

功能：
1. 获取市场信号
2. 分析概率和风险
3. 计算仓位
4. 生成交易建议
"""

import json
import sys
from datetime import datetime

# 高概率信号库
SIGNALS = {
    "government_shutdown": {
        "name": "政府周六关门",
        "slug": "government-shutdown",
        "probability": 96.8,
        "action": "NO",
        "min_investment": 10,
        "max_investment": 100,
        "expected_return": 0.03,
        "risk": 0.032,
        "category": "政治"
    },
    "btc_above_66000": {
        "name": "BTC 2/14 > $66,000",
        "slug": "btc-above-66000",
        "probability": 97.7,
        "action": "YES",
        "min_investment": 10,
        "max_investment": 100,
        "expected_return": 0.10,
        "risk": 0.024,
        "category": "加密货币"
    },
    "btc_above_85000": {
        "name": "BTC 2月 $85,000",
        "slug": "btc-85000",
        "probability": 96.0,
        "action": "NO",
        "min_investment": 10,
        "max_investment": 50,
        "expected_return": 0.04,
        "risk": 0.04,
        "category": "加密货币"
    },
    "fed_no_change": {
        "name": "Fed 3月不降息",
        "slug": "fed-no-change",
        "probability": 93.5,
        "action": "YES",
        "min_investment": 10,
        "max_investment": 50,
        "expected_return": 0.07,
        "risk": 0.065,
        "category": "金融"
    }
}

def calculate_position(signal, total_capital=1000):
    """计算仓位"""
    prob = signal['probability']
    
    if prob < 70:
        return 0
    
    # 仓位比例
    if prob > 90:
        max_pct = 0.10
    elif prob > 80:
        max_pct = 0.07
    else:
        max_pct = 0.05
    
    # 期望值
    expected_value = (prob/100) * signal['expected_return'] - ((100-prob)/100) * signal['risk']
    
    if expected_value <= 0:
        return 0
    
    return total_capital * max_pct

def analyze_signals():
    """分析所有信号"""
    results = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "strong_signals": [],
        "medium_signals": [],
        "no_trade": []
    }
    
    for key, signal in SIGNALS.items():
        position = calculate_position(signal)
        
        if signal['probability'] > 90:
            results["strong_signals"].append({
                **signal,
                "position": position,
                "signal": "🟢 强烈推荐"
            })
        elif signal['probability'] > 70:
            results["medium_signals"].append({
                **signal,
                "position": position,
                "signal": "🟡 谨慎参与"
            })
        else:
            results["no_trade"].append({
                **signal,
                "position": 0,
                "signal": "⚠️ 不建议"
            })
    
    return results

def generate_report(results):
    """生成报告"""
    report = f"""
============================================================
📊 Polymarket 交易信号报告
============================================================
时间: {results['timestamp']}
============================================================

🎯 强烈推荐 (>90%)

"""
    
    for s in results['strong_signals']:
        report += f"""
{s['name']}
  操作: 买 {s['action']}
  概率: {s['probability']}%
  仓位: ${s['position']:.2f}
  预期收益: {s['expected_return']*100:.1f}%
  风险: {s['risk']*100:.1f}%
  类别: {s['category']}
"""
    
    if results['medium_signals']:
        report += """
🟡 谨慎参与 (70-90%)

"""
        for s in results['medium_signals']:
            report += f"""
{s['name']}
  操作: 买 {s['action']}
  概率: {s['probability']}%
  仓位: ${s['position']:.2f}
  类别: {s['category']}
"""
    
    report += """
============================================================
⚠️ 风险提示
============================================================
1. 高概率不等于确定性
2. 预测市场有结算风险
3. 建议单笔不超过总资金 5%
4. 台湾用户避免选举类预测
============================================================
"""
    
    return report

def main():
    """主函数"""
    results = analyze_signals()
    report = generate_report(results)
    print(report)
    
    # 保存报告
    filename = f"/tmp/polymarket_signals_{datetime.now().strftime('%Y%m%d')}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 报告已保存: {filename}")

if __name__ == "__main__":
    main()
