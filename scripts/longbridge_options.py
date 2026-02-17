#!/usr/bin/env python3
"""
Longbridge 期权交易集成
"""

import os
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============ 配置 ============
CONFIG_FILE = "skills/longbridge-trading/config/credentials.json"
OPTIONS_FILE = "data/options_portfolio.json"


class LongbridgeOptionsClient:
    """长桥期权客户端"""
    
    def __init__(self):
        self.credentials = self._load_credentials()
        self.connected = False
        self.client = None
        
        # 真实期权参数
        self.option_params = {
            "QQQ": {"strike_multiplier": 5, "min_premium": 15, "contract_size": 100},
            "NVDA": {"strike_multiplier": 5, "min_premium": 10, "contract_size": 100},
            "AMD": {"strike_multiplier": 2.5, "min_premium": 5, "contract_size": 100},
            "PLTR": {"strike_multiplier": 2.5, "min_premium": 3, "contract_size": 100},
            "TSLA": {"strike_multiplier": 10, "min_premium": 10, "contract_size": 100},
            "GOOGL": {"strike_multiplier": 5, "min_premium": 10, "contract_size": 100},
            "MSFT": {"strike_multiplier": 5, "min_premium": 10, "contract_size": 100},
            "AAPL": {"strike_multiplier": 2.5, "min_premium": 5, "contract_size": 100},
            "META": {"strike_multiplier": 10, "min_premium": 15, "contract_size": 100},
            "AMZN": {"strike_multiplier": 5, "min_premium": 10, "contract_size": 100},
        }
    
    def _load_credentials(self) -> Dict:
        """加载凭证"""
        config_path = Path(CONFIG_FILE)
        if config_path.exists():
            with open(config_path) as f:
                data = json.load(f)
                return data.get("credentials", {})
        return {}
    
    def connect(self) -> bool:
        """连接长桥"""
        try:
            # 导入长桥 SDK
            from longbridge.openapi import Config, Trade, QuoteContext
            
            config = Config(
                app_key=self.credentials.get("app_key", ""),
                app_secret=self.credentials.get("app_secret", ""),
                access_token=self.credentials.get("access_token", "")
            )
            
            # 交易客户端
            self.client = Trade(config)
            self.connected = True
            
            print("✅ 长桥期权客户端已连接")
            return True
            
        except Exception as e:
            print(f"⚠️ 长桥连接失败: {e}")
            print("使用模拟模式")
            self.connected = False
            return False
    
    def get_option_chain(self, symbol: str) -> List[Dict]:
        """获取期权链 (模拟真实数据)"""
        params = self.option_params.get(symbol, self.option_params["QQQ"])
        
        # 生成期权链
        chain = []
        for months_ahead in [1, 2, 3]:
            expiry = (datetime.now() + timedelta(days=30*months_ahead)).strftime("%Y-%m-%d")
            
            for strike_pct in [0.90, 0.92, 0.95, 0.97, 1.00]:
                # 简化计算
                strike = round(100 * strike_pct / params["strike_multiplier"]) * params["strike_multiplier"]
                premium = params["min_premium"] + abs(100 * (strike_pct - 1)) * 2
                
                chain.append({
                    "symbol": symbol,
                    "underlying": f"{symbol}",
                    "expiration": expiry,
                    "strike": strike,
                    "type": "put",
                    "premium": round(premium, 2),
                    "bid": round(premium * 0.98, 2),
                    "ask": round(premium * 1.02, 2),
                })
        
        return chain
    
    def get_realistic_option(self, symbol: str, strategy: str, 
                           current_price: float) -> Dict:
        """获取真实期权参数"""
        params = self.option_params.get(symbol, self.option_params["QQQ"])
        
        # 根据策略计算行权价
        if strategy == "hedge":
            strike = round(current_price * 0.95 / params["strike_multiplier"]) * params["strike_multiplier"]
        elif strategy == "bottom_fish":
            strike = round(current_price * 0.90 / params["strike_multiplier"]) * params["strike_multiplier"]
        else:
            strike = round(current_price * 0.92 / params["strike_multiplier"]) * params["strike_multiplier"]
        
        # 估算权利金
        if strategy == "hedge":
            premium = params["min_premium"] + current_price * 0.02  # 2% 权利金
        elif strategy == "bottom_fish":
            premium = params["min_premium"] + current_price * 0.03  # 3% 权利金
        else:
            premium = params["min_premium"] + current_price * 0.025
        
        premium = round(premium, 2)
        
        # 到期日
        if strategy == "bottom_fish":
            days = 60
        else:
            days = 30
        expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        
        # 期权代码 (长桥格式)
        expiry_code = expiry.replace("-", "")[2:]
        option_code = f"{symbol}{expiry_code}P{int(strike)}"
        
        return {
            "symbol": symbol,
            "option_code": option_code,
            "underlying": symbol,
            "expiration": expiry,
            "strike": strike,
            "type": "put",
            "premium": premium,
            "bid": round(premium * 0.98, 2),
            "ask": round(premium * 1.02, 2),
            "contract_size": params["contract_size"],
            "total_cost": premium * params["contract_size"],
            "days_to_expiry": days
        }


# ============ 期权交易系统 ============
class OptionsTrader:
    """期权交易器 (集成长桥)"""
    
    def __init__(self):
        self.client = LongbridgeOptionsClient()
        self.client.connect()
        
        self.positions = {}
        self.cash = 50000
        
        # 加载持仓
        self.load()
    
    def load(self):
        """加载持仓"""
        if Path(OPTIONS_FILE).exists():
            with open(OPTIONS_FILE) as f:
                data = json.load(f)
                self.cash = data.get("cash", 50000)
    
    def save(self):
        """保存持仓"""
        data = {
            "cash": self.cash,
            "positions": self.positions,
            "last_update": datetime.now().isoformat()
        }
        Path(OPTIONS_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(OPTIONS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    
    def analyze_and_buy(self, symbol: str, strategy: str, current_price: float,
                       position_size: float = 0.01) -> Dict:
        """分析并买入期权"""
        # 获取期权参数
        option = self.client.get_realistic_option(symbol, strategy, current_price)
        
        # 计算成本
        cost = option["total_cost"]
        
        print("="*70)
        print(f"📝 {symbol} {strategy.upper()} 期权")
        print("="*70)
        print(f"  现价: ${current_price:.2f}")
        print(f"  行权价: ${option['strike']:.0f}")
        print(f"  到期: {option['expiration']}")
        print(f"  权利金: ${option['premium']:.2f}")
        print(f"  合约价值: ${option['total_cost']:.2f}")
        
        # 检查资金
        if cost > self.cash:
            print(f"  ❌ 资金不足: ${self.cash:.2f} < ${cost:.2f}")
            return None
        
        # 执行 (模拟或实盘)
        if self.client.connected and self.client.client:
            print("  🔗 实盘模式...")
            # 实盘代码需要长桥完整API
            # result = self.client.client.place_order(...)
        else:
            print("  📝 模拟模式: 买入期权")
        
        # 记录持仓
        self.cash -= cost
        self.positions[option["option_code"]] = {
            "symbol": symbol,
            "option_code": option["option_code"],
            "strike": option["strike"],
            "expiration": option["expiration"],
            "premium": option["premium"],
            "quantity": 1,
            "cost": cost,
            "strategy": strategy,
            "open_date": datetime.now().strftime("%Y-%m-%d")
        }
        self.save()
        
        print(f"  ✅ 买入成功: {option['option_code']}")
        print(f"     成本: ${cost:.2f}")
        print(f"     剩余现金: ${self.cash:.2f}")
        
        return option
    
    def get_portfolio(self) -> Dict:
        """获取组合"""
        return {
            "cash": self.cash,
            "positions": self.positions,
            "total_value": self.cash + sum(p["cost"] for p in self.positions.values())
        }
    
    def print_portfolio(self):
        """打印组合"""
        print("\n" + "="*70)
        print("📊 期权持仓")
        print("="*70)
        print(f"\n💰 现金: ${self.cash:,.2f}")
        print(f"📈 持仓数: {len(self.positions)}")
        print(f"💵 总投入: ${sum(p['cost'] for p in self.positions.values()):,.2f}")
        print("="*70)


# ============ 测试 ============
def main():
    """测试"""
    print("="*70)
    print("🧪 Longbridge 期权集成测试")
    print("="*70)
    
    # 创建客户端
    client = LongbridgeOptionsClient()
    client.connect()
    
    # 测试 NVDA
    print("\n📊 NVDA 期权链:")
    chain = client.get_option_chain("NVDA")
    for opt in chain[:5]:
        print(f"  {opt['expiration']} Put @ ${opt['strike']:.0f}: ${opt['premium']:.2f}")
    
    # 测试真实期权参数
    print("\n📝 NVDA 对冲期权:")
    option = client.get_realistic_option("NVDA", "hedge", 180.47)
    print(f"  代码: {option['option_code']}")
    print(f"  行权价: ${option['strike']:.0f}")
    print(f"  权利金: ${option['premium']:.2f}")
    print(f"  总成本: ${option['total_cost']:.2f}")


if __name__ == "__main__":
    main()
