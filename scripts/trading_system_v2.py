#!/usr/bin/env python3
"""
QLib + RD-Agent + Longbridge 整合交易系统 v2.0
- 持仓管理
- 买入下单
- 信号执行
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Optional
from dataclasses import dataclass, asdict

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

# ============ 配置 ============
DEFAULT_CONFIG = {
    "symbols": [
        "QQQ", "NVDA", "TSLA", "GOOGL", "MSFT",
        "AAPL", "AMD", "META", "AMZN", "PLTR"
    ],
    "capital": 100000,  # 初始资金
    "data": {
        "lookback_days": 365,
        "rebalance_freq": "weekly"
    },
    "risk": {
        "max_single": 0.30,      # 单只最大仓位 30%
        "max_sector": 0.50,      # 单板块最大 50%
        "stop_loss": 0.05,       # 止损 5%
        "take_profit": 0.10,     # 止盈 10%
        "max_drawdown": 0.10     # 最大回撤 10%
    },
    "execution": {
        "broker": "longbridge",
        "paper_trading": True,
        "auto_trade": False       # 自动交易开关
    }
}


# ============ 持仓管理 ============
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
    side: str
    entry_date: str


class PortfolioManager:
    """持仓管理器"""
    
    def __init__(self, capital: float = 100000):
        self.cash = capital
        self.positions: Dict[str, Position] = {}
        self.portfolio_file = PORTFOLIO_FILE
        
        Path(self.portfolio_file).parent.mkdir(parents=True, exist_ok=True)
        self.load()
    
    def load(self):
        """加载持仓"""
        if Path(self.portfolio_file).exists():
            with open(self.portfolio_file) as f:
                data = json.load(f)
                self.cash = data.get("cash", 100000)
                self.positions = {
                    k: Position(**v) for k, v in data.get("positions", {}).items()
                }
    
    def save(self):
        """保存持仓"""
        data = {
            "cash": self.cash,
            "positions": {k: asdict(v) for k, v in self.positions.items()},
            "last_update": datetime.now().isoformat()
        }
        with open(self.portfolio_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def update_price(self, symbol: str, price: float):
        """更新价格"""
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos.current_price = price
            pos.market_value = pos.quantity * price
            pos.pnl = (price - pos.avg_price) * pos.quantity
            pos.pnl_pct = (price - pos.avg_price) / pos.avg_price * 100
    
    def add_position(self, symbol: str, quantity: float, price: float):
        """添加持仓"""
        cost = quantity * price
        if cost > self.cash:
            print(f"❌ 现金不足: ${self.cash:.2f} < ${cost:.2f}")
            return False
        
        self.cash -= cost
        
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_cost = pos.avg_price * pos.quantity + cost
            pos.quantity += quantity
            pos.avg_price = total_cost / pos.quantity
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_price=price,
                current_price=price,
                market_value=cost,
                pnl=0,
                pnl_pct=0,
                weight=0,
                side="long",
                entry_date=datetime.now().strftime("%Y-%m-%d")
            )
        
        self.save()
        return True
    
    def close_position(self, symbol: str, quantity: float = None, price: float = None):
        """平仓"""
        if symbol not in self.positions:
            return 0
        
        pos = self.positions[symbol]
        close_qty = quantity or pos.quantity
        close_price = price or pos.current_price
        proceeds = close_qty * close_price
        
        self.cash += proceeds
        
        if close_qty >= pos.quantity:
            del self.positions[symbol]
        else:
            pos.quantity -= close_qty
            pos.market_value = pos.quantity * pos.current_price
        
        self.save()
        return proceeds
    
    def get_portfolio_value(self) -> float:
        """获取组合价值"""
        return self.cash + sum(pos.market_value for pos in self.positions.values())
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """获取指定持仓"""
        return self.positions.get(symbol)
    
    def print_portfolio(self):
        """打印持仓"""
        print("\n" + "="*70)
        print("📊 当前持仓")
        print("="*70)
        
        total_value = self.get_portfolio_value()
        
        print(f"\n💰 现金: ${self.cash:,.2f}")
        print(f"📈 总资产: ${total_value:,.2f}")
        print("-"*70)
        
        if not self.positions:
            print("  无持仓")
        else:
            print(f"{'代码':<8} {'数量':<10} {'均价':<10} {'现价':<10} {'市值':<12} {'盈亏':<12} {'收益率':<8}")
            print("-"*80)
            
            for pos in sorted(self.positions.values(), key=lambda x: -x.market_value):
                pnl_str = f"+${pos.pnl:.2f}" if pos.pnl >= 0 else f"-${abs(pos.pnl):.2f}"
                pct_str = f"+{pos.pnl_pct:.2f}%" if pos.pnl_pct >= 0 else f"{pos.pnl_pct:.2f}%"
                
                print(f"{pos.symbol:<8} {pos.quantity:<10.2f} ${pos.avg_price:<9.2f} ${pos.current_price:<9.2f} "
                      f"${pos.market_value:<11,.2f} {pnl_str:<12} {pct_str:<8}")
        
        print("="*70)


# ============ 长桥交易执行器 ============
class LongbridgeTrader:
    """长桥交易执行器"""
    
    def __init__(self, paper_trading: bool = True):
        self.paper_trading = paper_trading
        self.client = self._init_client()
        
        # 模拟价格
        self.simulated_prices = {
            "QQQ": 600, "NVDA": 185, "TSLA": 420,
            "GOOGL": 170, "MSFT": 400, "AAPL": 185,
            "AMD": 180, "META": 500, "AMZN": 175, "PLTR": 70
        }
    
    def _init_client(self):
        """初始化客户端"""
        if self.paper_trading:
            print("📝 模拟交易模式")
            return None
        
        try:
            from longbridge.openapi import Config, Trade
            
            # 从配置文件读取凭证
            creds = self._load_credentials()
            if not creds:
                print("⚠️ 未找到凭证，使用模拟模式")
                return None
            
            config = Config(
                app_key=creds.get("app_key"),
                app_secret=creds.get("app_secret"),
                access_token=creds.get("access_token", "")
            )
            
            client = Trade(config)
            print("✅ 长桥交易客户端已连接")
            return client
            
        except Exception as e:
            print(f"⚠️ 长桥连接失败: {e}")
            return None
    
    def _load_credentials(self) -> dict:
        """读取凭证"""
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
    
    def get_price(self, symbol: str) -> float:
        """获取价格"""
        if self.client and not self.paper_trading:
            # 实盘获取价格 (需要实现)
            pass
        
        return self.simulated_prices.get(symbol, 100)
    
    def set_price(self, symbol: str, price: float):
        """设置模拟价格"""
        self.simulated_prices[symbol] = price
    
    def buy(self, symbol: str, quantity: float = None, pct: float = None) -> dict:
        """买入"""
        price = self.get_price(symbol)
        
        # 计算数量
        if quantity is None and pct is not None:
            quantity = pct * 100000 / price  # 默认10万资金
        
        if quantity is None:
            quantity = 0.1
        
        if self.paper_trading:
            print(f"📝 [模拟] 买入 {symbol}: {quantity:.2f}股 @ ${price:.2f}")
            return {
                "status": "filled",
                "symbol": symbol,
                "side": "buy",
                "quantity": quantity,
                "price": price,
                "amount": quantity * price
            }
        else:
            # 实盘下单 (需要长桥API完整实现)
            print(f"⚠️ 实盘下单待实现")
            return {"status": "pending", "symbol": symbol, "side": "buy"}
    
    def sell(self, symbol: str, quantity: float = None) -> dict:
        """卖出"""
        price = self.get_price(symbol)
        
        if quantity is None:
            quantity = 1.0  # 全仓
        
        if self.paper_trading:
            print(f"📝 [模拟] 卖出 {symbol}: {quantity:.2f}股 @ ${price:.2f}")
            return {
                "status": "filled",
                "symbol": symbol,
                "side": "sell",
                "quantity": quantity,
                "price": price,
                "amount": quantity * price
            }
        else:
            return {"status": "pending", "symbol": symbol, "side": "sell"}


# ============ 主交易系统 ============
class TradingSystem:
    """交易系统"""
    
    def __init__(self, config: dict = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        
        # 初始化组件
        self.portfolio = PortfolioManager(self.config.get("capital", 100000))
        self.trader = LongbridgeTrader(self.config["execution"]["paper_trading"])
        
        # 加载模型 (模拟)
        self.models = {}
        
    def generate_signals(self) -> Dict[str, dict]:
        """生成信号 (模拟)"""
        import random
        
        signals = {}
        for symbol in self.config["symbols"]:
            score = random.uniform(0.3, 0.8)
            
            if score >= 0.65:
                level = "strong_buy"
                action = "buy"
            elif score >= 0.55:
                level = "buy"
                action = "buy"
            elif score >= 0.45:
                level = "hold"
                action = "hold"
            elif score >= 0.35:
                level = "sell"
                action = "sell"
            else:
                level = "strong_sell"
                action = "sell"
            
            position_size = min(abs(score - 0.5) * 2 * 0.3, 0.30)
            
            signals[symbol] = {
                "symbol": symbol,
                "score": score,
                "level": level,
                "action": action,
                "position_size": position_size,
                "price": self.trader.get_price(symbol)
            }
        
        return signals
    
    def execute_strong_buy_signals(self, signals: Dict[str, dict]):
        """执行强烈买入信号"""
        if not self.config["execution"]["auto_trade"]:
            print("\n🤖 自动交易已关闭，仅显示信号")
            return
        
        print("\n" + "="*70)
        print("🎯 执行强烈买入信号")
        print("="*70)
        
        for symbol, signal in signals.items():
            if signal["level"] == "strong_buy":
                price = signal["price"]
                quantity = signal["position_size"] * 100000 / price  # 默认10万资金
                
                print(f"\n📈 {symbol}: 分数 {signal['score']:.2f}")
                print(f"   建议: 买入 {quantity:.2f}股 @ ${price:.2f}")
                print(f"   金额: ${quantity * price:.2f}")
                
                # 实际执行
                result = self.trader.buy(symbol, quantity=quantity)
                
                if result["status"] == "filled":
                    # 更新持仓
                    self.portfolio.add_position(symbol, quantity, price)
                    print(f"   ✅ 买入成功!")
                else:
                    print(f"   ❌ 买入失败!")
        
        print("\n" + "="*70)
    
    def print_signals(self, signals: Dict[str, dict]):
        """打印信号"""
        print("\n" + "="*70)
        print("📊 交易信号")
        print("="*70)
        
        categorized = {"strong_buy": [], "buy": [], "hold": [], "sell": [], "strong_sell": []}
        for symbol, signal in signals.items():
            categorized[signal["level"]].append(signal)
        
        print(f"\n🟢 强烈买入 ({len(categorized['strong_buy'])} 只):")
        for s in categorized["strong_buy"]:
            print(f"   {s['symbol']}: {s['score']:.2f} | 建仓 {s['position_size']*100:.1f}%")
        
        print(f"\n🟡 买入 ({len(categorized['buy'])} 只):")
        for s in categorized["buy"]:
            print(f"   {s['symbol']}: {s['score']:.2f}")
        
        print(f"\n⚪ 观望 ({len(categorized['hold'])} 只):")
        for s in categorized["hold"]:
            print(f"   {s['symbol']}: {s['score']:.2f}")
        
        print("="*70)
    
    def run(self, mode: str = "signal"):
        """运行系统"""
        print("\n" + "="*70)
        print("🚀 QLib + RD-Agent + Longbridge 交易系统 v2.0")
        print("="*70)
        print(f"模式: {mode}")
        print(f"交易: {'自动' if self.config['execution']['auto_trade'] else '手动'}")
        print(f"资金: ${self.config.get('capital', 100000):,.0f}")
        print("="*70)
        
        # 生成信号
        signals = self.generate_signals()
        
        if mode in ["signal", "full"]:
            # 打印信号
            self.print_signals(signals)
            
            # 更新持仓价格
            for symbol, signal in signals.items():
                self.portfolio.update_price(symbol, signal["price"])
            
            # 打印持仓
            self.portfolio.print_portfolio()
        
        if mode == "full":
            # 执行强烈买入信号
            self.execute_strong_buy_signals(signals)
            
            # 再次打印持仓
            self.portfolio.print_portfolio()


# ============ 命令行界面 ============
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="交易系统 v2.0")
    parser.add_argument("--mode", choices=["signal", "full", "trade"], default="signal",
                       help="运行模式")
    parser.add_argument("--auto", action="store_true",
                       help="开启自动交易")
    parser.add_argument("--buy", type=str, metavar="SYMBOL",
                       help="买入股票")
    parser.add_argument("--sell", type=str, metavar="SYMBOL",
                       help="卖出股票")
    parser.add_argument("--quantity", type=float, default=0.1,
                       help="买入/卖出数量 (比例)")
    
    args = parser.parse_args()
    
    # 创建系统
    config = {
        "execution": {
            "paper_trading": True,
            "auto_trade": args.auto
        }
    }
    
    system = TradingSystem(config)
    
    if args.buy:
        # 买入
        print(f"\n📈 买入 {args.buy}")
        result = system.trader.buy(args.buy, pct=args.quantity)
        if result["status"] == "filled":
            system.portfolio.add_position(args.buy, result["quantity"], result["price"])
            print(f"✅ 买入成功: {result['quantity']:.2f}股 @ ${result['price']:.2f}")
        system.portfolio.print_portfolio()
        
    elif args.sell:
        # 卖出
        print(f"\n📉 卖出 {args.sell}")
        pos = system.portfolio.get_position(args.sell)
        if pos:
            quantity = pos.quantity * args.quantity
            proceeds = system.portfolio.close_position(args.sell, quantity)
            print(f"✅ 卖出成功: {quantity:.2f}股")
        system.portfolio.print_portfolio()
        
    elif args.mode == "trade":
        # 交互模式
        print("\n🛒 交易模式")
        print("命令: buy <代码> [比例], sell <代码> [比例], portfolio, signals, quit")
        
        while True:
            cmd = input("\n> ").strip().split()
            if not cmd:
                continue
            
            if cmd[0] == "quit":
                break
            elif cmd[0] == "portfolio":
                system.portfolio.print_portfolio()
            elif cmd[0] == "signals":
                signals = system.generate_signals()
                system.print_signals(signals)
            elif cmd[0] == "buy" and len(cmd) >= 2:
                symbol = cmd[1].upper()
                pct = float(cmd[2]) if len(cmd) > 2 else 0.1
                result = system.trader.buy(symbol, pct=pct)
                if result["status"] == "filled":
                    system.portfolio.add_position(symbol, result["quantity"], result["price"])
                    print(f"✅ 买入成功")
            elif cmd[0] == "sell" and len(cmd) >= 2:
                symbol = cmd[1].upper()
                pct = float(cmd[2]) if len(cmd) > 2 else 1.0
                pos = system.portfolio.get_position(symbol)
                if pos:
                    quantity = pos.quantity * pct
                    proceeds = system.portfolio.close_position(symbol, quantity)
                    print(f"✅ 卖出成功")
            else:
                print("❌ 未知命令")
    
    else:
        # 信号/完整模式
        system.run(mode=args.mode)


if __name__ == "__main__":
    main()
