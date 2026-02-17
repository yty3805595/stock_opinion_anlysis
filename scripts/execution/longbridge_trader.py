#!/usr/bin/env python3
"""
长桥交易执行器 - 使用长桥API执行交易
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class OrderRequest:
    """订单请求"""
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    order_type: str  # "market" or "limit"
    price: float = None
    time_in_force: str = "day"  # "day" or "gtc"


@dataclass
class OrderResult:
    """订单结果"""
    order_id: str
    status: str  # "filled", "pending", "failed"
    symbol: str
    side: str
    filled_price: float
    filled_quantity: float
    commission: float
    timestamp: str
    error: str = None


class LongbridgeTrader:
    """
    长桥交易执行器
    
    使用长桥API执行实盘交易
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.paper_trading = self.config.get("execution", {}).get("paper_trading", True)
        
        # 从配置文件加载凭证
        self.credentials = self._load_credentials()
        
        # 初始化客户端
        self.client = self._init_client()
        
    def _load_credentials(self) -> dict:
        """从配置文件读取凭证"""
        config_paths = [
            "skills/longbridge-trading/config/credentials.json",
            ".env",
        ]
        
        for path_str in config_paths:
            path = Path(path_str)
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                    return data.get("credentials", {})
        
        return None
        
    def _init_client(self):
        """初始化长桥客户端"""
        if self.paper_trading:
            print("📝 模拟交易模式")
            return None
        
        if not self.credentials:
            print("⚠️ 未找到凭证，使用模拟模式")
            return None
        
        try:
            from longbridge.openapi import Config, Trade
            
            config = Config(
                app_key=self.credentials.get("app_key"),
                app_secret=self.credentials.get("app_secret"),
                access_token=self.credentials.get("access_token", "")
            )
            
            client = Trade(config)
            print("✅ 长桥交易客户端已连接")
            return client
            
        except Exception as e:
            print(f"❌ 长桥连接失败: {e}")
            return None
        self.app_key = os.getenv("LONGBRIDGE_APP_KEY", "advanced-skill-creator")
        self.app_secret = os.getenv("LONGBRIDGE_APP_SECRET", "")
        
        # 初始化客户端
        self.client = self._init_client()
        
        # 订单记录
        self.order_history = []
        
    def _init_client(self) -> object:
        """初始化长桥客户端"""
        try:
            from longbridge.openapi import WsConfig, Config, Trade
            
            if not self.app_secret:
                print("⚠️ 长桥 API Secret 未配置，使用模拟模式")
                return None
            
            config = Config(
                app_key=self.app_key,
                app_secret=self.app_secret
            )
            
            trade = Trade(config)
            
            print("✅ 长桥客户端初始化成功")
            return trade
            
        except ImportError:
            print("⚠️ 长桥 SDK 未安装，使用模拟模式")
            return None
        except Exception as e:
            print(f"❌ 长桥客户端初始化失败: {e}")
            return None
    
    def place_order(self, order: OrderRequest) -> OrderResult:
        """
        下单
        
        Args:
            order: 订单请求
            
        Returns:
            订单结果
        """
        # 1. 验证订单
        validation = self._validate_order(order)
        if not validation["valid"]:
            return OrderResult(
                order_id=f"sim_{int(time.time())}",
                status="failed",
                symbol=order.symbol,
                side=order.side,
                filled_price=0,
                filled_quantity=0,
                commission=0,
                timestamp=datetime.now().isoformat(),
                error=validation["reason"]
            )
        
        # 2. 执行订单
        if self.paper_trading:
            result = self._execute_paper_order(order)
        else:
            result = self._execute_real_order(order)
        
        # 3. 记录订单
        self.order_history.append(result)
        
        return result
    
    def _validate_order(self, order: OrderRequest) -> dict:
        """验证订单"""
        # 验证股票代码
        if not order.symbol:
            return {"valid": False, "reason": "股票代码为空"}
        
        # 验证数量
        if order.quantity <= 0:
            return {"valid": False, "reason": "数量必须大于0"}
        
        # 验证价格
        if order.order_type == "limit" and (order.price is None or order.price <= 0):
            return {"valid": False, "reason": "限价单必须指定价格"}
        
        return {"valid": True}
    
    def _execute_paper_order(self, order: OrderRequest) -> OrderResult:
        """
        执行模拟订单
        
        模拟订单执行，不真正调用API
        """
        import random
        
        # 获取当前价格 (模拟)
        current_price = self._get_simulated_price(order.symbol)
        
        # 模拟成交
        filled_price = current_price
        filled_quantity = order.quantity
        commission = filled_price * filled_quantity * 0.0001  # 万分之一佣金
        
        return OrderResult(
            order_id=f"sim_{int(time.time())}_{random.randint(1000,9999)}",
            status="filled",
            symbol=order.symbol,
            side=order.side,
            filled_price=filled_price,
            filled_quantity=filled_quantity,
            commission=commission,
            timestamp=datetime.now().isoformat()
        )
    
    def _execute_real_order(self, order: OrderRequest) -> OrderResult:
        """
        执行实盘订单
        
        真正调用长桥API
        """
        if self.client is None:
            return OrderResult(
                order_id=f"err_{int(time.time())}",
                status="failed",
                symbol=order.symbol,
                side=order.side,
                filled_price=0,
                filled_quantity=0,
                commission=0,
                timestamp=datetime.now().isoformat(),
                error="长桥客户端未初始化"
            )
        
        try:
            from longbridge.openapi import OrderSide, OrderType, TimeInForce
            
            # 转换订单参数
            side = OrderSide.Buy if order.side == "buy" else OrderSide.Sell
            order_type = OrderType.Market if order.order_type == "market" else OrderType.Limit
            time_in_force = TimeInForce.Day if order.time_in_force == "day" else TimeInForce.GTC
            
            # 下单
            result = self.client.place_order(
                symbol=order.symbol,
                side=side,
                order_type=order_type,
                quantity=order.quantity,
                time_in_force=time_in_force,
                price=order.price
            )
            
            return OrderResult(
                order_id=result.order_id,
                status="filled",
                symbol=order.symbol,
                side=order.side,
                filled_price=result.filled_price or 0,
                filled_quantity=result.filled_quantity or 0,
                commission=result.commission or 0,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            return OrderResult(
                order_id=f"err_{int(time.time())}",
                status="failed",
                symbol=order.symbol,
                side=order.side,
                filled_price=0,
                filled_quantity=0,
                commission=0,
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    def _get_simulated_price(self, symbol: str) -> float:
        """获取模拟价格"""
        base_prices = {
            "QQQ": 600, "NVDA": 185, "TSLA": 420,
            "GOOGL": 170, "MSFT": 400, "AAPL": 185,
            "AMD": 180, "META": 500, "AMZN": 175, "PLTR": 70
        }
        
        import random
        base = base_prices.get(symbol, 100)
        return base * (1 + random.uniform(-0.01, 0.01))
    
    def execute_signal(self, signal: dict, account: dict = None) -> OrderResult:
        """
        根据信号执行交易
        
        Args:
            signal: 交易信号
            account: 账户信息
            
        Returns:
            订单结果
        """
        if signal.get("action") in ["buy", "sell"]:
            order = OrderRequest(
                symbol=signal["symbol"],
                side=signal["action"],
                quantity=signal.get("position_size", 0.1),
                order_type="market"
            )
            
            result = self.place_order(order)
            
            print(f"📝 {'买入' if order.side == 'buy' else '卖出'} {order.symbol}: "
                  f"{order.quantity*100:.1f}% "
                  f"(订单ID: {result.order_id})")
            
            return result
        
        return None
    
    def get_order_history(self, limit: int = 100) -> List[OrderResult]:
        """获取订单历史"""
        return self.order_history[-limit:]
    
    def get_positions(self) -> dict:
        """获取当前持仓"""
        positions = {}
        
        for order in self.order_history:
            if order.status == "filled":
                if order.symbol not in positions:
                    positions[order.symbol] = {
                        "quantity": 0,
                        "avg_price": 0,
                        "side": order.side
                    }
                
                pos = positions[order.symbol]
                if order.side == "buy":
                    total_cost = pos["avg_price"] * pos["quantity"] + order.filled_price * order.filled_quantity
                    total_qty = pos["quantity"] + order.filled_quantity
                    pos["avg_price"] = total_cost / total_qty if total_qty > 0 else 0
                    pos["quantity"] = total_qty
                else:
                    pos["quantity"] = max(0, pos["quantity"] - order.filled_quantity)
        
        return positions
    
    def get_account_summary(self) -> dict:
        """获取账户汇总"""
        positions = self.get_positions()
        
        total_value = 0
        for symbol, pos in positions.items():
            price = self._get_simulated_price(symbol)
            total_value += price * pos["quantity"]
        
        return {
            "positions": positions,
            "total_value": total_value,
            "position_count": len(positions),
            "order_count": len(self.order_history),
            "filled_orders": sum(1 for o in self.order_history if o.status == "filled"),
            "failed_orders": sum(1 for o in self.order_history if o.status == "failed")
        }


# 测试代码
if __name__ == "__main__":
    # 创建交易器
    trader = LongbridgeTrader({
        "execution": {"paper_trading": True}
    })
    
    # 测试下单
    order = OrderRequest(
        symbol="QQQ",
        side="buy",
        quantity=0.1,
        order_type="market"
    )
    
    result = trader.place_order(order)
    
    print(f"订单ID: {result.order_id}")
    print(f"状态: {result.status}")
    print(f"成交价: {result.filled_price}")
    print(f"佣金: {result.commission}")
    
    # 获取账户汇总
    summary = trader.get_account_summary()
    print(f"\n账户汇总:")
    print(f"  持仓数量: {summary['position_count']}")
    print(f"  订单数量: {summary['order_count']}")
