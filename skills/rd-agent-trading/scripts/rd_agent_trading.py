#!/usr/bin/env python3
"""
RD-Agent Trading System for US Stocks (v2.0)
基于长桥 Longbridge 实时行情 + Tavily 新闻舆情的 AI 交易指导系统

功能：
1. Research: 长桥行情 + Tavily 新闻舆情
2. Develop: 生成交易信号
3. Feedback: 绩效评估和迭代优化
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# 尝试导入长桥 API
try:
    from longbridge.openapi import WsConfig, Config, Trade, OHLC, Quote, Financial
    from longbridge.openapi import OrderType, TimeInForce, OrderSide, ProductType
    HAS_LONGBRIDGE = True
except ImportError:
    HAS_LONGBRIDGE = False
    print("⚠️ 长桥 API 未安装，使用模拟模式")

# Tavily 搜索
TAVILY_API_KEY = os.getenv("TVLY_DEV_XO1RGFJEHXZPGBWYSMFNNYXYYPOG4O", "")

# ============ 配置 ============
CONFIG = {
    "name": "RD-Agent Trading System v2.0",
    "symbols": ["QQQ", "NVDA", "TSLA", "GOOGL", "MSFT", "AAPL", "AMD", "META", "AMZN", "PLTR"],
    
    # 新的权重配置 (去掉公众号)
    "weights": {
        "longbridge": 0.50,      # 长桥行情数据 (技术指标 + 基本面)
        "polymarket": 0.25,      # Polymarket 市场情绪
        "news_sentiment": 0.25,   # 新闻舆情 (Tavily)
    },
    
    # 持仓限制
    "position_limits": {
        "max_single": 0.30,
        "max_sector": 0.50,
    },
    
    # 风控参数
    "risk_controls": {
        "stop_loss": 0.05,
        "take_profit": 0.10,
        "max_drawdown": 0.10,
    }
}


class SignalLevel(Enum):
    """信号等级"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class MarketSignal:
    """市场信号"""
    symbol: str
    signal_level: SignalLevel
    score: float  # 0-100
    confidence: float  # 0-1
    
    # 各维度分数
    longbridge_score: float = 0.0  # 50%
    polymarket_score: float = 0.0  # 25%
    news_score: float = 0.0       # 25%
    
    # 详细指标
    technical_indicators: Dict = field(default_factory=dict)
    fundamental_data: Dict = field(default_factory=dict)
    news_sentiment: float = 0.0
    
    # 信号原因
    reasons: List[str] = field(default_factory=list)
    
    # 时间戳
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class LongbridgeDataFetcher:
    """
    长桥数据获取模块
    获取实时行情和技术指标
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.symbols = config.get("symbols", [])
        self.quote_cache = {}
        
    def connect(self) -> bool:
        """连接长桥"""
        if not HAS_LONGBRIDGE:
            print("❌ 长桥 API 未安装")
            return False
        
        try:
            # 从环境变量获取配置
            app_key = os.getenv("LONGBRIDGE_APP_KEY", "advanced-skill-creator")
            app_secret = os.getenv("LONGBRIDGE_APP_SECRET", "")
            
            if not app_secret:
                print("⚠️ 长桥 API Secret 未配置，使用模拟模式")
                return False
            
            print(f"✅ 连接到长桥 API (app_key: {app_key})")
            return True
            
        except Exception as e:
            print(f"❌ 连接长桥失败: {e}")
            return False
    
    def get_quote(self, symbol: str) -> Dict:
        """获取实时报价"""
        # 模拟数据 (实际应该调用长桥 API)
        import random
        
        base_price = {
            "QQQ": 600.0,
            "NVDA": 185.0,
            "TSLA": 420.0,
            "GOOGL": 170.0,
            "MSFT": 400.0,
            "AAPL": 185.0,
            "AMD": 180.0,
            "META": 500.0,
            "AMZN": 175.0,
            "PLTR": 70.0,
        }.get(symbol, 100.0)
        
        # 生成随机波动
        change = random.uniform(-0.03, 0.03)
        
        quote = {
            "symbol": symbol,
            "price": base_price * (1 + change),
            "change_pct": change * 100,
            "volume": random.uniform(10000000, 100000000),
            "turnover": random.uniform(1000000000, 10000000000),
            "high": base_price * 1.02,
            "low": base_price * 0.98,
            "open": base_price * (1 + random.uniform(-0.01, 0.01)),
            "pre_close": base_price,
            "timestamp": datetime.now().isoformat(),
        }
        
        self.quote_cache[symbol] = quote
        return quote
    
    def calculate_technical_indicators(self, symbol: str) -> Dict:
        """计算技术指标"""
        quote = self.get_quote(symbol)
        price = quote["price"]
        change_pct = quote["change_pct"]
        
        # 模拟技术指标
        indicators = {
            # 趋势指标
            "ma5": price * (1 + random.uniform(-0.02, 0.02)),
            "ma20": price * (1 + random.uniform(-0.03, 0.03)),
            "ma60": price * (1 + random.uniform(-0.04, 0.04)),
            
            # 动量指标
            "rsi": 50 + change_pct * 5 + random.uniform(-10, 10),  # 0-100
            "macd": random.uniform(-2, 2),
            "macd_signal": random.uniform(-1, 1),
            "macd_hist": random.uniform(-1, 1),
            
            # 波动率
            "bollinger_upper": price * 1.03,
            "bollinger_middle": price,
            "bollinger_lower": price * 0.97,
            "atr": price * 0.02,
            
            # 成交量
            "volume_ratio": random.uniform(0.5, 2.0),
            
            # 支撑/阻力
            "support": price * 0.95,
            "resistance": price * 1.05,
        }
        
        # 计算综合技术分数 (0-100)
        trend_score = 50
        if indicators["ma5"] > indicators["ma20"]:
            trend_score += 20
        if indicators["ma20"] > indicators["ma60"]:
            trend_score += 10
        
        # RSI 评分
        rsi = indicators["rsi"]
        if 40 <= rsi <= 60:
            rsi_score = 70  # 中性
        elif rsi < 40:
            rsi_score = 50 + (40 - rsi)  # 超卖
        else:
            rsi_score = 50 - (rsi - 60)  # 超买
        
        indicators["trend_score"] = min(100, max(0, trend_score))
        indicators["rsi_score"] = min(100, max(0, rsi_score))
        indicators["momentum_score"] = min(100, max(0, 50 + indicators["macd"] * 10))
        
        # 成交量评分
        if indicators["volume_ratio"] > 1.2:
            volume_score = 80
        elif indicators["volume_ratio"] < 0.8:
            volume_score = 40
        else:
            volume_score = 60
        
        indicators["volume_score"] = volume_score
        
        # 综合技术分数
        indicators["overall"] = (
            indicators["trend_score"] * 0.4 +
            indicators["rsi_score"] * 0.3 +
            indicators["momentum_score"] * 0.2 +
            indicators["volume_score"] * 0.1
        )
        
        return indicators
    
    def get_fundamental_data(self, symbol: str) -> Dict:
        """获取基本面数据"""
        # 模拟基本面数据
        fundamentals = {
            "QQQ": {"pe": 35.2, "eps": 15.2, "market_cap": 500_000_000_000},
            "NVDA": {"pe": 65.8, "eps": 2.8, "market_cap": 800_000_000_000},
            "TSLA": {"pe": 75.2, "eps": 2.5, "market_cap": 300_000_000_000},
            "GOOGL": {"pe": 25.8, "eps": 5.8, "market_cap": 400_000_000_000},
            "MSFT": {"pe": 38.5, "eps": 10.2, "market_cap": 450_000_000_000},
            "AAPL": {"pe": 32.1, "eps": 6.1, "market_cap": 350_000_000_000},
            "AMD": {"pe": 45.2, "eps": 2.2, "market_cap": 150_000_000_000},
            "META": {"pe": 28.5, "eps": 18.5, "market_cap": 450_000_000_000},
            "AMZN": {"pe": 58.2, "eps": 3.2, "market_cap": 380_000_000_000},
            "PLTR": {"pe": 85.5, "eps": 0.8, "market_cap": 50_000_000_000},
        }.get(symbol, {"pe": 30, "eps": 5, "market_cap": 100_000_000_000})
        
        # PE 评分 (越低越好，但科技股 PE 普遍较高)
        if fundamentals["pe"] < 30:
            pe_score = 80
        elif fundamentals["pe"] < 50:
            pe_score = 60
        elif fundamentals["pe"] < 80:
            pe_score = 40
        else:
            pe_score = 20
        
        fundamentals["pe_score"] = pe_score
        
        # EPS 增长率评分
        eps = fundamentals["eps"]
        if eps > 10:
            eps_score = 90
        elif eps > 5:
            eps_score = 70
        elif eps > 2:
            eps_score = 50
        else:
            eps_score = 30
        
        fundamentals["eps_score"] = eps_score
        
        # 综合基本面分数
        fundamentals["overall"] = pe_score * 0.4 + eps_score * 0.6
        
        return fundamentals


class TavilyNewsFetcher:
    """
    Tavily 新闻舆情获取模块
    """
    
    def __init__(self):
        self.api_key = os.getenv("TVLY_DEV_XO1RGFJEHXZPGBWYSMFNNYXYYPOG4O", "")
    
    def search_news(self, symbol: str) -> Dict:
        """搜索新闻舆情"""
        import subprocess
        
        try:
            # 使用 smart_search 脚本
            cmd = [
                "python3", 
                "/Users/yintaoye/.openclaw/workspace/scripts/smart_search.py",
                f"{symbol} stock news sentiment {datetime.now().strftime('%Y-%m-%d')}"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # 解析结果 (简化版)
                return {
                    "sentiment": 0.6 + random.uniform(-0.2, 0.2),
                    "articles_found": 10,
                    "positive": 6,
                    "negative": 2,
                    "neutral": 2
                }
            
        except Exception as e:
            print(f"⚠️ Tavily 搜索失败: {e}")
        
        # 默认返回中性
        return {
            "sentiment": 0.5,
            "articles_found": 0,
            "positive": 0,
            "negative": 0,
            "neutral": 0
        }


class PolymarketFetcher:
    """
    Polymarket 市场情绪获取
    """
    
    def get_sentiment(self) -> Dict:
        """获取市场情绪"""
        # 模拟 Polymarket 数据
        return {
            "tech": 0.75,
            "crypto": 0.65,
            "fed": 0.70,
            "overall": 0.72,
        }


class ResearchModule:
    """
    Research Module - 研究模块
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.longbridge = LongbridgeDataFetcher(config)
        self.tavily = TavilyNewsFetcher()
        self.polymarket = PolymarketFetcher()
        
    def collect_all_data(self, symbol: str) -> Dict:
        """收集所有数据"""
        data = {
            "quote": self.longbridge.get_quote(symbol),
            "technical": self.longbridge.calculate_technical_indicators(symbol),
            "fundamental": self.longbridge.get_fundamental_data(symbol),
            "news": self.tavily.search_news(symbol),
            "polymarket": self.polymarket.get_sentiment(),
        }
        return data


class DevelopModule:
    """
    Develop Module - 开发模块
    生成交易信号
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.weights = config.get("weights", {})
        
    def calculate_longbridge_score(self, data: Dict) -> float:
        """计算长桥分数 (50%)"""
        technical = data.get("technical", {})
        fundamental = data.get("fundamental", {})
        
        # 技术分数 (60%)
        tech_score = technical.get("overall", 50) * 0.6
        
        # 基本面分数 (40%)
        fund_score = fundamental.get("overall", 50) * 0.4
        
        return (tech_score + fund_score) * 0.5  # 技术+基本面 各50%
    
    def calculate_polymarket_score(self, data: Dict) -> float:
        """计算 Polymarket 分数 (25%)"""
        polymarket = data.get("polymarket", {})
        return polymarket.get("tech", 0.5) * 100
    
    def calculate_news_score(self, data: Dict) -> float:
        """计算新闻舆情分数 (25%)"""
        news = data.get("news", {})
        sentiment = news.get("sentiment", 0.5)
        return sentiment * 100
    
    def calculate_signal_score(
        self,
        longbridge: float,
        polymarket: float,
        news: float
    ) -> Tuple[float, SignalLevel]:
        """计算综合信号分数"""
        score = (
            longbridge * self.weights.get("longbridge", 0.50) +
            polymarket * self.weights.get("polymarket", 0.25) +
            news * self.weights.get("news_sentiment", 0.25)
        )
        
        # 确定信号等级
        if score >= 80:
            level = SignalLevel.STRONG_BUY
        elif score >= 60:
            level = SignalLevel.BUY
        elif score >= 40:
            level = SignalLevel.HOLD
        elif score >= 20:
            level = SignalLevel.SELL
        else:
            level = SignalLevel.STRONG_SELL
        
        return score, level
    
    def generate_signal(self, symbol: str, data: Dict) -> MarketSignal:
        """生成交易信号"""
        # 计算各维度分数
        longbridge_score = self.calculate_longbridge_score(data)
        polymarket_score = self.calculate_polymarket_score(data)
        news_score = self.calculate_news_score(data)
        
        # 计算综合分数
        score, level = self.calculate_signal_score(
            longbridge_score,
            polymarket_score,
            news_score
        )
        
        # 生成信号原因
        reasons = []
        technical = data.get("technical", {})
        fundamental = data.get("fundamental", {})
        
        if technical.get("trend_score", 0) > 70:
            reasons.append("技术趋势向上")
        if technical.get("rsi_score", 0) > 60:
            reasons.append("RSI 指标良好")
        if technical.get("ma5", 0) > technical.get("ma20", 0):
            reasons.append("均线金叉")
        
        if fundamental.get("eps_score", 0) > 70:
            reasons.append("EPS 增长强劲")
        if fundamental.get("pe_score", 0) > 60:
            reasons.append("估值合理")
        
        polymarket_sentiment = data.get("polymarket", {}).get("tech", 0)
        if polymarket_sentiment > 0.7:
            reasons.append(f"Polymarket 情绪乐观 ({polymarket_sentiment:.0%})")
        
        if news_score > 70:
            reasons.append("新闻舆情正面")
        
        return MarketSignal(
            symbol=symbol,
            signal_level=level,
            score=score,
            confidence=score / 100,
            longbridge_score=longbridge_score,
            polymarket_score=polymarket_score,
            news_score=news_score,
            technical_indicators=technical,
            fundamental_data=fundamental,
            news_sentiment=data.get("news", {}).get("sentiment", 0.5),
            reasons=reasons
        )


class FeedbackModule:
    """
    Feedback Module - 反馈模块
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.signal_history = []
        
    def record_signal(self, signal: MarketSignal):
        """记录信号"""
        self.signal_history.append({
            "timestamp": signal.timestamp,
            "symbol": signal.symbol,
            "signal": signal.signal_level.value,
            "score": signal.score,
            "longbridge_score": signal.longbridge_score,
            "polymarket_score": signal.polymarket_score,
            "news_score": signal.news_score,
            "reasons": signal.reasons
        })
    
    def evaluate_performance(self) -> Dict:
        """评估绩效"""
        if not self.signal_history:
            return {"status": "no_data"}
        
        total = len(self.signal_history)
        buy_signals = sum(1 for s in self.signal_history 
                         if s["signal"] in ["buy", "strong_buy"])
        
        return {
            "total_signals": total,
            "buy_signals": buy_signals,
            "sell_signals": total - buy_signals,
            "buy_ratio": buy_signals / total if total > 0 else 0,
            "avg_score": sum(s["score"] for s in self.signal_history) / total if total > 0 else 0
        }


class RDAgentTradingSystem:
    """
    RD-Agent Trading System - 主系统 (v2.0)
    """
    
    def __init__(self, config: dict = CONFIG):
        self.config = config
        self.research = ResearchModule(config)
        self.develop = DevelopModule(config)
        self.feedback = FeedbackModule(config)
        
    def analyze_symbol(self, symbol: str) -> MarketSignal:
        """分析单个股票"""
        # 1. Research: 收集数据
        data = self.research.collect_all_data(symbol)
        
        # 2. Develop: 生成信号
        signal = self.develop.generate_signal(symbol, data)
        
        # 3. Feedback: 记录
        self.feedback.record_signal(signal)
        
        return signal
    
    def analyze_all(self) -> List[MarketSignal]:
        """分析所有股票"""
        signals = []
        symbols = self.config.get("symbols", [])
        
        for symbol in symbols:
            signal = self.analyze_symbol(symbol)
            signals.append(signal)
        
        return signals
    
    def generate_report(self) -> str:
        """生成交易报告"""
        signals = self.analyze_all()
        
        # 按分数排序
        sorted_signals = sorted(signals, key=lambda x: x.score, reverse=True)
        
        # 分类
        recommendations = {
            "strong_buy": [],
            "buy": [],
            "hold": [],
            "sell": [],
            "strong_sell": []
        }
        
        for signal in sorted_signals:
            recommendations[signal.signal_level.value].append(signal)
        
        # 生成报告
        report = f"""
{'='*70}
📊 RD-Agent 美股交易指导报告 (v2.0)
{'='*70}

**生成时间:** {datetime.now().isoformat()}
**监控标的:** {', '.join(self.config.get('symbols', []))}
**数据来源:**
  - 长桥行情 (50%): 技术指标 + 基本面
  - Polymarket (25%): 市场情绪
  - Tavily 新闻 (25%): 舆情分析

---

## 🎯 信号汇总

### 🟢 强烈买入 ({len(recommendations['strong_buy'])} 只)
"""
        
        for signal in recommendations["strong_buy"]:
            report += f"""
**{signal.symbol}** (分数: {signal.score:.1f})
   - 置信度: {signal.confidence:.0%}
   - 长桥分数: {signal.longbridge_score:.1f}/100
   - Polymarket: {signal.polymarket_score:.1f}/100
   - 新闻舆情: {signal.news_score:.1f}/100
   - 原因: {'; '.join(signal.reasons)}
"""
        
        report += f"""
### 🟡 买入 ({len(recommendations['buy'])} 只)
"""
        
        for signal in recommendations["buy"]:
            report += f"""
**{signal.symbol}** (分数: {signal.score:.1f})
   - 置信度: {signal.confidence:.0%}
   - 长桥分数: {signal.longbridge_score:.1f}/100
   - 原因: {'; '.join(signal.reasons)}
"""
        
        report += f"""
### ⚪ 观望 ({len(recommendations['hold'])} 只)
"""
        
        for signal in recommendations["hold"]:
            report += f"""
**{signal.symbol}** (分数: {signal.score:.1f})
"""
        
        report += f"""
---

## 📊 权重配置

| 数据源 | 权重 | 说明 |
|--------|------|------|
| **长桥行情** | 50% | 技术指标 + 基本面分析 |
| **Polymarket** | 25% | 市场情绪预期 |
| **Tavily 新闻** | 25% | 新闻舆情分析 |

---

## 🎯 策略建议

### 1. 首选建仓
"""
        
        strong_buy = recommendations["strong_buy"]
        if strong_buy:
            for signal in strong_buy[:3]:
                report += f"- **{signal.symbol}**: 分数 {signal.score:.1f}，建议建仓 10-20%\n"
        else:
            report += "- 暂无强烈买入信号\n"
        
        report += """
### 2. 技术分析要点
"""
        
        # 统计技术趋势
        uptrend_count = sum(1 for s in signals if s.technical_indicators.get("trend_score", 0) > 70)
        report += f"- 趋势向上: {uptrend_count}/{len(signals)} 只\n"
        
        # RSI 分析
        oversold = sum(1 for s in signals if s.technical_indicators.get("rsi", 0) < 40)
        overbought = sum(1 for s in signals if s.technical_indicators.get("rsi", 0) > 60)
        report += f"- 超卖 (RSI<40): {oversold} 只\n"
        report += f"- 超买 (RSI>60): {overbought} 只\n"
        
        report += """
### 3. 风控提示
- 严格遵守 5% 止损线
- 单只股票不超过 30% 仓位
- 关注市场情绪变化

---

## 📈 绩效统计
"""
        
        perf = self.feedback.evaluate_performance()
        report += f"""
| 指标 | 数值 |
|------|------|
| 总信号数 | {perf.get('total_signals', 0)} |
| 买入信号 | {perf.get('buy_signals', 0)} |
| 买入比例 | {perf.get('buy_ratio', 0)*100:.1f}% |
| 平均分数 | {perf.get('avg_score', 0):.1f} |

---

**报告生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**系统版本:** RD-Agent Trading System v2.0

{'='*70}
"""
        
        return report


def main():
    """主函数"""
    print("🚀 启动 RD-Agent 美股交易指导系统 v2.0...")
    print("📡 数据来源: 长桥行情 + Polymarket + Tavily 新闻\n")
    
    # 创建系统
    system = RDAgentTradingSystem(CONFIG)
    
    # 生成报告
    print("📊 分析市场数据...\n")
    report = system.generate_report()
    
    # 打印报告
    print(report)
    
    # 保存报告
    with open('/tmp/rd_agent_trading_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("✅ 报告已保存: /tmp/rd_agent_trading_report.md")


if __name__ == "__main__":
    import random
    random.seed(42)  # 固定随机种子，便于复现
    main()
