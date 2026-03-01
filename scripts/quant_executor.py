#!/usr/bin/env python3
"""
量化执行引擎

职责：
1. 接收 LLM 信号
2. 执行交易订单
3. 仓位管理
4. 止盈止损监控
5. 风险控制
"""

import time
import json
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass, field

# ============ 配置 ============
QUANT_CONFIG = {
    "max_position_pct": 0.20,      # 单只最大仓位 20%
    "max_total_position": 0.80,     # 总仓位最大 80%
    "max_loss_per_day": 0.03,       # 日最大亏损 3%
    "stop_loss_pct": 0.05,          # 止损 5%
    "take_profit_pct": 0.10,        # 止盈 10%
    "max_slippage": 0.005,          # 最大滑点 0.5%
    "min_order_value": 100,         # 最小订单金额
    "retry_times": 3,               # 重试次数
    "retry_delay": 1                # 重试延迟(秒)
}


@dataclass
class Order:
    """订单"""
    order_id: str
    timestamp: str
    symbol: str
    action: str  # BUY, SELL
    quantity: int
    price: float
    status: str  # PENDING, FILLED, CANCELLED, REJECTED
    filled_price: float = 0.0
    filled_time: str = ""


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pct: float = 0.0


class QuantExecutor:
    """量化执行引擎"""
    
    def __init__(self, config: Dict = None):
        self.config = {**QUANT_CONFIG, **(config or {})}
        self.orders: List[Order] = []
        self.positions: Dict[str, Position] = {}
        self.order_id_counter = 1000
        
    def validate_signal(self, signal: Dict) -> Dict:
        """
        验证 LLM 信号
        
        检查：
        - 信号格式
        - 仓位是否过重
        - 风险敞口
        """
        errors = []
        warnings = []
        
        # 1. 格式检查
        required_fields = ['action', 'symbol', 'quantity', 'price', 'stop_loss', 'take_profit']
        for field in required_fields:
            if field not in signal:
                errors.append(f"缺少字段: {field}")
        
        if errors:
            return {"valid": False, "errors": errors}
        
        # 2. 仓位检查
        current_weight = self.get_position_weight(signal['symbol'])
        new_weight = (signal['quantity'] * signal['price']) / self.get_total_capital()
        
        if current_weight + new_weight > self.config['max_position_pct']:
            errors.append(f"仓位过重: 当前 {current_weight:.1%} + 新建 {new_weight:.1%} > {self.config['max_position_pct']:.0%}")
        
        # 3. 总仓位检查
        total_weight = self.get_total_position_weight()
        if total_weight + new_weight > self.config['max_total_position']:
            warnings.append(f"总仓位接近上限: {total_weight:.1%} + {new_weight:.1%}")
        
        # 4. 止盈止损检查
        if signal['stop_loss'] >= signal['price']:
            errors.append("止损价必须低于买入价")
        
        if signal['take_profit'] <= signal['price']:
            errors.append("止盈价必须高于买入价")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "adjusted_signal": signal
        }
    
    def submit_order(self, signal: Dict) -> Order:
        """
        提交订单
        
        流程：
        1. 验证信号
        2. 计算实际仓位
        3. 下单
        4. 确认成交
        """
        # 验证
        validation = self.validate_signal(signal)
        if not validation['valid']:
            order = Order(
                order_id=self._generate_order_id(),
                timestamp=datetime.now().isoformat(),
                symbol=signal['symbol'],
                action=signal['action'],
                quantity=signal['quantity'],
                price=signal['price'],
                status="REJECTED",
                filled_price=0,
                filled_time=""
            )
            order.errors = validation['errors']
            self.orders.append(order)
            return order
        
        # 下单（模拟）
        order = Order(
            order_id=self._generate_order_id(),
            timestamp=datetime.now().isoformat(),
            symbol=signal['symbol'],
            action=signal['action'],
            quantity=signal['quantity'],
            price=signal['price'],
            status="PENDING",
            filled_price=0,
            filled_time=""
        )
        
        # 模拟成交（实际会调用券商 API）
        order.status = "FILLED"
        order.filled_price = signal['price'] * (1 + self.config['max_slippage'])
        order.filled_time = datetime.now().isoformat()
        
        # 更新持仓
        self._update_position(order)
        
        self.orders.append(order)
        return order
    
    def _update_position(self, order: Order):
        """更新持仓"""
        symbol = order.symbol
        
        if order.action == "BUY":
            if symbol in self.positions:
                pos = self.positions[symbol]
                total_shares = pos.quantity + order.quantity
                total_cost = pos.quantity * pos.avg_cost + order.quantity * order.filled_price
                pos.avg_cost = total_cost / total_shares
                pos.quantity = total_shares
            else:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=order.quantity,
                    avg_cost=order.filled_price,
                    current_price=order.filled_price
                )
        
        elif order.action == "SELL":
            if symbol in self.positions:
                pos = self.positions[symbol]
                pos.quantity -= order.quantity
                if pos.quantity <= 0:
                    del self.positions[symbol]
    
    def monitor_positions(self):
        """
        监控持仓
        
        检查：
        - 止盈触发
        - 止损触发
        - 异常波动
        """
        alerts = []
        
        for symbol, pos in self.positions.items():
            # 计算未实现盈亏
            pos.current_price = self._get_current_price(symbol)
            pos.unrealized_pnl = (pos.current_price - pos.avg_cost) * pos.quantity
            pos.unrealized_pct = (pos.current_price - pos.avg_cost) / pos.avg_cost
            
            # 检查止损
            if pos.unrealized_pct <= -self.config['stop_loss_pct']:
                alerts.append({
                    "type": "STOP_LOSS",
                    "symbol": symbol,
                    "pct": pos.unrealized_pct,
                    "action": "建议止损"
                })
            
            # 检查止盈
            if pos.unrealized_pct >= self.config['take_profit_pct']:
                alerts.append({
                    "type": "TAKE_PROFIT",
                    "symbol": symbol,
                    "pct": pos.unrealized_pct,
                    "action": "建议止盈"
                })
        
        return alerts
    
    def _get_current_price(self, symbol: str) -> float:
        """获取当前价格（模拟）"""
        # 实际应该调用行情 API
        prices = {
            "QQQ": 600.00,
            "NVDA": 185.00,
            "TSLA": 415.00,
            "GOOGL": 307.00,
            "MSFT": 400.00
        }
        return prices.get(symbol, 0.0)
    
    def get_position_weight(self, symbol: str) -> float:
        """获取某只股票仓位权重"""
        if symbol not in self.positions:
            return 0.0
        
        pos = self.positions[symbol]
        total_capital = self.get_total_capital()
        return (pos.quantity * pos.current_price) / total_capital
    
    def get_total_position_weight(self) -> float:
        """获取总仓位权重"""
        total_capital = self.get_total_capital()
        total_position = sum(
            pos.quantity * pos.current_price 
            for pos in self.positions.values()
        )
        return total_position / total_capital
    
    def get_total_capital(self) -> float:
        """获取总资金（模拟）"""
        return 100000.0  # 10万美元模拟资金
    
    def _generate_order_id(self) -> str:
        """生成订单 ID"""
        self.order_id_counter += 1
        return f"ORD{self.order_id_counter}"
    
    def get_status(self) -> Dict:
        """获取执行引擎状态"""
        total_capital = self.get_total_capital()
        total_position = sum(
            pos.quantity * pos.current_price 
            for pos in self.positions.values()
        )
        total_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_capital": total_capital,
            "total_position": total_position,
            "position_weight": total_position / total_capital,
            "unrealized_pnl": total_pnl,
            "unrealized_pct": total_pnl / total_capital,
            "orders_count": len(self.orders),
            "positions_count": len(self.positions),
            "config": self.config
        }


def main():
    """测试量化执行引擎"""
    print("\n" + "=" * 70)
    print("⚡ 量化执行引擎 - 测试")
    print("=" * 70)
    
    # 初始化
    executor = QuantExecutor()
    
    # 模拟 LLM 信号
    signal = {
        "strategy": "EOF",
        "action": "BUY",
        "symbol": "QQQ",
        "quantity": 10,
        "price": 600.00,
        "stop_loss": 570.00,
        "take_profit": 660.00,
        "confidence": 0.85,
        "reason": "MA20金叉"
    }
    
    # 1. 验证信号
    print("\n1. 验证信号...")
    validation = executor.validate_signal(signal)
    print(f"   有效: {validation['valid']}")
    if validation['errors']:
        print(f"   错误: {validation['errors']}")
    
    # 2. 提交订单
    print("\n2. 提交订单...")
    order = executor.submit_order(signal)
    print(f"   订单ID: {order.order_id}")
    print(f"   状态: {order.status}")
    print(f"   成交价: ${order.filled_price:.2f}")
    
    # 3. 查看持仓
    print("\n3. 持仓状态...")
    status = executor.get_status()
    print(f"   总资金: ${status['total_capital']:,.2f}")
    print(f"   总仓位: {status['position_weight']:.1%}")
    print(f"   未实现盈亏: ${status['unrealized_pnl']:,.2f}")
    
    # 4. 监控止盈止损
    print("\n4. 止盈止损监控...")
    alerts = executor.monitor_positions()
    if alerts:
        for alert in alerts:
            print(f"   {alert['type']}: {alert['symbol']} {alert['pct']:.2%}")
    else:
        print("   ✅ 无警报")
    
    print("\n" + "=" * 70)
    
    # 保存状态
    with open('/tmp/quant_status.json', 'w', encoding='utf-8') as f:
        json.dump({
            "status": status,
            "positions": {
                k: v.__dict__ for k, v in executor.positions.items()
            },
            "recent_orders": [o.__dict__ for o in executor.orders[-5:]]
        }, f, ensure_ascii=False, indent=2)
    
    print("✅ 状态已保存")


if __name__ == "__main__":
    main()
