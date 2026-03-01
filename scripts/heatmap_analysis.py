#!/usr/bin/env python3
"""
TradingView 策略移植：交易时段热力图分析

功能：
1. 分析不同时间段的历史交易量/波动率
2. 生成热力图可视化
3. 识别最佳交易时段
4. 辅助策略参数优化
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

import numpy as np

# ============ 配置 ============
CONFIG = {
    "symbol": "BTC.USDT",
    "data_type": "volume",  # volume 或 volatility
    "timeframe": "1h",  # K 线周期
    "lookback_days": 30,  # 分析过去多少天
    
    # 微信公众号文章关键词
    "wechat_keywords": ["量化", "机器学习", "深度学习", "AI"],
}


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataType(Enum):
    """数据类型"""
    VOLUME = "volume"
    VOLATILITY = "volatility"


@dataclass
class TimeBucket:
    """时间段数据"""
    hour: int  # 0-23
    day_of_week: int  # 0-6 (周一到周日)
    values: List[float] = field(default_factory=list)
    
    @property
    def median(self) -> float:
        return np.median(self.values) if self.values else 0.0
    
    @property
    def mean(self) -> float:
        return np.mean(self.values) if self.values else 0.0
    
    @property
    def std(self) -> float:
        return np.std(self.values) if self.values else 0.0
    
    @property
    def max(self) -> float:
        return max(self.values) if self.values else 0.0
    
    @property
    def min(self) -> float:
        return min(self.values) if self.values else 0.0


class TradingHeatmap:
    """
    交易时段热力图分析
    
    分析不同时间段的数据分布：
    - 按小时统计 (0-23)
    - 按星期统计 (周一到周日)
    - 按月份统计 (1-12)
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.symbol = config["symbol"]
        self.data_type = config.get("data_type", "volume")
        
        # 存储时间维度数据
        self.hourly_data: Dict[int, List[float]] = defaultdict(list)  # 0-23
        self.daily_data: Dict[int, List[float]] = defaultdict(list)  # 0-6
        self.monthly_data: Dict[int, List[float]] = defaultdict(list)  # 1-12
        
        # 原始数据
        self.timestamps: List[datetime] = []
        self.highs: List[float] = []
        self.lows: List[float] = []
        self.closes: List[float] = []
        self.volumes: List[float] = []
        
    def add_candle(self, high: float, low: float, close: float, volume: float, timestamp: datetime):
        """添加一根 K 线"""
        self.highs.append(high)
        self.lows.append(low)
        self.closes.append(close)
        self.volumes.append(volume)
        self.timestamps.append(timestamp)
        
        # 计算波动率 (True Range)
        if len(self.closes) > 1:
            tr = max(
                high - low,
                abs(high - self.closes[-2]),
                abs(low - self.closes[-2])
            )
            volatility = tr / close * 100  # 百分比
        else:
            volatility = 0.0
        
        value = volume if self.data_type == "volume" else volatility
        
        # 按小时分类
        hour = timestamp.hour
        self.hourly_data[hour].append(value)
        
        # 按星期分类 (Pandas: Monday=0)
        day_of_week = timestamp.weekday()
        self.daily_data[day_of_week].append(value)
        
        # 按月份分类
        month = timestamp.month
        self.monthly_data[month].append(value)
    
    def calculate_hourly_stats(self) -> Dict[int, Dict]:
        """计算每小时统计"""
        stats = {}
        for hour in range(24):
            values = self.hourly_data.get(hour, [])
            if values:
                stats[hour] = {
                    "median": np.median(values),
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "max": max(values),
                    "min": min(values),
                    "count": len(values)
                }
        return stats
    
    def calculate_daily_stats(self) -> Dict[int, Dict]:
        """计算每天统计"""
        stats = {}
        day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for day in range(7):
            values = self.daily_data.get(day, [])
            if values:
                stats[day] = {
                    "name": day_names[day],
                    "median": np.median(values),
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "max": max(values),
                    "min": min(values),
                    "count": len(values)
                }
        return stats
    
    def calculate_monthly_stats(self) -> Dict[int, Dict]:
        """计算每月统计"""
        stats = {}
        month_names = ["1月", "2月", "3月", "4月", "5月", "6月", 
                       "7月", "8月", "9月", "10月", "11月", "12月"]
        for month in range(1, 13):
            values = self.monthly_data.get(month, [])
            if values:
                stats[month] = {
                    "name": month_names[month - 1],
                    "median": np.median(values),
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "max": max(values),
                    "min": min(values),
                    "count": len(values)
                }
        return stats
    
    def get_best_hours(self, top_n: int = 3) -> List[Tuple[int, float]]:
        """获取最佳交易时段 (交易量/波动率最高)"""
        stats = self.calculate_hourly_stats()
        sorted_hours = sorted(stats.items(), key=lambda x: x[1]["median"], reverse=True)
        return [(hour, data["median"]) for hour, data in sorted_hours[:top_n]]
    
    def get_worst_hours(self, bottom_n: int = 3) -> List[Tuple[int, float]]:
        """获取最差交易时段"""
        stats = self.calculate_hourly_stats()
        sorted_hours = sorted(stats.items(), key=lambda x: x[1]["median"])
        return [(hour, data["median"]) for hour, data in sorted_hours[:bottom_n]]
    
    def get_best_days(self, top_n: int = 3) -> List[Tuple[int, float]]:
        """获取最佳交易日期"""
        stats = self.calculate_daily_stats()
        sorted_days = sorted(stats.items(), key=lambda x: x[1]["median"], reverse=True)
        return [(day, data["median"]) for day, data in sorted_days[:top_n]]
    
    def get_best_months(self, top_n: int = 3) -> List[Tuple[int, float]]:
        """获取最佳交易月份"""
        stats = self.calculate_monthly_stats()
        sorted_months = sorted(stats.items(), key=lambda x: x[1]["median"], reverse=True)
        return [(month, data["median"]) for month, data in sorted_months[:top_n]]
    
    def generate_heatmap_data(self) -> Dict:
        """生成热力图数据"""
        hourly_stats = self.calculate_hourly_stats()
        daily_stats = self.calculate_daily_stats()
        
        # 获取所有值的范围
        all_values = []
        for hour_data in hourly_stats.values():
            all_values.append(hour_data["median"])
        for day_data in daily_stats.values():
            all_values.append(day_data["median"])
        
        if not all_values:
            return {}
        
        min_val = min(all_values)
        max_val = max(all_values)
        value_range = max_val - min_val if max_val != min_val else 1
        
        # 生成热力图矩阵 (7天 x 24小时)
        heatmap = []
        for day in range(7):
            row = []
            for hour in range(24):
                # 获取该时段的值
                hour_val = hourly_stats.get(hour, {}).get("median", 0)
                day_val = daily_stats.get(day, {}).get("median", 0)
                
                # 综合评分
                combined = (hour_val + day_val) / 2
                
                # 归一化到 0-100
                normalized = (combined - min_val) / value_range * 100
                row.append(normalized)
            heatmap.append(row)
        
        return {
            "heatmap": heatmap,
            "hourly": hourly_stats,
            "daily": daily_stats,
            "min": min_val,
            "max": max_val
        }
    
    def generate_report(self) -> str:
        """生成分析报告"""
        hourly = self.calculate_hourly_stats()
        daily = self.calculate_daily_stats()
        monthly = self.calculate_monthly_stats()
        
        best_hours = self.get_best_hours(3)
        best_days = self.get_best_days(3)
        best_months = self.get_best_months(3)
        
        data_type = "交易量" if self.data_type == "volume" else "波动率"
        
        report = f"""
📊 交易时段热力图分析报告
{'=' * 60}

**分析时间:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**交易品种:** {self.symbol}
**数据类型:** {data_type}
**K线周期:** {self.config.get('timeframe', '1h')}

---

## 🕐 最佳交易时段 (按 {data_type})

### 🏆 Top 3 小时
| 时间 | {data_type} |
|------|-------------|
"""
        
        for hour, value in best_hours:
            report += f"| {hour:02d}:00 | {value:,.0f} |\n"
        
        report += f"""
### 🏆 Top 3 星期
| 星期 | {data_type} |
|------|-------------|
"""
        
        for day, value in best_days:
            day_name = daily.get(day, {}).get("name", f"星期{day+1}")
            report += f"| {day_name} | {value:,.0f} |\n"
        
        report += f"""
### 🏆 Top 3 月份
| 月份 | {data_type} |
|------|-------------|
"""
        
        for month, value in best_months:
            month_name = monthly.get(month, {}).get("name", f"{month}月")
            report += f"| {month_name} | {value:,.0f} |\n"
        
        report += f"""
---

## 📈 各时段详细数据

### 小时数据
| 小时 | 中位数 | 平均值 | 标准差 | 样本数 |
|------|--------|--------|--------|--------|
"""
        
        for hour in range(24):
            if hour in hourly:
                h = hourly[hour]
                report += f"| {hour:02d}:00 | {h['median']:,.0f} | {h['mean']:,.0f} | {h['std']:,.0f} | {h['count']} |\n"
        
        report += f"""
### 星期数据
| 星期 | 中位数 | 平均值 | 标准差 | 样本数 |
|------|--------|--------|--------|--------|
"""
        
        day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for day in range(7):
            if day in daily:
                d = daily[day]
                report += f"| {day_names[day]} | {d['median']:,.0f} | {d['mean']:,.0f} | {d['std']:,.0f} | {d['count']} |\n"
        
        report += f"""
---

## 🎯 策略建议

### 1. 择时建议
- **最佳交易时段:** {best_hours[0][0]:02d}:00 - {best_hours[0][0]+2:02d}:00
- **最佳交易日期:** {daily.get(best_days[0][0], {}).get('name', 'N/A')}
- **最佳交易月份:** {monthly.get(best_months[0][0], {}).get('name', 'N/A')}

### 2. 波动率交易
- 高波动时段适合: 突破交易、期权交易
- 低波动时段适合: 区间交易、现货买入

### 3. 交易量优化
- 高交易量时段适合: 大额交易、流动性好
- 低交易量时段可能出现: 滑点大、价差大

---

## 💡 实际应用

1. **策略参数优化**
   - 根据最佳时段调整策略参数
   - 在活跃时段使用激进策略
   
2. **风险管理**
   - 在高波动时段控制仓位
   - 止损位根据波动率调整

3. **订单执行**
   - 在高交易量时段执行大额订单
   - 避免在低流动性时段交易

"""
        
        return report
    
    def get_color_gradient(self, value: float, min_val: float, max_val: float) -> str:
        """获取颜色渐变 (热力图用)"""
        if max_val == min_val:
            return "#808080"
        
        normalized = (value - min_val) / (max_val - min_val)
        
        # Viridis 风格颜色映射
        if normalized < 0.25:
            # 深紫 -> 紫
            r = int(64 + (85 - 64) * normalized * 4)
            g = int(10)
            b = int(83 + (142 - 83) * normalized * 4)
        elif normalized < 0.5:
            # 紫 -> 青
            r = int(85 + (72 - 85) * (normalized - 0.25) * 4)
            g = int(10 + (142 - 10) * (normalized - 0.25) * 4)
            b = int(142 + (139 - 142) * (normalized - 0.25) * 4)
        elif normalized < 0.75:
            # 青 -> 黄
            r = int(72 + (241 - 72) * (normalized - 0.5) * 4)
            g = int(142 + (247 - 142) * (normalized - 0.5) * 4)
            b = int(139 + (85 - 139) * (normalized - 0.5) * 4)
        else:
            # 黄 -> 亮黄
            r = int(241 + (252 - 241) * (normalized - 0.75) * 4)
            g = int(247 + (252 - 247) * (normalized - 0.75) * 4)
            b = int(85 + (254 - 85) * (normalized - 0.75) * 4)
        
        return f"#{r:02x}{g:02x}{b:02x}"


def generate_html_heatmap(heatmap_data: Dict) -> str:
    """生成 HTML 热力图"""
    heatmap = heatmap_data.get("heatmap", [])
    hourly = heatmap_data.get("hourly", {})
    daily = heatmap_data.get("daily", {})
    
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    hour_labels = [f"{h:02d}:00" for h in range(24)]
    
    min_val = heatmap_data.get("min", 0)
    max_val = heatmap_data.get("max", 1)
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>交易时段热力图</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #4CAF50; color: white; }}
        .heatmap-cell {{ min-width: 30px; height: 30px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; }}
        .legend {{ display: flex; align-items: center; margin: 10px 0; }}
        .legend-box {{ width: 30px; height: 20px; margin-right: 5px; }}
    </style>
</head>
<body>
    <h1>📊 交易时段热力图</h1>
    <p>分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    
    <h2>热力图 (行=星期, 列=小时)</h2>
    <table>
        <tr>
            <th></th>
            {"".join(f'<th>{h}</th>' for h in hour_labels)}
        </tr>
"""
    
    for day_idx, day_name in enumerate(day_names):
        html += f'<tr><th>{day_name}</th>'
        for hour_idx in range(24):
            value = heatmap[day_idx][hour_idx] if day_idx < len(heatmap) and hour_idx < len(heatmap[day_idx]) else 0
            color = f"#{int(40 + (215-40)*value/100):02x}{int(10 + (215-10)*value/100):02x}{int(83 + (190-83)*value/100):02x}"
            html += f'<td class="heatmap-cell" style="background-color: {color}" title="{day_name} {hour_idx}:00 - 值: {value:.1f}">{value:.0f}</td>'
        html += '</tr>'
    
    html += """
    </table>
    
    <div class="legend">
        <span>低: </span>
        <div class="legend-box" style="background-color: #280a53;"></div>
        <span>中: </span>
        <div class="legend-box" style="background-color: #488e8b;"></div>
        <span>高: </span>
        <div class="legend-box" style="background-color: #f8e650;"></div>
    </div>
    
</body>
</html>
"""
    
    return html


def main():
    """主函数 - 测试"""
    import random
    
    # 创建热力图分析器
    heatmap = TradingHeatmap(CONFIG)
    
    # 模拟数据
    print("📊 模拟 K 线数据...")
    
    base_price = 67000.0
    base_volume = 5000.0
    
    # 生成 30 天的数据
    for day in range(30):
        for hour in range(24):
            # 模拟价格波动
            price_change = random.uniform(-0.02, 0.03)
            close = base_price * (1 + price_change)
            high = close * random.uniform(1.0, 1.02)
            low = close * random.uniform(0.98, 1.0)
            
            # 模拟交易量 (美国时段更高)
            if 21 <= hour or hour < 4:  # 美国时段
                volume = base_volume * random.uniform(1.5, 2.5)
            else:
                volume = base_volume * random.uniform(0.5, 1.5)
            
            # 添加周末效应
            if day % 7 in [5, 6]:
                volume *= 0.7
            
            timestamp = datetime.now() - timedelta(days=30-day, hours=hour)
            
            heatmap.add_candle(high, low, close, volume, timestamp)
    
    # 生成报告
    print("📈 生成分析报告...")
    report = heatmap.generate_report()
    print(report)
    
    # 保存报告
    with open('/tmp/heatmap_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ 报告已保存: /tmp/heatmap_report.md")
    
    # 生成 HTML 热力图
    heatmap_data = heatmap.generate_heatmap_data()
    html = generate_html_heatmap(heatmap_data)
    
    with open('/tmp/heatmap.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML 热力图已保存: /tmp/heatmap.html")


if __name__ == "__main__":
    main()
