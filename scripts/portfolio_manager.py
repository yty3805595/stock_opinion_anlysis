#!/usr/bin/env python3
"""
持仓管理器 - 管理股票持仓和交易
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


# 持仓文件路径
PORTFOLIO_FILE = "data/portfolio.json"


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    market_value: float
    pnl: float
    pnl_pct: float
    weight: float
    side: str  # "long" or "short"
    entry_date: str


@dataclass
class Order:
    """订单"""
    order_id: str
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    price: float
    status: str  # "pending", "filled", "cancelled"
    order_type: str  # "market" or "limit"
    created_at: str
    filled_at: Optional[str] = None
    filled_price: Optional[float] = None
    filled_quantity: Optional[float] = None


class PortfolioManager:
    """
    持仓管理器
    
    功能：
    - 持仓查询
    - 订单管理
    - 绩效统计
    """
    
    def __init__(self, portfolio_file: str = None):
        self.portfolio_file = portfolio_file or PORTFOLIO_FILE
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        
        # 确保目录存在
        Path(self.portfolio_file).parent.mkdir(parents=True, exist_ok=True)
        
        # 加载现有数据
        self.load()
    
    def load(self):
        """加载持仓数据"""
        if Path(self.portfolio_file).exists():
            with open(self.portfolio_file) as f:
                data = json.load(f)
                self.positions = {
                    k: Position(**v) for k, v in data.get("positions", {}).items()
                }
                self.orders = [Order(**o) for o in data.get("orders", [])]
    
    def save(self):
        """保存持仓数据"""
        data = {
            "positions": {k: asdict(v) for k, v in self.positions.items()},
            "orders": [asdict(o) for o in self.orders],
            "last_update": datetime.now().isoformat()
        }
        
        with open(self.portfolio_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def update_price(self, symbol: str, current_price: float):
        """更新持仓价格"""
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos.current_price = current_price
            pos.market_value = pos.quantity * current_price
            pos.pnl = (current_price - pos.avg_price) * pos.quantity
            pos.pnl_pct = (current_price - pos.avg_price) / pos.avg_price * 100
    
    def update_all_prices(self, quotes: Dict[str, float]):
        """批量更新价格"""
        for symbol, price in quotes.items():
            self.update_price(symbol, price)
    
    def add_position(self, symbol: str, quantity: float, price: float, side: str = "long"):
        """添加持仓"""
        if symbol in self.positions:
            # 追加持仓
            pos = self.positions[symbol]
            total_cost = pos.avg_price * pos.quantity + price * quantity
            pos.quantity += quantity
            pos.avg_price = total_cost / pos.quantity
        else:
            # 新建持仓
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_price=price,
                current_price=price,
                market_value=quantity * price,
                pnl=0,
                pnl_pct=0,
                weight=0,
                side=side,
                entry_date=datetime.now().strftime("%Y-%m-%d")
            )
        
        self.save()
    
    def close_position(self, symbol: str, quantity: float = None, price: float = None):
        """平仓"""
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        close_qty = quantity or pos.quantity
        close_price = price or pos.current_price
        
        pnl = (close_price - pos.avg_price) * close_qty
        
        # 更新或删除持仓
        if close_qty >= pos.quantity:
            del self.positions[symbol]
        else:
            pos.quantity -= close_qty
            pos.market_value = pos.quantity * pos.current_price
        
        self.save()
        return pnl
    
    def get_portfolio_value(self) -> float:
        """获取总资产"""
        return sum(pos.market_value for pos in self.positions.values())
    
    def get_total_pnl(self) -> float:
        """获取总盈亏"""
        return sum(pos.pnl for pos in self.positions.values())
    
    def get_positions(self) -> List[Position]:
        """获取所有持仓"""
        return list(self.positions.values())
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """获取指定持仓"""
        return self.positions.get(symbol)
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """获取指定持仓"""
        return self.positions.get(symbol)
    
    def rebalance_weights(self):
        """重新计算权重"""
        total_value = self.get_portfolio_value()
        if total_value == 0:
            return
        
        for pos in self.positions.values():
            pos.weight = pos.market_value / total_value
    
    def print_portfolio(self):
        """打印持仓"""
        print("\n" + "="*70)
        print("📊 当前持仓")
        print("="*70)
        
        if not self.positions:
            print("  无持仓")
            return
        
        print(f"\n{'代码':<8} {'数量':<10} {'均价':<10} {'现价':<10} {'市值':<12} {'盈亏':<12} {'收益率':<10}")
        print("-"*80)
        
        for pos in sorted(self.positions.values(), key=lambda x: -x.market_value):
            pnl_symbol = f"+{pos.pnl:.2f}" if pos.pnl >= 0 else f"{pos.pnl:.2f}"
            pnl_pct_symbol = f"+{pos.pnl_pct:.2f}%" if pos.pnl_pct >= 0 else f"{pos.pnl_pct:.2f}%"
            
            print(f"{pos.symbol:<8} {pos.quantity:<10.2f} {pos.avg_price:<10.2f} "
                  f"{pos.current_price:<10.2f} {pos.market_value:<12.2f} {pnl_symbol:<12} {pnl_pct_symbol:<10}")
        
        print("-"*80)
        total_value = self.get_portfolio_value()
        total_pnl = self.get_total_pnl()
        total_pnl_pct = total_pnl / (total_value - total_pnl) * 100 if total_value > total_pnl else 0
        
        pnl_symbol = f"+{total_pnl:.2f}" if total_pnl >= 0 else f"{total_pnl:.2f}"
        pnl_pct_symbol = f"+{total_pnl_pct:.2f}%" if total_pnl_pct >= 0 else f"{total_pnl_pct:.2f}%"
        
        print(f"{'合计':<8} {'':<10} {'':<10} {'':<10} {total_value:<12.2f} {pnl_symbol:<12} {pnl_pct_symbol:<10}")
        print("="*70)
    
    def create_order(self, symbol: str, side: str, quantity: float, 
                     price: float = None, order_type: str = "market") -> Order:
        """创建订单"""
        order = Order(
            order_id=f"ord_{datetime.now().strftime('%Y%m%d%H%M%S')}_{symbol}",
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            status="pending",
            order_type=order_type,
            created_at=datetime.now().isoformat()
        )
        
        self.orders.append(order)
        self.save()
        return order
    
    def get_orders(self, status: str = None) -> List[Order]:
        """获取订单"""
        if status:
            return [o for o in self.orders if o.status == status]
        return self.orders
    
    def fill_order(self, order_id: str, filled_price: float, 
                   filled_quantity: float) -> Optional[Order]:
        """订单成交"""
        for order in self.orders:
            if order.order_id == order_id:
                order.status = "filled"
                order.filled_at = datetime.now().isoformat()
                order.filled_price = filled_price
                order.filled_quantity = filled_quantity
                
                # 执行交易
                if order.side == "buy":
                    self.add_position(order.symbol, filled_quantity, filled_price)
                else:
                    self.close_position(order.symbol, filled_quantity, filled_price)
                
                self.save()
                return order
        
        return None
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        for order in self.orders:
            if order.order_id == order_id and order.status == "pending":
                order.status = "cancelled"
                self.save()
                return True
        return False


def main():
    """测试"""
    pm = PortfolioManager()
    
    # 模拟添加持仓
    print("测试持仓管理...")
    
    # 添加测试持仓
    pm.add_position("QQQ", 10, 600)
    pm.add_position("NVDA", 5, 185)
    pm.add_position("TSLA", 3, 420)
    
    # 更新价格
    pm.update_price("QQQ", 615)
    pm.update_price("NVDA", 180)
    pm.update_price("TSLA", 425)
    
    # 打印持仓
    pm.print_portfolio()
    
    print(f"\n总资产: ${pm.get_portfolio_value():.2f}")
    print(f"总盈亏: ${pm.get_total_pnl():.2f}")


if __name__ == "__main__":
    main()
