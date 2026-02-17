#!/usr/bin/env python3
"""
长桥 API 完整集成系统
- 从长桥证券API获取真实持仓
- 获取实时行情
- 分析期权信号
"""

import json
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

CONFIG_FILE = "skills/longbridge-trading/config/credentials.json"


def decimal_to_float(obj):
    """转换Decimal为float"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj


class LongbridgePortfolio:
    """长桥组合管理器"""
    
    def __init__(self):
        self.credentials = self._load_credentials()
        self.connected = False
        self.trade_client = None
        self.quote_client = None
        self.connect()
    
    def _load_credentials(self) -> Dict:
        path = Path(CONFIG_FILE)
        if path.exists():
            with open(path) as f:
                return json.load(f).get("credentials", {})
        return {}
    
    def connect(self) -> bool:
        try:
            from longbridge.openapi import Config, TradeContext, QuoteContext
            
            config = Config(
                app_key=self.credentials.get("app_key", ""),
                app_secret=self.credentials.get("app_secret", ""),
                access_token=self.credentials.get("access_token", "")
            )
            
            self.trade_client = TradeContext(config)
            self.quote_client = QuoteContext(config)
            self.connected = True
            print("✅ 长桥连接成功")
            return True
        except Exception as e:
            print(f"❌ 长桥连接失败: {e}")
            return False
    
    def get_positions(self) -> Dict[str, Dict]:
        """获取持仓"""
        if not self.connected:
            return {}
        
        try:
            response = self.trade_client.stock_positions()
            positions = {}
            
            for channel in response.channels:
                for pos in channel.positions:
                    symbol = pos.symbol.replace(".US", "")
                    positions[symbol] = {
                        "symbol": symbol,
                        "name": pos.symbol_name,
                        "quantity": float(pos.quantity),
                        "available": float(pos.available_quantity),
                        "cost_price": float(pos.cost_price),
                        "currency": str(pos.currency),
                    }
            
            return positions
        except Exception as e:
            print(f"❌ 获取持仓失败: {e}")
            return {}
    
    def get_prices(self, symbols: List[str]) -> Dict[str, float]:
        """获取实时价格"""
        prices = {}
        
        if not self.connected:
            return prices
        
        try:
            response = self.quote_client.quote([f"{s}.US" for s in symbols])
            
            for r in response:
                symbol = r.symbol.replace(".US", "")
                price = getattr(r, 'last_done', None) or getattr(r, 'prev_close', 0)
                prices[symbol] = float(price)
            
            return prices
        except Exception as e:
            print(f"❌ 获取价格失败: {e}")
            return prices
    
    def fetch_portfolio(self) -> Dict:
        """获取完整组合"""
        positions = self.get_positions()
        
        if not positions:
            return {"error": "无法获取持仓"}
        
        # 获取实时价格
        symbols = list(positions.keys())
        prices = self.get_prices(symbols)
        
        # 计算
        total_value = 0
        total_cost = 0
        
        for symbol, pos in positions.items():
            if symbol in prices:
                pos["current_price"] = prices[symbol]
            else:
                pos["current_price"] = pos["cost_price"]
            
            pos["market_value"] = pos["quantity"] * pos["current_price"]
            pos["pnl"] = (pos["current_price"] - pos["cost_price"]) * pos["quantity"]
            pos["pnl_pct"] = (pos["current_price"] - pos["cost_price"]) / pos["cost_price"] * 100
            
            total_value += pos["market_value"]
            total_cost += pos["quantity"] * pos["cost_price"]
        
        return {
            "positions": positions,
            "total_value": total_value,
            "total_cost": total_cost,
            "total_pnl": total_value - total_cost,
            "update_time": datetime.now().isoformat(),
            "connected": self.connected
        }


def main():
    print("="*70)
    print("🔗 长桥组合管理")
    print("="*70)
    
    lb = LongbridgePortfolio()
    portfolio = lb.fetch_portfolio()
    
    if "error" in portfolio:
        print(f"❌ {portfolio['error']}")
        return
    
    print("\n💼 你的持仓 (从长桥API获取):")
    print("-"*70)
    
    for symbol, pos in portfolio["positions"].items():
        emoji = "🟢" if pos["pnl"] >= 0 else "🔴"
        print(f"\n{symbol}")
        print(f"  {pos['name']}")
        print(f"  数量: {pos['quantity']:.2f}股")
        print(f"  成本: ${pos['cost_price']:.2f}")
        print(f"  现价: ${pos['current_price']:.2f}")
        print(f"  市值: ${pos['market_value']:,.2f}")
        print(f"  盈亏: {emoji} ${pos['pnl']:,.2f} ({pos['pnl_pct']:+.1f}%)")
    
    print("\n" + "="*70)
    print("📈 汇总")
    print("="*70)
    print(f"  状态: {'✅ 已连接' if portfolio['connected'] else '❌ 未连接'}")
    print(f"  持仓: {len(portfolio['positions'])} 只")
    print(f"  总市值: ${portfolio['total_value']:,.2f}")
    print(f"  总盈亏: ${portfolio['total_pnl']:,.2f}")
    print(f"  时间: {portfolio['update_time']}")
    print("="*70)
    
    # 保存
    with open("/tmp/longbridge_portfolio.json", "w") as f:
        json.dump(decimal_to_float(portfolio), f, indent=2)
    print("\n✅ 已保存到 /tmp/longbridge_portfolio.json")


if __name__ == "__main__":
    main()
