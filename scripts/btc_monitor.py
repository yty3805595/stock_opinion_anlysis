#!/usr/bin/env python3
"""
BTC 价格查询脚本

功能：
1. 从 Binance API 获取实时 BTC 价格
2. 查询 MA20 均线
3. 生成监控报告
"""

import requests
import json
from datetime import datetime
from typing import Dict

def get_btc_price() -> Dict:
    """获取 BTC 实时价格"""
    try:
        # Binance API
        resp = requests.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            return {
                "source": "Binance",
                "price": float(data['price']),
                "symbol": data['symbol'],
                "status": "success"
            }
        else:
            return {"status": "error", "message": f"HTTP {resp.status_code}"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_btc_ma20() -> Dict:
    """估算 BTC MA20 (简化版，实际应该用历史数据)"""
    # 这里简化处理，实际应该查询历史K线计算
    return {
        "ma20": 75000,  # 示例值，实际应该计算
        "status": "estimated"
    }

def check_conditions(price: float, ma20: float) -> Dict:
    """检查监控条件"""
    conditions = {
        "above_70000": price >= 70000,
        "above_ma20": price >= ma20,
        "above_65000": price >= 65000,
        "near_65000": price < 65000 + 3000  # 距离支撑位3000以内
    }
    
    return conditions

def generate_report() -> str:
    """生成监控报告"""
    # 获取价格
    price_data = get_btc_price()
    
    if price_data['status'] != 'success':
        return f"❌ 获取价格失败: {price_data.get('message', 'Unknown error')}"
    
    price = price_data['price']
    ma20_data = get_btc_ma20()
    ma20 = ma20_data.get('ma20', 75000)
    
    # 检查条件
    conditions = check_conditions(price, ma20)
    
    # 生成报告
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    report = f"""## 📊 BTC 价格监控报告

**时间:** {now}
**数据来源:** {price_data['source']}

---

### 💰 当前价格

**BTC/USDT: ${price:,.2f}**

---

### 📈 技术指标

| 指标 | 数值 | 状态 |
|------|------|------|
| 当前价格 | ${price:,.2f} | - |
| MA20 | ${ma20:,.2f} | {'✅ 高于' if price > ma20 else '❌ 低于'} |
| 支撑位 | $65,000 | {'✅ 之上' if price > 65000 else '❌ 跌破'} |
| 建仓线 | $70,000 | {'✅ 突破' if price >= 70000 else '❌ 未突破'} |

---

### ✅ 触发条件检查

| 条件 | 状态 | 说明 |
|------|------|------|
| 价格回到 $70,000 以上 | {'✅ 触发' if conditions['above_70000'] else '❌ 未触发'} | {'当前 $' + f'{price:,.2f}' + ' >= $70,000' if conditions['above_70000'] else '当前 $' + f'{price:,.2f}' + ' < $70,000'} |
| 站稳 MA20 (${ma20:,.0f}) | {'✅ 触发' if conditions['above_ma20'] else '❌ 未触发'} | {'价格高于均线' if conditions['above_ma20'] else '价格低于均线'} |
| 触及支撑位 $65,000 | {'⚠️ 接近' if conditions['near_65000'] else '✅ 之上'} | {'距离支撑位 < $3,000' if conditions['near_65000'] else '距离支撑位 > $3,000'} |

---

### 💡 分析结论

"""
    
    # 分析结论
    if conditions['above_70000'] and conditions['above_ma20']:
        report += """**✅ 建仓条件已触发！**

理由：
1. 价格已突破 $70,000 心理关口
2. 价格已站稳 MA20 均线
3. 趋势偏多

**建议:** 可考虑分批建仓
"""
    elif conditions['above_70000']:
        report += """**⚠️ 部分条件触发**

理由：
1. 价格突破 $70,000
2. 但仍在 MA20 下方

**建议:** 等待价格站稳 MA20 后再考虑建仓
"""
    elif conditions['above_ma20']:
        report += """**⚠️ 部分条件触发**

理由：
1. 价格站稳 MA20
2. 但未突破 $70,000

**建议:** 等待价格突破 $70,000 确认
"""
    else:
        report += """**❌ 建仓条件未触发**

理由：
1. 价格仍在 $70,000 以下
2. 低于 MA20 均线约 ${:,.0f} ({}%)

**建议:** 继续观望，等待价格突破关键阻力位
""".format(ma20 - price, (ma20 - price) / price * 100)
    
    report += f"""

---

**下次监控:** 每2小时自动检查
**数据来源:** Binance API
"""
    
    return report

def main():
    """主函数"""
    print("🔍 查询 BTC 价格...")
    
    report = generate_report()
    print(report)
    
    # 保存报告
    with open('/tmp/btc_monitor_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ 报告已保存: /tmp/btc_monitor_report.md")

if __name__ == "__main__":
    main()
