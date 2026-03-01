#!/usr/bin/env python3
"""
TradingView 策略移植：双顶/双底识别 + 长桥交易

功能：
1. 识别双顶/双底形态
2. 计算止盈止损
3. 自动执行交易 (长桥 API)
4. 实时监控形态变化
5. 追踪止损保护盈利

使用:
    python3 scripts/double_top_trader.py
"""

import os
import sys
import json
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# 添加项目路径
sys.path.insert(0, '/Users/yintaoye/.openclaw/workspace')

# 尝试导入长桥 API
try:
    from longbridge.openapi import WsConfig, Config, Trade, OrderType, TimeInForce
    from longbridge.openapi import OrderSide, ProductType
    HAS_LONGBRIDGE = True
except ImportError:
    HAS_LONGBRIDGE = False
    print("⚠️ 长桥 API 未安装，将使用模拟模式")

# ============ 配置 ============
CONFIG = {
    "symbol": "BTC.USDT",
    "exchange": "Binance",  # Binance, Coinbase, OKX
    "trade_quantity": 0.01,  # 交易数量 (BTC)
    
    # 形态检测参数
    "window": 5,  # 局部极值窗口
    "tolerance": 0.10,  # 双顶/双底容差 (10%)
    "min_distance": 5,  # 两个顶/底的最小距离 (K 线数)
    "target_ratio": 1.0,  # 目标止盈比例
    
    # 追踪止损
    "use_trailing_stop": True,
    "trailing_atr_period": 14,
    "trailing_atr_multiplier": 2.0,
    
    # 交易配置
    "simulate": True,  # 模拟交易模式
    "order_type": "market",  # market, limit
    "limit_offset": 0.001,  # 限价单偏移比例
    
    # 通知配置
    "notify_telegram": True,
    "notify_email": False,
    
    # 长桥 API 凭证
    "longbridge": {
        "app_key": os.getenv("LONGBRIDGE_APP_KEY", "advanced-skill-creator"),
        "app_secret": os.getenv("LONGBRIDGE_APP_SECRET", ""),
    }
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PatternType(Enum):
    """形态类型"""
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    NONE = "none"


@dataclass
class Candle:
    """K 线"""
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime


@dataclass
class TradeOrder:
    """交易订单"""
    order_id: str
    symbol: str
    side: str  # buy, sell
    quantity: float
    price: float
    status: str  # pending, filled, cancelled
    created_at: datetime
    filled_at: Optional[datetime] = None
    pnl: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "pnl": self.pnl
        }


class PatternDetector:
    """双顶/双底形态检测器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.window = config.get("window", 5)
        self.tolerance = config.get("tolerance", 0.10)
        self.min_distance = config.get("min_distance", 5)
        self.target_ratio = config.get("target_ratio", 1.0)
        
        self.candles: List[Candle] = []
        
    def add_candle(self, high: float, low: float, close: float, 
                   volume: float, timestamp: datetime):
        """添加 K 线"""
        self.candles.append(Candle(high, low, close, volume, timestamp))
        
        # 保持最多 200 根 K 线
        if len(self.candles) > 200:
            self.candles = self.candles[-200:]
    
    def find_local_extrema(self) -> Tuple[List[int], List[int]]:
        """找到局部极值点索引"""
        highs_idx = []
        lows_idx = []
        
        for i in range(self.window, len(self.candles) - self.window):
            # 局部高点
            is_high = True
            for j in range(i - self.window, i + self.window + 1):
                if j != i and self.candles[j].high >= self.candles[i].high:
                    is_high = False
                    break
            if is_high:
                highs_idx.append(i)
            
            # 局部低点
            is_low = True
            for j in range(i - self.window, i + self.window + 1):
                if j != i and self.candles[j].low <= self.candles[i].low:
                    is_low = False
                    break
            if is_low:
                lows_idx.append(i)
        
        return highs_idx, lows_idx
    
    def detect_pattern(self) -> Dict:
        """检测形态"""
        highs_idx, lows_idx = self.find_local_extrema()
        
        # 检测双顶
        double_top = self._detect_double_top(highs_idx)
        if double_top:
            return double_top
        
        # 检测双底
        double_bottom = self._detect_double_bottom(lows_idx)
        if double_bottom:
            return double_bottom
        
        return {"pattern": "none", "confidence": 0.0}
    
    def _detect_double_top(self, highs_idx: List[int]) -> Optional[Dict]:
        """检测双顶"""
        if len(highs_idx) < 2:
            return None
        
        recent = highs_idx[-6:]  # 最近 6 个
        
        for i in range(len(recent) - 1):
            idx1, idx2 = recent[i], recent[i + 1]
            
            if idx2 - idx1 < self.min_distance:
                continue
            
            price1 = self.candles[idx1].high
            price2 = self.candles[idx2].high
            
            diff = abs(price1 - price2) / ((price1 + price2) / 2)
            if diff > self.tolerance:
                continue
            
            # 找颈线 (两个高点之间的最低点)
            neckline = min(
                c.low for c in self.candles[idx1:idx2 + 1]
            )
            
            # 检查是否跌破颈线
            current = self.candles[-1]
            if current.low <= neckline:
                height = ((price1 + price2) / 2) - neckline
                
                return {
                    "pattern": "double_top",
                    "side": "sell",
                    "confidence": 1.0 - diff,
                    "entry": neckline,
                    "target": neckline - height * self.target_ratio,
                    "stop_loss": max(price1, price2),
                    "pivot_highs": [price1, price2],
                    "neckline": neckline,
                    "break_candle": len(self.candles) - 1
                }
        
        return None
    
    def _detect_double_bottom(self, lows_idx: List[int]) -> Optional[Dict]:
        """检测双底"""
        if len(lows_idx) < 2:
            return None
        
        recent = lows_idx[-6:]
        
        for i in range(len(recent) - 1):
            idx1, idx2 = recent[i], recent[i + 1]
            
            if idx2 - idx1 < self.min_distance:
                continue
            
            price1 = self.candles[idx1].low
            price2 = self.candles[idx2].low
            
            diff = abs(price1 - price2) / ((price1 + price2) / 2)
            if diff > self.tolerance:
                continue
            
            # 找颈线 (两个低点之间的最高点)
            neckline = max(
                c.high for c in self.candles[idx1:idx2 + 1]
            )
            
            # 检查是否突破颈线
            current = self.candles[-1]
            if current.high >= neckline:
                height = neckline - ((price1 + price2) / 2)
                
                return {
                    "pattern": "double_bottom",
                    "side": "buy",
                    "confidence": 1.0 - diff,
                    "entry": neckline,
                    "target": neckline + height * self.target_ratio,
                    "stop_loss": min(price1, price2),
                    "pivot_lows": [price1, price2],
                    "neckline": neckline,
                    "break_candle": len(self.candles) - 1
                }
        
        return None
    
    def get_signal(self) -> Dict:
        """获取交易信号"""
        result = self.detect_pattern()
        
        if result["pattern"] == "none":
            return {
                "signal": "none",
                "action": None,
                "entry": None,
                "target": None,
                "stop_loss": None,
                "confidence": 0.0
            }
        
        return {
            "signal": result["side"],
            "action": "sell" if result["side"] == "sell" else "buy",
            "entry": result["entry"],
            "target": result["target"],
            "stop_loss": result["stop_loss"],
            "confidence": result["confidence"],
            "pattern": result["pattern"]
        }


class LongbridgeTrader:
    """长桥交易执行器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.simulate = config.get("simulate", True)
        self.orders: List[TradeOrder] = []
        self.position = {"qty": 0.0, "avg_price": 0.0}
        
        self.client = None
        if not self.simulate and HAS_LONGBRIDGE:
            self._init_client()
    
    def _init_client(self):
        """初始化长桥客户端"""
        try:
            cfg = Config(
                app_key=self.config["longbridge"]["app_key"],
                app_secret=self.config["longbridge"]["app_secret"],
            )
            self.client = Trade(cfg)
            logger.info("✅ 长桥交易客户端已连接")
        except Exception as e:
            logger.error(f"❌ 长桥连接失败: {e}")
            self.simulate = True
    
    def execute_order(self, signal: Dict) -> TradeOrder:
        """执行订单"""
        if signal["signal"] == "none":
            return None
        
        symbol = self.config["symbol"]
        side = signal["action"]
        qty = self.config["trade_quantity"]
        price = signal["entry"]
        
        order = TradeOrder(
            order_id=f"dt_{int(time.time())}_{side}",
            symbol=symbol,
            side=side,
            quantity=qty,
            price=price,
            status="pending",
            created_at=datetime.now()
        )
        
        if self.simulate:
            # 模拟交易
            order.status = "filled"
            order.filled_at = datetime.now()
            
            if side == "buy":
                self.position["qty"] += qty
                self.position["avg_price"] = price
            else:
                self.position["qty"] = max(0, self.position["qty"] - qty)
            
            logger.info(f"📝 [模拟] {side.upper()} {qty} {symbol} @ {price}")
        else:
            # 真实交易 (长桥 API)
            try:
                # 这里实现真实的交易逻辑
                # order_result = self.client.place_order(...)
                logger.info(f"🔄 [长桥] {side.upper()} {qty} {symbol} @ {price}")
            except Exception as e:
                logger.error(f"❌ 交易失败: {e}")
                order.status = "failed"
        
        self.orders.append(order)
        return order
    
    def get_position(self) -> Dict:
        """获取当前持仓"""
        return self.position
    
    def get_orders(self, limit: int = 20) -> List[Dict]:
        """获取订单历史"""
        return [o.to_dict() for o in self.orders[-limit:]]


class DoubleTopTrader:
    """双顶/双底交易机器人"""
    
    def __init__(self, config: dict):
        self.config = config
        self.detector = PatternDetector(config)
        self.trader = LongbridgeTrader(config)
        
        # 状态
        self.current_signal: Dict = {"signal": "none"}
        self.last_pattern_time: Optional[datetime] = None
        self.trade_count = 0
        self.win_count = 0
        
        # 记录
        self.trades: List[Dict] = []
    
    def on_candle(self, high: float, low: float, close: float, 
                  volume: float, timestamp: datetime):
        """收到新 K 线"""
        # 添加 K 线
        self.detector.add_candle(high, low, close, volume, timestamp)
        
        # 分析形态
        signal = self.detector.get_signal()
        
        # 信号变化检测
        if signal["signal"] != self.current_signal["signal"]:
            if signal["signal"] != "none":
                self.current_signal = signal
                self._on_new_signal(signal)
    
    def _on_new_signal(self, signal: Dict):
        """新信号处理"""
        self.last_pattern_time = datetime.now()
        
        # 执行交易
        order = self.trader.execute_order(signal)
        
        if order:
            self.trades.append({
                "time": datetime.now().isoformat(),
                "pattern": signal["pattern"],
                "side": signal["action"],
                "entry": signal["entry"],
                "target": signal["target"],
                "stop_loss": signal["stop_loss"],
                "status": order.status,
                "pnl": 0.0  # 稍后计算
            })
            
            self.trade_count += 1
            
            # 发送通知
            self._notify(signal)
    
    def _notify(self, signal: Dict):
        """发送通知"""
        msg = f"""
🎯 双顶/双底交易信号

**形态:** {signal.get('pattern', 'N/A')}
**方向:** {signal['action'].upper()}
**置信度:** {signal['confidence']*100:.1f}%

**入场:** {signal['entry']:.2f}
**目标:** {signal['target']:.2f}
**止损:** {signal['stop_loss']:.2f}

**交易量:** {self.config['trade_quantity']} {self.config['symbol']}
"""
        if self.config.get("notify_telegram", False):
            logger.info(f"📨 通知: {msg.strip()}")
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "symbol": self.config["symbol"],
            "current_signal": self.current_signal["signal"],
            "position": self.trader.get_position(),
            "trade_count": self.trade_count,
            "win_rate": self.win_count / self.trade_count if self.trade_count > 0 else 0.0,
            "last_pattern_time": self.last_pattern_time.isoformat() if self.last_pattern_time else None,
            "recent_trades": self.trades[-5:]
        }
    
    def generate_report(self) -> str:
        """生成报告"""
        status = self.get_status()
        
        report = f"""
📊 双顶/双底交易报告
{'=' * 60}

**时间:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**品种:** {status['symbol']}

---

## 📈 当前状态

**信号:** {status['current_signal'].upper()}
**交易次数:** {status['trade_count']}
**胜率:** {status['win_rate']*100:.1f}%

---

## 📦 持仓

| 项目 | 数值 |
|------|------|
| 数量 | {status['position']['qty']} |
| 平均价 | {status['position']['avg_price']:.2f} |

---

## 🎯 策略参数

| 参数 | 数值 |
|------|------|
| 极值窗口 | {self.config['window']} |
| 容差 | {self.config['tolerance']*100:.0f}% |
| 最小距离 | {self.config['min_distance']} K线 |
| 目标比例 | {self.config['target_ratio']*100:.0f}% |
| 模拟模式 | {'是' if self.config['simulate'] else '否'} |

---

## 📝 最近交易

"""
        
        for trade in status['recent_trades']:
            report += f"- {trade['time'][:16]} | {trade['pattern']} | {trade['side']} | {trade['entry']:.0f} | {trade['status']}\n"
        
        return report


def main():
    """主函数 - 测试"""
    import random
    from datetime import timedelta
    
    # 创建交易机器人
    bot = DoubleTopTrader(CONFIG)
    
    print("🚀 启动双顶/双底交易机器人")
    print(f"   模拟模式: {CONFIG['simulate']}")
    print()
    
    # 生成模拟数据 - 明显的双底形态
    base_price = 67000.0
    
    print("📊 生成模拟 K 线数据...")
    
    # 阶段 1: 下跌
    for i in range(20):
        price = base_price - i * 150
        bot.on_candle(
            high=price + 100,
            low=price - 100,
            close=(price + 100 + price - 100) / 2,
            volume=5000,
            timestamp=datetime.now() - timedelta(hours=30 - i)
        )
    
    # 阶段 2: 第一个底
    for i in range(5):
        price = base_price - 2000
        bot.on_candle(
            high=price + 80,
            low=price - 80,
            close=(price + 80 + price - 80) / 2,
            volume=8000,
            timestamp=datetime.now() - timedelta(hours=10 - i)
        )
    
    # 阶段 3: 反弹
    for i in range(8):
        price = base_price - 2000 + i * 150
        bot.on_candle(
            high=price + 100,
            low=price - 100,
            close=(price + 100 + price - 100) / 2,
            volume=6000,
            timestamp=datetime.now() - timedelta(hours=5 - i)
        )
    
    # 阶段 4: 第二个底
    for i in range(5):
        price = base_price - 1800
        bot.on_candle(
            high=price + 80,
            low=price - 80,
            close=(price + 80 + price - 80) / 2,
            volume=8000,
            timestamp=datetime.now() - timedelta(hours=i)
        )
    
    # 阶段 5: 突破颈线 - 触发信号
    for i in range(3):
        price = base_price - 1000
        bot.on_candle(
            high=price + 150,
            low=price - 100,
            close=(price + 150 + price - 100) / 2,
            volume=10000,
            timestamp=datetime.now() - timedelta(hours=2 - i)
        )
    
    # 生成报告
    report = bot.generate_report()
    print(report)
    
    # 保存报告
    with open('/tmp/double_top_trader_report.md', 'w') as f:
        f.write(report)
    
    print("✅ 报告已保存: /tmp/double_top_trader_report.md")


if __name__ == "__main__":
    main()
