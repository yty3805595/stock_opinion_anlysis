#!/usr/bin/env python3
"""
期权交易系统 - EOF 全天候策略期权模块

功能：
1. 监控标的资产，识别期权机会
2. 买入看跌期权 (Put) 用于抄底或对冲
3. 小仓位管理
4. 集成 Longbridge API
"""

import os
import sys
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


# ============ 常量 ============
OPTIONS_FILE = "data/options_portfolio.json"

# 仓位配置
MAX_OPTIONS_PCT = 0.05  # 期权最大仓位 5%
MAX_SINGLE_OPTION_PCT = 0.02  # 单个期权最大 2%
DEFAULT_OPTIONS_PCT = 0.01  # 默认 1%


class OptionType(Enum):
    """期权类型"""
    CALL = "call"
    PUT = "put"


class PositionType(Enum):
    """持仓方向"""
    LONG = "long"
    SHORT = "short"


class StrategyType(Enum):
    """策略类型"""
    HEDGE = "hedge"       # 对冲
    BOTTOM_FISH = "bottom_fish"  # 抄底
    SPECULATE = "speculate"  # 投机


# ============ 数据类 ============
@dataclass
class OptionContract:
    """期权合约"""
    symbol: str           # 标的股票代码 (e.g., QQQ)
    underlying: str       # 期权代码 (e.g., QQQ240315P580)
    option_type: str      # "call" or "put"
    strike_price: float   # 行权价
    expiration: str       # 到期日 (YYYY-MM-DD)
    premium: float       # 权利金
    quantity: int         # 合约数量
    open_date: str       # 开仓日期
    status: str          # "open", "expired", "exercised", "closed"
    
    # 当前数据
    current_price: float  # 当前权利金
    market_value: float  # 市值
    unrealized_pnl: float  # 未实现盈亏
    return_pct: float   # 收益率


@dataclass
class OptionSignal:
    """期权信号"""
    symbol: str           # 标的
    strategy_type: str    # "hedge" or "bottom_fish"
    option_type: str     # "put"
    urgency: str         # "high", "medium", "low"
    strike_price: float  # 建议行权价
    expiration: str      # 建议到期日
    position_size: float # 建议仓位比例
    confidence: float    # 置信度 0-1
    reasoning: str       # 理由


@dataclass
class OptionsPortfolio:
    """期权组合"""
    cash: float                    # 可用现金
    positions: Dict[str, OptionContract]  # 持仓
    total_value: float             # 总价值
    total_pnl: float               # 总盈亏


# ============ 期权分析器 ============
class OptionsAnalyzer:
    """期权分析器"""
    
    # 默认期权参数
    STRIKE_DISCOUNT = {
        "hedge": 0.95,       # 对冲: 略低于现价
        "bottom_fish": 0.90  # 抄底: 低于现价 10%
    }
    
    EXPIRATION_DAYS = {
        "hedge": 30,        # 对冲: 1个月
        "bottom_fish": 60   # 抄底: 2个月
    }
    
    @staticmethod
    def calculate_strike_price(
        current_price: float,
        strategy_type: str,
        direction: str = "below"
    ) -> float:
        """计算建议行权价"""
        if direction == "below":
            # 买入看跌，行权价应该低于现价
            discount = OptionsAnalyzer.STRIKE_DISCOUNT.get(strategy_type, 0.95)
            return round(current_price * discount / 5) * 5  # 5的倍数
        else:
            # 买入看涨，行权价应该高于现价
            premium = 1.05
            return round(current_price * premium / 5) * 5
    
    @staticmethod
    def calculate_expiration(strategy_type: str) -> str:
        """计算建议到期日"""
        days = OptionsAnalyzer.EXPIRATION_DAYS.get(strategy_type, 30)
        expiry = datetime.now() + timedelta(days=days)
        return expiry.strftime("%Y-%m-%d")
    
    @staticmethod
    def estimate_premium(
        underlying_price: float,
        strike_price: float,
        time_to_expiry: float,
        volatility: float = 0.30,
        risk_free_rate: float = 0.05
    ) -> float:
        """估算权利金 (Black-Scholes 简化版)"""
        import math
        
        if time_to_expiry <= 0:
            return max(0, abs(underlying_price - strike_price))
        
        # 简化计算
        intrinsic = max(0, abs(underlying_price - strike_price))
        time_value = underlying_price * volatility * math.sqrt(time_to_expiry/365) * 0.4
        
        return min(intrinsic + time_value, underlying_price * 0.15)
    
    @staticmethod
    def get_option_symbol(symbol: str, expiration: str, 
                          option_type: str, strike: float) -> str:
        """生成期权代码"""
        # 长桥/美股期权代码格式: QQQ240315P580
        date = expiration.replace("-", "")[2:]  # 240315
        type_letter = "P" if option_type == "put" else "C"
        return f"{symbol}{date}{type_letter}{int(strike)}"
    
    @staticmethod
    def analyze_market_condition(
        price: float,
        ma20: float,
        rsi: float,
        volatility: float
    ) -> Dict:
        """分析市场状况"""
        condition = {
            "trend": "neutral",
            "momentum": "neutral",
            "volatility": "normal",
            "recommendation": "wait"
        }
        
        # 趋势判断
        if price > ma20 * 1.02:
            condition["trend"] = "bullish"
        elif price < ma20 * 0.98:
            condition["trend"] = "bearish"
        
        # 动量判断
        if rsi > 70:
            condition["momentum"] = "overbought"
        elif rsi < 30:
            condition["momentum"] = "oversold"
        
        # 波动率判断
        if volatility > 0.4:
            condition["volatility"] = "high"
        elif volatility < 0.2:
            condition["volatility"] = "low"
        
        # 综合建议
        if condition["trend"] == "bearish" and condition["momentum"] == "oversold":
            condition["recommendation"] = "bottom_fish"  # 适合抄底
        elif condition["trend"] == "bullish" and volatility > 0.3:
            condition["recommendation"] = "hedge"  # 适合对冲
        elif condition["volatility"] == "high":
            condition["recommendation"] = "speculate"  # 波动率交易
        
        return condition
    
    @staticmethod
    def generate_put_signal(
        symbol: str,
        current_price: float,
        ma20: float,
        rsi: float,
        volatility: float,
        portfolio_value: float
    ) -> Optional[OptionSignal]:
        """生成看跌期权信号"""
        
        condition = OptionsAnalyzer.analyze_market_condition(
            current_price, ma20, rsi, volatility
        )
        
        # 不满足条件，不建议买入
        if condition["recommendation"] == "wait":
            return None
        
        # 计算参数
        strike = OptionsAnalyzer.calculate_strike_price(
            current_price, 
            condition["recommendation"],
            "below"
        )
        expiration = OptionsAnalyzer.calculate_expiration(condition["recommendation"])
        
        # 计算仓位
        max_size = MAX_SINGLE_OPTION_PCT  # 2%
        min_size = 0.005  # 0.5%
        
        # 根据置信度调整仓位
        confidence = 0.5
        
        if condition["recommendation"] == "bottom_fish":
            # 抄底信号较强
            if rsi < 25:
                confidence = 0.8
            elif rsi < 30:
                confidence = 0.7
            else:
                confidence = 0.6
        elif condition["recommendation"] == "hedge":
            # 对冲信号
            confidence = 0.5 + volatility * 0.5
        
        position_size = min_size + (max_size - min_size) * confidence
        
        # 验证仓位
        position_value = portfolio_value * position_size
        if position_value < 1000:  # 最小1000美元
            position_size = 1000 / portfolio_value
        
        return OptionSignal(
            symbol=symbol,
            strategy_type=condition["recommendation"],
            option_type="put",
            urgency="high" if confidence > 0.7 else "medium",
            strike_price=strike,
            expiration=expiration,
            position_size=position_size,
            confidence=confidence,
            reasoning=f"""
市场状况: {condition['trend']} / {condition['momentum']} / {condition['volatility']}
RSI: {rsi:.1f} | 波动率: {volatility:.1%}
策略: {condition['recommendation']}
置信度: {confidence:.0%}
""".strip()
        )


# ============ 期权持仓管理器 ============
class OptionsPortfolioManager:
    """期权持仓管理器"""
    
    def __init__(self, initial_cash: float = 50000):
        self.portfolio = OptionsPortfolio(
            cash=initial_cash,
            positions={},
            total_value=initial_cash,
            total_pnl=0
        )
        self.file_path = OPTIONS_FILE
        
        Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)
        self.load()
    
    def load(self):
        """加载持仓"""
        if Path(self.file_path).exists():
            with open(self.file_path) as f:
                data = json.load(f)
                self.portfolio.cash = data.get("cash", 50000)
                self.portfolio.positions = {
                    k: OptionContract(**v) 
                    for k, v in data.get("positions", {}).items()
                }
                self.portfolio.total_value = data.get("total_value", self.portfolio.cash)
                self.portfolio.total_pnl = data.get("total_pnl", 0)
    
    def save(self):
        """保存持仓"""
        data = {
            "cash": self.portfolio.cash,
            "positions": {k: asdict(v) for k, v in self.portfolio.positions.items()},
            "total_value": self.portfolio.total_value,
            "total_pnl": self.portfolio.total_pnl,
            "last_update": datetime.now().isoformat()
        }
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def open_position(
        self,
        symbol: str,
        option_type: str,
        strike_price: float,
        expiration: str,
        quantity: int,
        premium: float,
        current_price: float = None
    ) -> Tuple[bool, str]:
        """开仓"""
        option_symbol = OptionsAnalyzer.get_option_symbol(
            symbol, expiration, option_type, strike_price
        )
        
        cost = premium * quantity * 100  # 1合约=100股
        
        if cost > self.portfolio.cash:
            return False, f"现金不足: ${self.portfolio.cash:.2f} < ${cost:.2f}"
        
        self.portfolio.cash -= cost
        
        contract = OptionContract(
            symbol=symbol,
            underlying=option_symbol,
            option_type=option_type,
            strike_price=strike_price,
            expiration=expiration,
            premium=premium,
            quantity=quantity,
            open_date=datetime.now().strftime("%Y-%m-%d"),
            status="open",
            current_price=current_price or premium,
            market_value=cost,
            unrealized_pnl=0,
            return_pct=0
        )
        
        self.portfolio.positions[option_symbol] = contract
        self.recalculate()
        self.save()
        
        return True, f"开仓成功: {option_symbol} @ ${premium}"
    
    def close_position(self, option_symbol: str, 
                       quantity: int = None) -> Tuple[bool, str]:
        """平仓"""
        if option_symbol not in self.portfolio.positions:
            return False, f"未找到持仓: {option_symbol}"
        
        contract = self.portfolio.positions[option_symbol]
        close_qty = min(quantity or contract.quantity, contract.quantity)
        
        # 模拟按当前价格平仓
        proceeds = contract.current_price * close_qty * 100
        self.portfolio.cash += proceeds
        
        if close_qty >= contract.quantity:
            del self.portfolio.positions[option_symbol]
        else:
            contract.quantity -= close_qty
            self.portfolio.positions[option_symbol] = contract
        
        self.recalculate()
        self.save()
        
        return True, f"平仓成功: {option_symbol} @ ${contract.current_price}"
    
    def update_prices(self, prices: Dict[str, float]):
        """更新价格"""
        for symbol, price in prices.items():
            for contract in self.portfolio.positions.values():
                if contract.symbol == symbol:
                    contract.current_price = price
                    self.recalculate_contract(contract)
        
        self.save()
    
    def recalculate(self):
        """重新计算组合"""
        total_value = self.portfolio.cash
        total_pnl = 0
        
        for contract in self.portfolio.positions.values():
            self.recalculate_contract(contract)
            total_value += contract.market_value
            total_pnl += contract.unrealized_pnl
        
        self.portfolio.total_value = total_value
        self.portfolio.total_pnl = total_pnl
    
    def recalculate_contract(self, contract: OptionContract):
        """重新计算单个合约"""
        contract.market_value = contract.current_price * contract.quantity * 100
        cost = contract.premium * contract.quantity * 100
        contract.unrealized_pnl = contract.market_value - cost
        contract.return_pct = contract.unrealized_pnl / cost * 100 if cost > 0 else 0
    
    def get_summary(self) -> Dict:
        """获取汇总"""
        return {
            "cash": self.portfolio.cash,
            "positions_count": len(self.portfolio.positions),
            "total_value": self.portfolio.total_value,
            "total_pnl": self.portfolio.total_pnl,
            "pnl_pct": self.portfolio.total_pnl / (self.portfolio.total_value - self.portfolio.total_pnl) * 100 
                      if self.portfolio.total_value > self.portfolio.total_pnl else 0
        }
    
    def print_portfolio(self):
        """打印组合"""
        print("\n" + "="*70)
        print("📊 期权组合")
        print("="*70)
        
        summary = self.get_summary()
        
        print(f"\n💰 现金: ${self.portfolio.cash:,.2f}")
        print(f"📈 总价值: ${summary['total_value']:,.2f}")
        print(f"💵 总盈亏: ${summary['total_pnl']:,.2f} ({summary['pnl_pct']:.2f}%)")
        
        if not self.portfolio.positions:
            print("\n  无持仓")
            return
        
        print(f"\n{'代码':<15} {'标的':<6} {'类型':<6} {'行权价':<10} {'数量':<6} {'成本':<10} {'市价':<10} {'盈亏':<12}")
        print("-"*90)
        
        for contract in self.portfolio.positions.values():
            pnl_str = f"+${contract.unrealized_pnl:.2f}" if contract.unrealized_pnl >= 0 else f"-${abs(contract.unrealized_pnl):.2f}"
            
            print(f"{contract.underlying:<15} {contract.symbol:<6} {contract.option_type:<6} "
                  f"${contract.strike_price:<9.2f} {contract.quantity:<6} ${contract.premium:<9.2f} "
                  f"${contract.current_price:<9.2f} {pnl_str:<12}")
        
        print("="*70)


# ============ 主系统 ============
class OptionsTradingSystem:
    """期权交易系统"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.portfolio = OptionsPortfolioManager(
            self.config.get("initial_cash", 50000)
        )
        self.analyzer = OptionsAnalyzer()
    
    def analyze_underlying(self, symbol: str, 
                           data: Dict) -> Optional[OptionSignal]:
        """分析标的并生成信号"""
        current_price = data.get("price", 100)
        ma20 = data.get("ma20", current_price)
        rsi = data.get("rsi", 50)
        volatility = data.get("volatility", 0.3)
        portfolio_value = self.portfolio.get_summary()["total_value"]
        
        return self.analyzer.generate_put_signal(
            symbol, current_price, ma20, rsi, volatility, portfolio_value
        )
    
    def execute_signal(self, signal: OptionSignal, 
                       current_premium: float = None) -> Tuple[bool, str]:
        """执行信号"""
        if not signal:
            return False, "无信号"
        
        # 估算权利金
        if current_premium is None:
            time_to_expiry = (datetime.strptime(signal.expiration, "%Y-%m-%d") - datetime.now()).days
            current_premium = self.analyzer.estimate_premium(
                100, signal.strike_price, time_to_expiry  # 简化
            )
        
        # 计算数量 (每张合约100股)
        position_value = 50000 * signal.position_size  # 默认5万基准
        quantity = max(1, int(position_value / (current_premium * 100)))
        
        return self.portfolio.open_position(
            symbol=signal.symbol,
            option_type=signal.option_type,
            strike_price=signal.strike_price,
            expiration=signal.expiration,
            quantity=quantity,
            premium=current_premium
        )
    
    def run_analysis(self, symbols_data: Dict[str, Dict]) -> List[OptionSignal]:
        """运行分析"""
        signals = []
        
        for symbol, data in symbols_data.items():
            signal = self.analyze_underlying(symbol, data)
            if signal:
                signals.append(signal)
        
        return signals
    
    def print_signals(self, signals: List[OptionSignal]):
        """打印信号"""
        if not signals:
            print("\n📭 当前无期权信号")
            return
        
        print("\n" + "="*70)
        print("📊 期权信号")
        print("="*70)
        
        for signal in signals:
            emoji = "🔥" if signal.urgency == "high" else "📌"
            
            print(f"\n{emoji} {signal.symbol} - {signal.strategy_type.upper()}")
            print(f"   期权: Put @ ${signal.strike_price}")
            print(f"   到期: {signal.expiration}")
            print(f"   仓位: {signal.position_size*100:.2f}%")
            print(f"   置信度: {signal.confidence*100:.0f}%")
            print(f"   理由: {signal.reasoning}")
        
        print("\n" + "="*70)


# ============ 测试 ============
def main():
    """测试"""
    print("="*70)
    print("🧪 期权交易系统测试")
    print("="*70)
    
    # 创建系统
    system = OptionsTradingSystem({"initial_cash": 50000})
    
    # 测试信号生成
    print("\n📊 测试信号生成...")
    
    test_data = {
        "QQQ": {"price": 580, "ma20": 600, "rsi": 25, "volatility": 0.35},
        "NVDA": {"price": 180, "ma20": 185, "rsi": 45, "volatility": 0.40},
        "TSLA": {"price": 400, "ma20": 420, "rsi": 30, "volatility": 0.50},
    }
    
    signals = system.run_analysis(test_data)
    system.print_signals(signals)
    
    # 测试执行
    if signals:
        print("\n📝 测试执行信号...")
        for signal in signals[:1]:
            success, msg = system.execute_signal(signal)
            print(f"   {msg}")
    
    # 打印组合
    system.portfolio.print_portfolio()
    
    print("\n✅ 测试完成!")


if __name__ == "__main__":
    main()
