#!/usr/bin/env python3
"""
双顶/双底形态识别 - 简化版

功能：
1. 识别双顶 (Double Top) 和双底 (Double Bottom) 形态
2. 简单的形态检测算法
3. 可视化形态结构
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

# ============ 配置 ============
CONFIG = {
    "symbol": "BTC.USDT",
    "tolerance": 0.10,  # 容差 10%
    "min_distance_bars": 5,  # 两个顶/底之间的最小 K 线数
    "target_ratio": 1.0,  # 目标比例
}


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Candle:
    """K 线数据"""
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime


class DoublePatternDetector:
    """
    简化的双顶/双底检测器
    
    核心思路：
    1. 找到最近的 N 个局部极值点
    2. 检查是否有两个相近的高点 (双顶) 或低点 (双底)
    3. 确认颈线位置
    4. 检查是否突破颈线
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.tolerance = config.get("tolerance", 0.10)
        self.min_distance = config.get("min_distance_bars", 5)
        self.target_ratio = config.get("target_ratio", 1.0)
        
        self.candles: List[Candle] = []
        
    def add_candle(self, high: float, low: float, close: float, volume: float, timestamp: datetime):
        """添加 K 线"""
        self.candles.append(Candle(high, low, close, volume, timestamp))
        
        # 只保留最近的 100 根 K 线
        if len(self.candles) > 100:
            self.candles = self.candles[-100:]
    
    def find_local_extrema(self, window: int = 5) -> Tuple[List[int], List[int]]:
        """
        找到局部极值点的索引
        
        Returns:
            highs_idx: 局部高点索引列表
            lows_idx: 局部低点索引列表
        """
        highs_idx = []
        lows_idx = []
        
        for i in range(window, len(self.candles) - window):
            # 检查是否为局部高点
            is_high = True
            for j in range(i - window, i + window + 1):
                if j != i and self.candles[j].high >= self.candles[i].high:
                    is_high = False
                    break
            
            if is_high:
                highs_idx.append(i)
            
            # 检查是否为局部低点
            is_low = True
            for j in range(i - window, i + window + 1):
                if j != i and self.candles[j].low <= self.candles[i].low:
                    is_low = False
                    break
            
            if is_low:
                lows_idx.append(i)
        
        return highs_idx, lows_idx
    
    def detect_double_top(self, highs_idx: List[int]) -> Optional[Dict]:
        """检测双顶形态"""
        if len(highs_idx) < 2:
            return None
        
        # 获取最近的高点
        recent_highs = highs_idx[-5:]  # 最近 5 个
        
        for i in range(len(recent_highs) - 1):
            idx1 = recent_highs[i]
            idx2 = recent_highs[i + 1]
            
            # 检查距离
            if idx2 - idx1 < self.min_distance:
                continue
            
            price1 = self.candles[idx1].high
            price2 = self.candles[idx2].high
            
            # 检查价格是否接近
            avg_price = (price1 + price2) / 2
            diff = abs(price1 - price2) / avg_price
            
            if diff > self.tolerance:
                continue
            
            # 找到两个高点之间的最低点 (颈线)
            neckline_idx = idx1
            neckline_low = self.candles[idx1].low
            for j in range(idx1 + 1, idx2):
                if self.candles[j].low < neckline_low:
                    neckline_low = self.candles[j].low
                    neckline_idx = j
            
            # 检查当前价格是否跌破颈线
            current_price = self.candles[-1].close
            current_low = self.candles[-1].low
            
            if current_low <= neckline_low:
                # 形态确认
                height = avg_price - neckline_low
                target = neckline_low - height * self.target_ratio
                stop_loss = max(price1, price2)
                
                return {
                    "pattern": "double_top",
                    "confidence": 1.0 - diff,
                    "pivot1": {"index": idx1, "price": price1, "time": self.candles[idx1].timestamp},
                    "pivot2": {"index": idx2, "price": price2, "time": self.candles[idx2].timestamp},
                    "neckline": {"index": neckline_idx, "price": neckline_low},
                    "target": target,
                    "stop_loss": stop_loss,
                    "break_point": len(self.candles) - 1,
                    "confirmed": True
                }
        
        return None
    
    def detect_double_bottom(self, lows_idx: List[int]) -> Optional[Dict]:
        """检测双底形态"""
        if len(lows_idx) < 2:
            return None
        
        # 获取最近的低点
        recent_lows = lows_idx[-5:]
        
        for i in range(len(recent_lows) - 1):
            idx1 = recent_lows[i]
            idx2 = recent_lows[i + 1]
            
            # 检查距离
            if idx2 - idx1 < self.min_distance:
                continue
            
            price1 = self.candles[idx1].low
            price2 = self.candles[idx2].low
            
            # 检查价格是否接近
            avg_price = (price1 + price2) / 2
            diff = abs(price1 - price2) / avg_price
            
            if diff > self.tolerance:
                continue
            
            # 找到两个低点之间的最高点 (颈线)
            neckline_idx = idx1
            neckline_high = self.candles[idx1].high
            for j in range(idx1 + 1, idx2):
                if self.candles[j].high > neckline_high:
                    neckline_high = self.candles[j].high
                    neckline_idx = j
            
            # 检查当前价格是否突破颈线
            current_price = self.candles[-1].close
            current_high = self.candles[-1].high
            
            if current_high >= neckline_high:
                # 形态确认
                height = neckline_high - avg_price
                target = neckline_high + height * self.target_ratio
                stop_loss = min(price1, price2)
                
                return {
                    "pattern": "double_bottom",
                    "confidence": 1.0 - diff,
                    "pivot1": {"index": idx1, "price": price1, "time": self.candles[idx1].timestamp},
                    "pivot2": {"index": idx2, "price": price2, "time": self.candles[idx2].timestamp},
                    "neckline": {"index": neckline_idx, "price": neckline_high},
                    "target": target,
                    "stop_loss": stop_loss,
                    "break_point": len(self.candles) - 1,
                    "confirmed": True
                }
        
        return None
    
    def analyze(self) -> Dict:
        """分析当前形态"""
        highs_idx, lows_idx = self.find_local_extrema(window=5)
        
        # 先检测双顶
        double_top = self.detect_double_top(highs_idx)
        if double_top:
            return double_top
        
        # 再检测双底
        double_bottom = self.detect_double_bottom(lows_idx)
        if double_bottom:
            return double_bottom
        
        return {
            "pattern": None,
            "confidence": 0.0,
            "message": "未检测到双顶/双底形态"
        }
    
    def get_signal(self) -> Dict:
        """获取交易信号"""
        result = self.analyze()
        
        if result["pattern"] == "double_top":
            return {
                "signal": "short",
                "action": "sell",
                "entry": result["neckline"]["price"],
                "target": result["target"],
                "stop_loss": result["stop_loss"],
                "confidence": result["confidence"],
                "pattern": "双顶"
            }
        
        elif result["pattern"] == "double_bottom":
            return {
                "signal": "long",
                "action": "buy",
                "entry": result["neckline"]["price"],
                "target": result["target"],
                "stop_loss": result["stop_loss"],
                "confidence": result["confidence"],
                "pattern": "双底"
            }
        
        return {
            "signal": "none",
            "action": None,
            "entry": None,
            "target": None,
            "stop_loss": None,
            "confidence": 0.0,
            "pattern": None
        }


def generate_report(detector: DoublePatternDetector, signal: Dict) -> str:
    """生成报告"""
    report = f"""
📊 双顶/双底形态分析报告
{'=' * 60}

**分析时间:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**K线数量:** {len(detector.candles)}

---

## 🎯 形态识别结果

**信号:** {signal['signal'].upper() if signal['signal'] != 'none' else '无信号'}
**形态:** {signal.get('pattern', 'N/A')}
**置信度:** {signal.get('confidence', 0) * 100:.1f}%

---

## 📈 交易参数

| 参数 | 数值 |
|------|------|
| **入场价** | {signal.get('entry', 'N/A'):.2f}" if signal.get('entry') else "**入场价** | N/A
| **目标价** | {signal.get('target', 'N/A'):.2f}" if signal.get('target') else "**目标价** | N/A
| **止损价** | {signal.get('stop_loss', 'N/A'):.2f}" if signal.get('stop_loss') else "**止损价** | N/A

---

"""
    
    if signal["signal"] == "short":
        report += "🔴 **双顶形态确认 - 建议做空**\n"
        report += f"- 颈线: {signal['entry']:.2f}\n"
        report += f"- 目标: {signal['target']:.2f}\n"
        report += f"- 止损: {signal['stop_loss']:.2f}\n"
    elif signal["signal"] == "long":
        report += "🟢 **双底形态确认 - 建议做多**\n"
        report += f"- 颈线: {signal['entry']:.2f}\n"
        report += f"- 目标: {signal['target']:.2f}\n"
        report += f"- 止损: {signal['stop_loss']:.2f}\n"
    else:
        report += "⚠️ **暂无形态信号**\n"
    
    return report


def main():
    """主函数 - 测试"""
    import random
    from datetime import timedelta
    
    # 创建检测器
    detector = DoublePatternDetector(CONFIG)
    
    print("📊 模拟 K 线数据...")
    
    # 生成明显的双底形态
    base_price = 67000.0
    
    # 阶段 1: 下跌
    for i in range(20):
        price = base_price - i * 150
        high = price + 100
        low = price - 100
        volume = 5000
        timestamp = datetime.now() - timedelta(hours=30 - i)
        detector.add_candle(high, low, (high+low)/2, volume, timestamp)
    
    # 阶段 2: 第一个底 (65000)
    for i in range(5):
        price = base_price - 2000  # 65000
        high = price + 80
        low = price - 80
        volume = 8000
        timestamp = datetime.now() - timedelta(hours=10 - i)
        detector.add_candle(high, low, (high+low)/2, volume, timestamp)
    
    # 阶段 3: 反弹
    for i in range(8):
        price = base_price - 2000 + i * 150
        high = price + 100
        low = price - 100
        volume = 6000
        timestamp = datetime.now() - timedelta(hours=5 - i)
        detector.add_candle(high, low, (high+low)/2, volume, timestamp)
    
    # 阶段 4: 第二个底 (接近 65000)
    for i in range(5):
        price = base_price - 1800  # 65200 (与第一个底相差约 3%)
        high = price + 80
        low = price - 80
        volume = 8000
        timestamp = datetime.now() - timedelta(hours=i)
        detector.add_candle(high, low, (high+low)/2, volume, timestamp)
    
    # 阶段 5: 突破颈线
    for i in range(3):
        price = base_price - 1000  # 66000 (突破颈线约 65800)
        high = price + 150
        low = price - 100
        volume = 10000
        timestamp = datetime.now() - timedelta(hours=2 - i)
        detector.add_candle(high, low, (high+low)/2, volume, timestamp)
    
    print(f"   K线数量: {len(detector.candles)}")
    
    # 找极值点
    highs_idx, lows_idx = detector.find_local_extrema(window=3)
    print(f"   发现 {len(highs_idx)} 个局部高点")
    print(f"   发现 {len(lows_idx)} 个局部低点")
    
    # 分析
    print("\n🔍 分析形态...")
    signal = detector.get_signal()
    
    # 生成报告
    report = generate_report(detector, signal)
    print(report)
    
    # 极值点详情
    print("\n📍 局部高点:")
    for idx in highs_idx[-5:]:
        c = detector.candles[idx]
        print(f"   - {c.timestamp.strftime('%H:%M')}: {c.high:.0f}")
    
    print("\n📍 局部低点:")
    for idx in lows_idx[-5:]:
        c = detector.candles[idx]
        print(f"   - {c.timestamp.strftime('%H:%M')}: {c.low:.0f}")


if __name__ == "__main__":
    main()
