#!/usr/bin/env python3
"""
RD-Agent 期权交易系统 v1.0

结合 RD-Agent 三阶段架构：
- Research: Polymarket情绪 + Tavily新闻 + 技术分析
- Develop: 策略生成 + 信号计算
- Feedback: 绩效评估 + 策略优化
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
RD_SIGNALS_FILE = "data/rd_agent_signals.json"

# 真实期权参数 (从 LongbridgeOptionsClient 导入)
OPTION_PARAMS = {
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


def get_option_params(symbol: str) -> Dict:
    """获取期权参数"""
    return OPTION_PARAMS.get(symbol, OPTION_PARAMS["QQQ"])


def calculate_realistic_option(symbol: str, strategy: str, current_price: float) -> Dict:
    """计算真实期权参数"""
    params = get_option_params(symbol)
    
    if strategy == "hedge":
        strike = round(current_price * 0.95 / params["strike_multiplier"]) * params["strike_multiplier"]
        premium = params["min_premium"] + current_price * 0.02
        days = 30
    elif strategy == "bottom_fish":
        strike = round(current_price * 0.90 / params["strike_multiplier"]) * params["strike_multiplier"]
        premium = params["min_premium"] + current_price * 0.03
        days = 60
    else:
        strike = round(current_price * 0.92 / params["strike_multiplier"]) * params["strike_multiplier"]
        premium = params["min_premium"] + current_price * 0.025
        days = 30
    
    premium = round(premium, 2)
    
    expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    expiry_code = expiry.replace("-", "")[2:]
    option_code = f"{symbol}{expiry_code}P{int(strike)}"
    
    return {
        "option_code": option_code,
        "strike": strike,
        "premium": premium,
        "total_cost": premium * params["contract_size"],
        "expiration": expiry,
        "days": days
    }


class OptionType(Enum):
    """期权类型"""
    CALL = "call"
    PUT = "put"


class StrategyType(Enum):
    """策略类型"""
    HEDGE = "hedge"
    BOTTOM_FISH = "bottom_fish"
    SPECULATE = "speculate"


# ============ RD-Agent 数据结构 ============
@dataclass
class RDResearchResult:
    """RD-Agent Research 结果"""
    symbol: str
    polymarket_sentiment: float        # Polymarket 情绪 (0-1)
    news_sentiment: float              # Tavily 新闻情绪 (0-1)
    technical_score: float             # 技术分析分数 (0-1)
    fundamental_score: float            # 基本面分数 (0-1)
    risk_level: str                   # "low", "medium", "high"
    event_risk: float                 # 事件风险 (0-1)
    timestamp: str


@dataclass
class RDDevelopResult:
    """RD-Agent Develop 结果"""
    symbol: str
    strategy_type: str                # "hedge", "bottom_fish", "speculate"
    option_type: str                 # "put" (看跌)
    strike_price: float
    expiration_days: int
    position_size: float
    confidence: float
    reasoning: str
    rd_score: float                  # 综合RD分数
    timestamp: str


@dataclass
class OptionPosition:
    """期权持仓"""
    symbol: str
    underlying: str
    option_type: str
    strike_price: float
    expiration: str
    premium: float
    quantity: int
    open_date: str
    status: str
    rd_strategy: str                 # RD策略类型
    rd_confidence: float            # RD置信度
    current_price: float
    market_value: float
    unrealized_pnl: float
    return_pct: float


# ============ RD-Agent Research 模块 ============
class RDResearchAgent:
    """
    RD-Agent Research 模块
    
    收集多源数据进行分析
    """
    
    def __init__(self):
        self.polymarket_data = {}
        self.news_data = {}
        self.technical_data = {}
    
    def fetch_polymarket_sentiment(self, symbol: str) -> float:
        """获取 Polymarket 情绪"""
        # 模拟 Polymarket 数据
        # 实际应该调用 Polymarket API
        
        # Fed 相关市场情绪
        fed_sensitive = ["QQQ", "SPY", "IWM"]
        
        if symbol in fed_sensitive:
            # Fed 3月维持利率概率 99%
            return 0.99  # 高概率市场稳定
        else:
            # 其他股票
            return random.uniform(0.4, 0.6)
    
    def fetch_news_sentiment(self, symbol: str) -> float:
        """获取 Tavily 新闻情绪"""
        # 模拟 Tavily 新闻数据
        # 实际应该调用 Tavily API
        
        news_sentiment = {
            "QQQ": 0.55,   # AI/科技热点
            "NVDA": 0.70,  # AI芯片龙头，热点
            "TSLA": 0.45,  # 新能源车，争议
            "GOOGL": 0.50, # 稳定
            "MSFT": 0.60,  # AI/OpenAI
            "AAPL": 0.55,  # 稳定
            "AMD": 0.65,   # AI芯片
            "META": 0.50,  # 稳定
            "AMZN": 0.55,  # 电商+云
            "PLTR": 0.40,  # AI数据，波动大
        }
        
        return news_sentiment.get(symbol, 0.50)
    
    def analyze_technical(self, symbol: str, 
                          price: float, ma20: float, 
                          rsi: float, volatility: float) -> Dict:
        """技术分析"""
        # 趋势
        if price > ma20 * 1.02:
            trend = "bullish"
        elif price < ma20 * 0.98:
            trend = "bearish"
        else:
            trend = "neutral"
        
        # 动量
        if rsi > 70:
            momentum = "overbought"
        elif rsi < 30:
            momentum = "oversold"
        else:
            momentum = "neutral"
        
        # 波动率
        if volatility > 0.4:
            vol_regime = "high"
        elif volatility < 0.2:
            vol_regime = "low"
        else:
            vol_regime = "normal"
        
        # 技术分数
        score = 0.5
        if trend == "bullish":
            score += 0.15
        elif trend == "bearish":
            score -= 0.15
        
        if momentum == "oversold":
            score += 0.1
        elif momentum == "overbought":
            score -= 0.1
        
        if vol_regime == "high":
            score += 0.05
        
        return {
            "trend": trend,
            "momentum": momentum,
            "volatility": vol_regime,
            "score": max(0, min(1, score))
        }
    
    def analyze_fundamental(self, symbol: str) -> Dict:
        """基本面分析"""
        # 模拟基本面数据
        fundamentals = {
            "QQQ": {"score": 0.70, "pe": 35, "growth": 0.25},
            "NVDA": {"score": 0.85, "pe": 60, "growth": 0.50},
            "TSLA": {"score": 0.50, "pe": 50, "growth": 0.30},
            "GOOGL": {"score": 0.65, "pe": 25, "growth": 0.15},
            "MSFT": {"score": 0.70, "pe": 35, "growth": 0.20},
            "AAPL": {"score": 0.65, "pe": 28, "growth": 0.10},
            "AMD": {"score": 0.60, "pe": 40, "growth": 0.25},
            "META": {"score": 0.55, "pe": 22, "growth": 0.15},
            "AMZN": {"score": 0.60, "pe": 50, "growth": 0.25},
            "PLTR": {"score": 0.45, "pe": 80, "growth": 0.40},
        }
        
        data = fundamentals.get(symbol, {"score": 0.50, "pe": 25, "growth": 0.10})
        
        return {
            "score": data["score"],
            "pe_ratio": data["pe"],
            "growth_rate": data["growth"]
        }
    
    def research(self, symbol: str, price: float, ma20: float,
                rsi: float, volatility: float) -> RDResearchResult:
        """
        执行 Research 阶段
        
        整合多源数据：
        - Polymarket 情绪
        - Tavily 新闻
        - 技术分析
        - 基本面
        """
        # 1. 获取 Polymarket 情绪
        polymarket = self.fetch_polymarket_sentiment(symbol)
        
        # 2. 获取新闻情绪
        news = self.fetch_news_sentiment(symbol)
        
        # 3. 技术分析
        technical = self.analyze_technical(symbol, price, ma20, rsi, volatility)
        
        # 4. 基本面分析
        fundamental = self.analyze_fundamental(symbol)
        
        # 5. 计算事件风险
        # Fed 会议临近，政策风险
        event_risk = 0.1 if volatility > 0.3 else 0.05
        
        # 6. 综合风险评估
        risk_factors = []
        
        if technical["trend"] == "bearish":
            risk_factors.append("下降趋势")
        if technical["momentum"] == "oversold":
            risk_factors.append("超卖")
        if volatility > 0.4:
            risk_factors.append("高波动")
        
        if len(risk_factors) >= 3:
            risk_level = "high"
        elif len(risk_factors) >= 1:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return RDResearchResult(
            symbol=symbol,
            polymarket_sentiment=polymarket,
            news_sentiment=news,
            technical_score=technical["score"],
            fundamental_score=fundamental["score"],
            risk_level=risk_level,
            event_risk=event_risk,
            timestamp=datetime.now().isoformat()
        )


# ============ RD-Agent Develop 模块 ============
class RDDevelopAgent:
    """
    RD-Agent Develop 模块
    
    根据 Research 结果生成交易策略
    """
    
    # 权重配置 (无 Polymarket)
    WEIGHTS = {
        "news": 0.25,
        "technical": 0.40,
        "fundamental": 0.35
    }
    
    # 策略映射
    STRATEGY_MAP = {
        ("bearish", "oversold", "high"): "hedge",
        ("bearish", "oversold", "normal"): "bottom_fish",
        ("bearish", "neutral", "high"): "hedge",
        ("neutral", "oversold", "normal"): "bottom_fish",
        ("bearish", "neutral", "normal"): "hedge",
        ("neutral", "neutral", "high"): "speculate",
    }
    
    def develop(self, research: RDResearchResult) -> RDDevelopResult:
        """
        执行 Develop 阶段
        
        根据 Research 结果生成期权策略
        """
        symbol = research.symbol
        
        # 1. 计算综合 RD 分数 (无 Polymarket)
        rd_score = (
            research.news_sentiment * self.WEIGHTS["news"] +
            research.technical_score * self.WEIGHTS["technical"] +
            research.fundamental_score * self.WEIGHTS["fundamental"]
        )
        
        # 2. 确定策略类型
        strategy = self._determine_strategy(research)
        
        # 3. 计算期权参数
        params = self._calculate_option_params(research, strategy)
        
        # 4. 生成理由
        reasoning = self._generate_reasoning(research, strategy, rd_score)
        
        return RDDevelopResult(
            symbol=symbol,
            strategy_type=strategy,
            option_type="put",  # 看跌期权
            strike_price=params["strike"],
            expiration_days=params["expiration"],
            position_size=params["position_size"],
            confidence=params["confidence"],
            reasoning=reasoning,
            rd_score=rd_score,
            timestamp=datetime.now().isoformat()
        )
    
    def _determine_strategy(self, research: RDResearchResult) -> str:
        """确定策略类型"""
        trend = research.technical_score < 0.45 and "bearish" or "neutral"
        if research.technical_score > 0.55:
            trend = "bullish"
        
        momentum = "oversold" if research.technical_score < 0.4 else "neutral"
        if research.technical_score > 0.6:
            momentum = "overbought"
        
        vol = "high" if research.event_risk > 0.2 else "normal"
        if research.polymarket_sentiment < 0.4:
            vol = "high"
        
        # 匹配策略
        for (t, m, v), strategy in self.STRATEGY_MAP.items():
            if (t == "_" or t == trend) and (m == "_" or m == momentum) and (v == "_" or v == vol):
                return strategy
        
        return "hedge"
    
    def _calculate_option_params(self, research: RDResearchResult, 
                                 strategy: str) -> Dict:
        """计算期权参数"""
        base_price = 100  # 标准化价格
        
        # 行权价
        if strategy == "hedge":
            strike = base_price * 0.95
        elif strategy == "bottom_fish":
            strike = base_price * 0.88
        else:
            strike = base_price * 0.92
        
        # 到期日
        expiration_map = {
            "hedge": 30,
            "bottom_fish": 60,
            "speculate": 21
        }
        expiration = expiration_map.get(strategy, 30)
        
        # 仓位
        base_size = 0.01  # 1%
        
        if research.risk_level == "high":
            position_size = base_size * 0.5  # 减仓
        elif research.risk_level == "low":
            position_size = base_size * 1.5  # 加仓
        else:
            position_size = base_size
        
        # 置信度 (无 Polymarket)
        confidence = 0.5 + research.news_sentiment * 0.5
        
        return {
            "strike": round(strike / 5) * 5,
            "expiration": expiration,
            "position_size": min(position_size, 0.03),
            "confidence": confidence
        }
    
    def _generate_reasoning(self, research: RDResearchResult, 
                           strategy: str, rd_score: float) -> str:
        """生成交易理由 (无 Polymarket)"""
        reasons = []
        
        # 新闻
        if research.news_sentiment > 0.6:
            reasons.append(f"新闻正面 ({research.news_sentiment:.0%})")
        elif research.news_sentiment < 0.4:
            reasons.append(f"新闻负面 ({research.news_sentiment:.0%})")
        
        # 技术
        if research.technical_score > 0.6:
            reasons.append("技术面偏强")
        elif research.technical_score < 0.4:
            reasons.append("技术面偏弱")
        
        # 风险
        reasons.append(f"风险等级: {research.risk_level}")
        
        return " | ".join(reasons)


# ============ 期权执行模块 ============
class RDOptionsTrader:
    """
    RD-Agent 期权交易系统
    
    整合 Research + Develop + Execution
    """
    
    def __init__(self, initial_cash: float = 50000):
        self.research_agent = RDResearchAgent()
        self.develop_agent = RDDevelopAgent()
        
        self.cash = initial_cash
        self.positions: Dict[str, OptionPosition] = {}
        self.trade_history: List[Dict] = []
        
        Path(OPTIONS_FILE).parent.mkdir(parents=True, exist_ok=True)
        self.load()
    
    def load(self):
        """加载持仓"""
        if Path(OPTIONS_FILE).exists():
            with open(OPTIONS_FILE) as f:
                data = json.load(f)
                self.cash = data.get("cash", 50000)
                self.positions = {}
                for k, v in data.get("positions", {}).items():
                    # 兼容旧数据
                    v.setdefault("rd_strategy", "unknown")
                    v.setdefault("rd_confidence", 0.5)
                    self.positions[k] = OptionPosition(**v)
    
    def save(self):
        """保存持仓"""
        data = {
            "cash": self.cash,
            "positions": {k: asdict(v) for k, v in self.positions.items()},
            "trade_history": self.trade_history,
            "last_update": datetime.now().isoformat()
        }
        with open(OPTIONS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    
    def analyze_symbol(self, symbol: str, price: float, ma20: float,
                      rsi: float, volatility: float) -> RDDevelopResult:
        """分析单个标的"""
        # Research 阶段
        research = self.research_agent.research(symbol, price, ma20, rsi, volatility)
        
        # Develop 阶段
        strategy = self.develop_agent.develop(research)
        
        return strategy
    
    def execute_strategy(self, strategy: RDDevelopResult, 
                        current_price: float = None) -> Tuple[bool, str]:
        """执行策略 - 使用真实期权参数"""
        symbol = strategy.symbol
        
        # 使用真实期权参数 (当前价格)
        option = calculate_realistic_option(
            symbol, 
            strategy.strategy_type, 
            current_price or 100
        )
        
        # 成本
        cost = option["total_cost"]
        
        # 验证资金
        if cost > self.cash:
            return False, f"现金不足: ${self.cash:.2f} < ${cost:.2f}"
        
        # 开仓
        self.cash -= cost
        
        position = OptionPosition(
            symbol=symbol,
            underlying=option["option_code"],
            option_type=strategy.option_type,
            strike_price=option["strike"],
            expiration=option["expiration"],
            premium=option["premium"],
            quantity=1,  # 1张合约
            open_date=datetime.now().strftime("%Y-%m-%d"),
            status="open",
            rd_strategy=strategy.strategy_type,
            rd_confidence=strategy.confidence,
            current_price=option["premium"],
            market_value=cost,
            unrealized_pnl=0,
            return_pct=0
        )
        
        self.positions[option["option_code"]] = position
        self.save()
        
        return True, f"✅ 开仓: {option['option_code']} | {strategy.strategy_type.upper()} | ${cost:.2f} | 置信度: {strategy.confidence:.0%}"
    
    def close_position(self, underlying: str) -> Tuple[bool, str]:
        """平仓"""
        if underlying not in self.positions:
            return False, f"未找到: {underlying}"
        
        position = self.positions[underlying]
        proceeds = position.current_price * position.quantity * 100
        
        self.cash += proceeds
        
        del self.positions[underlying]
        self.save()
        
        return True, f"✅ 平仓: {underlying} | 收回: ${proceeds:.2f}"
    
    def analyze_all(self, market_data: Dict[str, Dict]) -> List[RDDevelopResult]:
        """分析所有标的"""
        strategies = []
        
        for symbol, data in market_data.items():
            strategy = self.analyze_symbol(
                symbol,
                data.get("price", 100),
                data.get("ma20", 100),
                data.get("rsi", 50),
                data.get("volatility", 0.3)
            )
            strategies.append(strategy)
        
        return strategies
    
    def print_report(self, strategies: List[RDDevelopResult]):
        """打印报告"""
        print("\n" + "="*70)
        print("🤖 RD-Agent 期权交易报告")
        print("="*70)
        
        # 过滤有效的策略
        valid_strategies = [s for s in strategies if s.rd_score > 0.4]
        
        if not valid_strategies:
            print("\n📭 无有效期权信号")
            return
        
        print(f"\n📊 信号 ({len(valid_strategies)} 只)")
        print("-"*70)
        
        for s in sorted(valid_strategies, key=lambda x: -x.rd_score):
            emoji = {
                "hedge": "🛡️",
                "bottom_fish": "🎣",
                "speculate": "📊"
            }.get(s.strategy_type, "📌")
            
            print(f"\n{emoji} {s.symbol} - {s.strategy_type.upper()}")
            print(f"   RD Score: {s.rd_score:.2f} | 置信度: {s.confidence:.0%}")
            print(f"   期权: Put @ ${s.strike_price:.0f}")
            print(f"   到期: {s.expiration_days}天后")
            print(f"   仓位: {s.position_size*100:.2f}%")
            print(f"   理由: {s.reasoning}")
        
        # 当前持仓
        if self.positions:
            print(f"\n📈 当前持仓 ({len(self.positions)} 只)")
            print("-"*70)
            total_value = sum(p.market_value for p in self.positions.values())
            total_pnl = sum(p.unrealized_pnl for p in self.positions.values())
            
            for pos in self.positions.values():
                print(f"   {pos.underlying}: {pos.rd_strategy} | ${pos.market_value:.0f} | {pos.return_pct:.1f}%")
            
            print(f"\n   💰 现金: ${self.cash:,.0f}")
            print(f"   📊 总价值: ${self.cash + total_value:,.0f}")
            print(f"   💵 盈亏: ${total_pnl:,.0f}")
        
        print("\n" + "="*70)


# ============ 测试 ============
def main():
    """测试"""
    print("="*70)
    print("🧪 RD-Agent 期权交易系统测试")
    print("="*70)
    
    # 创建系统
    trader = RDOptionsTrader(50000)
    
    # 市场数据
    market_data = {
        "QQQ": {"price": 580, "ma20": 600, "rsi": 25, "volatility": 0.35},
        "NVDA": {"price": 180, "ma20": 185, "rsi": 45, "volatility": 0.40},
        "TSLA": {"price": 400, "ma20": 420, "rsi": 28, "volatility": 0.50},
        "GOOGL": {"price": 170, "ma20": 175, "rsi": 40, "volatility": 0.30},
        "MSFT": {"price": 400, "ma20": 405, "rsi": 35, "volatility": 0.25},
    }
    
    # 分析
    strategies = trader.analyze_all(market_data)
    trader.print_report(strategies)
    
    # 执行 Top 1
    if strategies:
        best = max(strategies, key=lambda x: x.rd_score)
        if best.rd_score > 0.55:
            print(f"\n📝 执行最佳策略: {best.symbol}")
            success, msg = trader.execute_strategy(best)
            print(f"   {msg}")
    
    trader.print_report([])


if __name__ == "__main__":
    main()
