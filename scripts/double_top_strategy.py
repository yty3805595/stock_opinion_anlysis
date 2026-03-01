#!/usr/bin/env python3
"""
TradingView 策略移植：双顶/双底识别 + 交易执行

功能：
1. 识别双顶 (Double Top) 和双底 (Double Bottom) 形态
2. 计算止盈止损位
3. 执行自动交易 (长桥 API)
4. 实时监控形态变化
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

# 尝试导入长桥 API
try:
    from longbridge.openapi import WsConfig, Config, Trade, OrderType, TimeInForce
    from longbridge.openapi import OrderSide, ProductType
    HAS_LONGBRIDGE = True
except ImportError:
    HAS_LONGBRIDGE = False
    print("⚠️ 长桥 API 未安装，使用模拟模式")

# ============ 配置 ============
CONFIG = {
    "symbol": "BTC.USDT",
    "timeframe": "1h",  # 1h, 4h, 1d
    "lookback": 10,  # 寻找枢轴点的周期数 (减小以便更容易发现形态)
    "tolerance": 0.15,  # 双顶/双底的容差 (15%)
    "target_fib": 1.0,  # 目标斐波那契比例
    "atr_length": 14,
    "atr_multiplier": 1.0,
    "atr_stop": False,  # 是否使用 ATR 追踪止损
    
    # 交易配置
    "order_size": 0.01,  # BTC 数量
    "simulate": True,  # 模拟交易
    
    # 长桥配置
    "longbridge": {
        "app_key": os.getenv("LONGBRIDGE_APP_KEY", "advanced-skill-creator"),
        "app_secret": os.getenv("LONGBRIDGE_APP_SECRET", ""),
    }
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PatternType(Enum):
    """形态类型"""
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    NONE = "none"


@dataclass
class PivotPoint:
    """枢轴点"""
    high: float
    low: float
    timestamp: datetime
    is_high: bool


@dataclass
class PatternSignal:
    """形态信号"""
    pattern_type: PatternType
    confidence: float  # 0-1
    pivot_high: float  # 顶部价格
    pivot_low: float   # 底部价格
    neckline: float    # 颈线价格
    target: float      # 目标位
    stop_loss: float   # 止损位
    formation_start: datetime
    formation_end: datetime
    break_timestamp: Optional[datetime] = None
    confirmed: bool = False


class DoubleTapStrategy:
    """
    双顶/双底识别策略
    
    逻辑：
    1. 寻找最近的 N 根 K 线中的最高点和最低点
    2. 判断是否形成双顶或双底形态
    3. 计算颈线、目标位、止损位
    4. 发出交易信号
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.lookback = config["lookback"]
        self.tolerance = config["tolerance"]
        self.target_fib = config["target_fib"]
        self.atr_length = config["atr_length"]
        self.atr_multiplier = config["atr_multiplier"]
        
        # 存储历史数据
        self.highs: List[float] = []
        self.lows: List[float] = []
        self.timestamps: List[datetime] = []
        self.volumes: List[float] = []
        
        # 形态状态
        self.current_pattern: Optional[PatternSignal] = None
        self.last_pattern: Optional[PatternSignal] = None
        
    def add_candle(self, high: float, low: float, close: float, volume: float, timestamp: datetime):
        """添加一根 K 线"""
        self.highs.append(high)
        self.lows.append(low)
        self.timestamps.append(timestamp)
        self.volumes.append(volume)
        
        # 保持数据在 lookback 范围内
        if len(self.highs) > self.lookback * 2:
            self.highs = self.highs[-self.lookback * 2:]
            self.lows = self.lows[-self.lookback * 2:]
            self.timestamps = self.timestamps[-self.lookback * 2:]
            self.volumes = self.volumes[-self.lookback * 2:]
    
    def find_pivots(self) -> Tuple[List[PivotPoint], List[PivotPoint]]:
        """寻找枢轴点 (简化的局部极值检测)"""
        highs = []
        lows = []
        
        window = self.lookback
        
        for i in range(len(self.highs)):
            if i < window or i >= len(self.highs) - window:
                continue
            
            # 检查是否为局部最高点
            is_high = True
            for j in range(i - window, i + window + 1):
                if j != i and self.highs[j] > self.highs[i]:
                    is_high = False
                    break
            
            if is_high:
                highs.append(PivotPoint(
                    high=self.highs[i],
                    low=self.highs[i],
                    timestamp=self.timestamps[i],
                    is_high=True
                ))
            
            # 检查是否为局部最低点
            is_low = True
            for j in range(i - window, i + window + 1):
                if j != i and self.lows[j] < self.lows[i]:
                    is_low = False
                    break
            
            if is_low:
                lows.append(PivotPoint(
                    high=self.lows[i],
                    low=self.lows[i],
                    timestamp=self.timestamps[i],
                    is_high=False
                ))
        
        print(f"   🔍 发现 {len(highs)} 个高点, {len(lows)} 个低点")
        return highs, lows
    
    def calculate_atr(self, recent_n: int = 14) -> float:
        """计算 ATR"""
        if len(self.highs) < recent_n + 1:
            return 0.0
        
        tr_list = []
        for i in range(-recent_n, 0):
            high = self.highs[i]
            low = self.lows[i]
            close = self.highs[i]  # 用 high 近似
            tr = max(high - low, abs(high - close), abs(low - close))
            tr_list.append(tr)
        
        return sum(tr_list) / len(tr_list) if tr_list else 0.0
    
    def detect_double_top(self, highs: List[PivotPoint], lows: List[PivotPoint]) -> Optional[PatternSignal]:
        """检测双顶形态"""
        if len(highs) < 2:
            return None
        
        # 获取最近的几个高点
        recent_highs = sorted(highs, key=lambda x: x.timestamp, reverse=True)[:3]
        
        if len(recent_highs) < 2:
            return None
        
        h1, h2 = recent_highs[0], recent_highs[1]
        
        # 检查两个高点是否在容差范围内
        price_diff = abs(h1.high - h2.high)
        avg_price = (h1.high + h2.high) / 2
        tolerance_amount = avg_price * self.tolerance
        
        if price_diff > tolerance_amount:
            return None
        
        # 找到两个高点之间的最低点 (颈线)
        h1_idx = self.timestamps.index(h1.timestamp)
        h2_idx = self.timestamps.index(h2.timestamp)
        start_idx = min(h1_idx, h2_idx)
        end_idx = max(h1_idx, h2_idx)
        
        neckline_lows = self.lows[start_idx:end_idx + 1]
        if not neckline_lows:
            return None
        
        neckline = min(neckline_lows)
        
        # 检查价格是否跌破颈线
        current_price = self.highs[-1]
        if current_price > neckline:
            return None
        
        # 计算形态高度
        height = h1.high - neckline
        
        # 计算目标位
        target = neckline - height * self.target_fib
        
        # 计算止损位
        atr = self.calculate_atr()
        if self.config.get("atr_stop", False):
            stop_loss = h1.high + atr * self.atr_multiplier
        else:
            stop_loss = h1.high
        
        return PatternSignal(
            pattern_type=PatternType.DOUBLE_TOP,
            confidence=1.0 - (price_diff / avg_price),
            pivot_high=h1.high,
            pivot_low=neckline,
            neckline=neckline,
            target=target,
            stop_loss=stop_loss,
            formation_start=min(h1.timestamp, h2.timestamp),
            formation_end=max(h1.timestamp, h2.timestamp),
            break_timestamp=self.timestamps[-1] if current_price < neckline else None,
            confirmed=current_price < neckline
        )
    
    def detect_double_bottom(self, highs: List[PivotPoint], lows: List[PivotPoint]) -> Optional[PatternSignal]:
        """检测双底形态"""
        if len(lows) < 2:
            return None
        
        # 获取最近的几个低点
        recent_lows = sorted(lows, key=lambda x: x.timestamp, reverse=True)[:3]
        
        if len(recent_lows) < 2:
            return None
        
        l1, l2 = recent_lows[0], recent_lows[1]
        
        # 检查两个低点是否在容差范围内
        price_diff = abs(l1.low - l2.low)
        avg_price = (l1.low + l2.low) / 2
        tolerance_amount = avg_price * self.tolerance
        
        if price_diff > tolerance_amount:
            return None
        
        # 找到两个低点之间的最高点 (颈线)
        l1_idx = self.timestamps.index(l1.timestamp)
        l2_idx = self.timestamps.index(l2.timestamp)
        start_idx = min(l1_idx, l2_idx)
        end_idx = max(l1_idx, l2_idx)
        
        neckline_highs = self.highs[start_idx:end_idx + 1]
        if not neckline_highs:
            return None
        
        neckline = max(neckline_highs)
        
        # 检查价格是否突破颈线
        current_price = self.lows[-1]
        if current_price < neckline:
            return None
        
        # 计算形态高度
        height = neckline - l1.low
        
        # 计算目标位
        target = neckline + height * self.target_fib
        
        # 计算止损位
        atr = self.calculate_atr()
        if self.config.get("atr_stop", False):
            stop_loss = l1.low - atr * self.atr_multiplier
        else:
            stop_loss = l1.low
        
        return PatternSignal(
            pattern_type=PatternType.DOUBLE_BOTTOM,
            confidence=1.0 - (price_diff / avg_price),
            pivot_high=neckline,
            pivot_low=l1.low,
            neckline=neckline,
            target=target,
            stop_loss=stop_loss,
            formation_start=min(l1.timestamp, l2.timestamp),
            formation_end=max(l1.timestamp, l2.timestamp),
            break_timestamp=self.timestamps[-1] if current_price > neckline else None,
            confirmed=current_price > neckline
        )
    
    def analyze(self) -> Optional[PatternSignal]:
        """分析当前形态"""
        highs, lows = self.find_pivots()
        
        # 先检测双顶
        double_top = self.detect_double_top(highs, lows)
        if double_top:
            self.current_pattern = double_top
            return double_top
        
        # 再检测双底
        double_bottom = self.detect_double_bottom(highs, lows)
        if double_bottom:
            self.current_pattern = double_bottom
            return double_bottom
        
        self.current_pattern = None
        return None
    
    def get_signal(self) -> Dict:
        """获取交易信号"""
        pattern = self.analyze()
        
        if not pattern:
            return {
                "signal": "none",
                "pattern": None,
                "action": None,
                "entry": None,
                "target": None,
                "stop_loss": None,
                "confidence": 0.0
            }
        
        if pattern.pattern_type == PatternType.DOUBLE_TOP:
            return {
                "signal": "short",
                "pattern": "Double Top",
                "action": "sell",
                "entry": pattern.neckline,
                "target": pattern.target,
                "stop_loss": pattern.stop_loss,
                "confidence": pattern.confidence
            }
        
        elif pattern.pattern_type == PatternType.DOUBLE_BOTTOM:
            return {
                "signal": "long",
                "pattern": "Double Bottom",
                "action": "buy",
                "entry": pattern.neckline,
                "target": pattern.target,
                "stop_loss": pattern.stop_loss,
                "confidence": pattern.confidence
            }
        
        return {
            "signal": "none",
            "pattern": None,
            "action": None,
            "entry": None,
            "target": None,
            "stop_loss": None,
            "confidence": 0.0
        }


class TradingExecutor:
    """交易执行器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.simulate = config.get("simulate", True)
        self.orders: List[Dict] = []
        self.positions: Dict = {"symbol": config["symbol"], "qty": 0.0, "avg_price": 0.0}
        
    def execute_signal(self, signal: Dict) -> Dict:
        """执行交易信号"""
        if signal["signal"] == "none":
            return {"status": "no_signal"}
        
        action = signal["action"]
        symbol = self.config["symbol"]
        qty = self.config["order_size"]
        price = signal["entry"]
        target = signal["target"]
        stop_loss = signal["stop_loss"]
        
        if self.simulate:
            # 模拟交易
            order = {
                "id": f"sim_{int(time.time())}",
                "symbol": symbol,
                "action": action,
                "qty": qty,
                "price": price,
                "target": target,
                "stop_loss": stop_loss,
                "status": "filled",
                "timestamp": datetime.now().isoformat(),
                "mode": "simulated"
            }
            self.orders.append(order)
            
            # 更新持仓
            if action == "buy":
                self.positions["qty"] += qty
                self.positions["avg_price"] = price
            elif action == "sell":
                self.positions["qty"] = max(0, self.positions["qty"] - qty)
            
            logger.info(f"📝 [模拟] {action.upper()} {qty} {symbol} @ {price}")
            return order
        
        else:
            # 真实交易 (长桥 API)
            if not HAS_LONGBRIDGE:
                logger.error("❌ 长桥 API 未安装")
                return {"status": "error", "message": "Longbridge not available"}
            
            try:
                # 这里实现长桥 API 调用
                # order = trade.place_order(...)
                logger.info(f"🔄 [长桥] {action.upper()} {qty} {symbol} @ {price}")
                return {"status": "pending", "symbol": symbol, "action": action}
            except Exception as e:
                logger.error(f"❌ 交易失败: {e}")
                return {"status": "error", "message": str(e)}
    
    def get_positions(self) -> Dict:
        """获取当前持仓"""
        return self.positions
    
    def get_orders(self, limit: int = 10) -> List[Dict]:
        """获取订单历史"""
        return self.orders[-limit:]


def generate_report(strategy: DoubleTapStrategy, signal: Dict) -> str:
    """生成形态分析报告"""
    report = f"""
📊 双顶/双底形态分析报告
{'=' * 50}

**分析时间:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**交易品种:** {strategy.config['symbol']}
**时间周期:** {strategy.config['timeframe']}

---

## 🎯 形态识别结果

**信号:** {signal['signal'].upper() if signal['signal'] != 'none' else '无信号'}
**形态:** {signal.get('pattern', 'N/A')}
**置信度:** {signal.get('confidence', 0) * 100:.1f}%

---

## 📈 交易参数

| 参数 | 数值 |
|------|------|
| **入场价** | {signal.get('entry', 'N/A')} |
| **目标价** | {signal.get('target', 'N/A')} |
| **止损价** | {signal.get('stop_loss', 'N/A')} |

---

## ⚙️ 策略参数

| 参数 | 数值 |
|------|------|
| 枢轴周期 | {strategy.lookback} |
| 容差 | {strategy.tolerance * 100:.0f}% |
| 目标 Fib | {strategy.target_fib * 100:.0f}% |
| ATR 长度 | {strategy.atr_length} |
| ATR 倍数 | {strategy.atr_multiplier} |

---

{'✅ 双顶形态确认 - 建议做空' if signal['signal'] == 'short' else ''}
{'🟢 双底形态确认 - 建议做多' if signal['signal'] == 'long' else ''}
{'⚠️ 暂无形态信号' if signal['signal'] == 'none' else ''}

"""
    return report


def main():
    """主函数 - 测试"""
    import random
    
    # 创建策略
    strategy = DoubleTapStrategy(CONFIG)
    executor = TradingExecutor(CONFIG)
    
    # 模拟数据
    print("📊 模拟 K 线数据...")
    
    # 生成模拟的 BTC 价格数据 - 明显的双底形态
    base_price = 67000.0
    
    # 阶段 1: 下跌到第一个底
    for i in range(30):
        price = base_price - (30 - i) * 100
        high = price + random.uniform(100, 200)
        low = price - random.uniform(100, 200)
        volume = random.uniform(1000, 5000)
        timestamp = datetime.now() - timedelta(hours=50 - i)
        strategy.add_candle(high, low, (high + low) / 2, volume, timestamp)
    
    # 阶段 2: 第一个底 (价格最低)
    for i in range(5):
        price = base_price - 3500
        high = price + random.uniform(50, 150)
        low = price - random.uniform(50, 150)
        volume = random.uniform(3000, 8000)  # 放量
        timestamp = datetime.now() - timedelta(hours=20 - i)
        strategy.add_candle(high, low, (high + low) / 2, volume, timestamp)
    
    # 阶段 3: 反弹
    for i in range(15):
        price = base_price - 3500 + (i + 1) * 150
        high = price + random.uniform(100, 200)
        low = price - random.uniform(100, 200)
        volume = random.uniform(2000, 6000)
        timestamp = datetime.now() - timedelta(hours=15 - i)
        strategy.add_candle(high, low, (high + low) / 2, volume, timestamp)
    
    # 阶段 4: 第二个底 (相近价格)
    for i in range(5):
        price = base_price - 2750  # 与第一个底相差约 750 (约 11% 容差)
        high = price + random.uniform(50, 150)
        low = price - random.uniform(50, 150)
        volume = random.uniform(3000, 8000)  # 放量
        timestamp = datetime.now() - timedelta(hours=5 - i)
        strategy.add_candle(high, low, (high + low) / 2, volume, timestamp)
    
    # 阶段 5: 突破颈线 (形成双底)
    for i in range(5):
        price = base_price - 2000  # 突破颈线
        high = price + random.uniform(100, 200)
        low = price - random.uniform(100, 200)
        volume = random.uniform(4000, 10000)  # 放量突破
        timestamp = datetime.now() - timedelta(hours=i)
        strategy.add_candle(high, low, (high + low) / 2, volume, timestamp)
    
    # 分析形态
    print("🔍 分析形态...")
    signal = strategy.get_signal()
    
    # 生成报告
    report = generate_report(strategy, signal)
    print(report)
    
    # 执行交易 (模拟)
    print("🚀 执行交易...")
    result = executor.execute_signal(signal)
    print(f"交易结果: {result}")
    
    # 持仓
    print(f"\n📦 当前持仓: {executor.get_positions()}")


if __name__ == "__main__":
    main()
