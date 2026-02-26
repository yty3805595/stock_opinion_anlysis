#!/usr/bin/env python3
"""
RD-Agent 实盘交易系统
- 因子挖掘 → 信号生成 → 期权分析 → 实盘执行

运行: python3 scripts/rd_agent_trading_v2.py
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Longbridge
from longbridge.openapi import Config, TradeContext, QuoteContext

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ==================== 配置 ====================
CONFIG = {
    "symbols": ["QQQ", "NVDA", "TSLA", "GOOGL", "MSFT", "AAPL", "META", "SPY"],
    "max_position_pct": 0.20,  # 单只最大仓位 20%
    "max_loss_per_day": 0.03,   # 日最大亏损 3%
    "min_signal_confidence": 0.6,  # 最小信号置信度
    "initial_capital": 100000,
}

CREDENTIALS_PATH = "/Users/yintaoye/.openclaw/workspace/skills/longbridge-trading/config/credentials.json"


# ==================== 数据获取 ====================
class DataFetcher:
    """数据获取"""
    
    @staticmethod
    def get_stock_data(symbol: str, days: int = 250) -> pd.DataFrame:
        """获取股票数据"""
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=(datetime.now() - timedelta(days=days+30)).strftime("%Y-%m-%d"))
        df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
        return df
    
    @staticmethod
    def get_realtime_quote(symbols: List[str]) -> Dict[str, float]:
        """获取实时行情"""
        creds = json.load(open(CREDENTIALS_PATH))["credentials"]
        config = Config(app_key=creds["app_key"], app_secret=creds["app_secret"], access_token=creds["access_token"])
        ctx = QuoteContext(config)
        
        quotes = ctx.quote([f"{s}.US" for s in symbols])
        return {q.symbol.replace(".US", ""): q.last_done for q in quotes}


# ==================== 因子计算 ====================
class FactorEngine:
    """因子引擎"""
    
    @staticmethod
    def calculate_factors(df: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算技术因子"""
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        factors = {}
        
        # 均线
        for w in [5, 10, 20, 60]:
            factors[f'ma{w}_ratio'] = close / close.rolling(w).mean() - 1
            
        # 动量
        for w in [5, 10, 20]:
            factors[f'momentum_{w}'] = close / close.shift(w) - 1
            
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        factors['rsi'] = 100 - (100 / (1 + rs))
        
        # 成交量
        factors['volume_ma5'] = volume / volume.rolling(5).mean() - 1
        factors['volume_ma20'] = volume / volume.rolling(20).mean() - 1
        
        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        factors['macd'] = macd - signal
        
        # 布林带
        ma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        factors['bb_position'] = (close - ma20) / (2 * std20 + 1e-8)
        
        # KDJ
        lowest = low.rolling(9).min()
        highest = high.rolling(9).max()
        k = 100 * (close - lowest) / (highest - lowest + 1e-8)
        d = k.rolling(3).mean()
        factors['k_d_cross'] = k - d
        
        return {k: v for k, v in factors.items() if len(v.dropna()) > 60}


# ==================== 信号生成 ====================
class SignalGenerator:
    """信号生成器"""
    
    def __init__(self, factors: Dict[str, pd.Series], df: pd.DataFrame):
        self.factors = factors
        self.df = df
        self.close = df['close']
        
    def generate(self) -> Dict[str, Dict]:
        """生成交易信号"""
        signals = {}
        
        # 多因子组合信号
        score = 0
        count = 0
        
        # 均线多头
        ma5 = self.close.rolling(5).mean()
        ma20 = self.close.rolling(20).mean()
        if ma5.iloc[-1] > ma20.iloc[-1]:
            score += 1
        count += 1
        
        # RSI 不极端
        rsi = self.factors.get('rsi')
        if rsi is not None:
            if 30 < rsi.iloc[-1] < 70:
                score += 1
            elif rsi.iloc[-1] < 30:
                score += 0.5  # 超卖
            elif rsi.iloc[-1] > 70:
                score -= 0.5  # 超买
        count += 1
        
        # MACD 金叉
        macd = self.factors.get('macd')
        if macd is not None:
            if macd.iloc[-1] > 0 and macd.iloc[-2] < 0:
                score += 1
            elif macd.iloc[-1] < 0 and macd.iloc[-2] > 0:
                score -= 1
        count += 1
        
        # 成交量放大
        vol = self.factors.get('volume_ma5')
        if vol is not None:
            if vol.iloc[-1] > 0.3:
                score += 0.5
        count += 1
        
        # 布林带
        bb = self.factors.get('bb_position')
        if bb is not None:
            if bb.iloc[-1] < -1:  # 超卖
                score += 0.5
            elif bb.iloc[-1] > 1:  # 超买
                score -= 0.5
        count += 1
        
        # 计算置信度
        confidence = score / count
        normalized = (confidence + 1) / 2  # 转换到 0-1
        
        # 信号等级
        if normalized > 0.7:
            signal = "BUY"
        elif normalized > 0.55:
            signal = "HOLD"
        elif normalized < 0.3:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        return {
            "signal": signal,
            "confidence": normalized,
            "score": score,
            "price": self.close.iloc[-1],
            "rsi": rsi.iloc[-1] if rsi is not None else None,
            "ma5": ma5.iloc[-1],
            "ma20": ma20.iloc[-1]
        }


# ==================== 期权分析 ====================
class OptionsAnalyzer:
    """期权分析"""
    
    @staticmethod
    def analyze(symbol: str, current_price: float, position_qty: int = 0) -> Dict:
        """分析期权"""
        # 确保 current_price 是 float
        current_price = float(current_price)
        
        # 获取期权链
        creds = json.load(open(CREDENTIALS_PATH))["credentials"]
        config = Config(app_key=creds["app_key"], app_secret=creds["app_secret"], access_token=creds["access_token"])
        ctx = QuoteContext(config)
        
        result = {
            "symbol": symbol,
            "current_price": current_price,
            "has_position": position_qty != 0,
            "position_qty": position_qty,
            "recommendation": "HOLD"
        }
        
        # 简单分析
        if position_qty > 0:
            # 持有股票，看是否需要卖出看涨期权
            if current_price > 190:  # 假设是NVDA
                result["recommendation"] = "SELL_CALL"
                result["strike_price"] = int(current_price * 1.05)
                result["expiry_days"] = 30
                
        return result


# ==================== 持仓管理 ====================
class PositionManager:
    """持仓管理"""
    
    def __init__(self):
        creds = json.load(open(CREDENTIALS_PATH))["credentials"]
        config = Config(app_key=creds["app_key"], app_secret=creds["app_secret"], access_token=creds["access_token"])
        self.trade_ctx = TradeContext(config)
        self.quote_ctx = QuoteContext(config)
        
    def get_positions(self) -> List[Dict]:
        """获取持仓"""
        positions_resp = self.trade_ctx.stock_positions()
        
        positions = []
        for channel in positions_resp.channels:
            if 'lb_papertrading' in channel.account_channel:
                for p in channel.positions:
                    positions.append({
                        "symbol": p.symbol.replace(".US", ""),
                        "name": p.symbol_name,
                        "quantity": p.quantity,
                        "cost_price": p.cost_price,
                        "type": "option" if "NVDA260" in p.symbol else "stock"
                    })
        return positions
    
    def get_account(self) -> Dict:
        """获取账户信息"""
        balance = self.trade_ctx.account_balance()[0]
        return {
            "total_assets": float(balance.net_assets),
            "cash_usd": float([c for c in balance.cash_infos if c.currency == "USD"][0].available_cash)
        }


# ==================== 主系统 ====================
class RDAgentTradingSystem:
    """RD-Agent 实盘交易系统"""
    
    def __init__(self):
        self.data_fetcher = DataFetcher()
        self.position_manager = PositionManager()
        
    def run(self):
        """运行系统"""
        print("\n" + "=" * 80)
        print("🤖 RD-Agent 实盘交易系统")
        print("=" * 80)
        
        # 1. 获取持仓
        print("\n📊 获取持仓...")
        positions = self.position_manager.get_positions()
        account = self.position_manager.get_account()
        
        print(f"   现金 (USD): ${account['cash_usd']:,.2f}")
        print(f"   总资产: ${account['total_assets']:,.2f}")
        
        stock_positions = {p['symbol']: p for p in positions if p['type'] == 'stock'}
        option_positions = {p['symbol']: p for p in positions if p['type'] == 'option'}
        
        print(f"   股票持仓: {list(stock_positions.keys())}")
        print(f"   期权持仓: {list(option_positions.keys())}")
        
        # 2. 获取实时行情
        print("\n📈 获取实时行情...")
        symbols = CONFIG["symbols"]
        quotes = self.data_fetcher.get_realtime_quote(symbols)
        print(f"   已获取 {len(quotes)} 个行情")
        
        # 3. 因子分析 & 信号生成
        print("\n🔬 因子分析 & 信号生成...")
        signals = {}
        
        for symbol in symbols:
            try:
                df = self.data_fetcher.get_stock_data(symbol)
                if df is None or len(df) < 60:
                    continue
                    
                factors = FactorEngine.calculate_factors(df)
                generator = SignalGenerator(factors, df)
                signal = generator.generate()
                signals[symbol] = signal
                
            except Exception as e:
                logger.error(f"   {symbol} 分析失败: {e}")
        
        # 4. 生成报告
        print("\n" + "=" * 80)
        print("📋 交易信号报告")
        print("=" * 80)
        print("\n📝 策略说明:")
        print("  - 买入条件: 均线多头 + RSI不极端 + MACD金叉 + 成交量放大 + 布林不超买")
        print("  - 卖出条件: 均线死叉 + RSI超买 + MACD死叉 + 布林超买")
        print("  - 置信度 = (得分 + 1) / 2")
        
        # 按置信度排序
        sorted_signals = sorted(signals.items(), key=lambda x: x[1]['confidence'], reverse=True)
        
        print(f"\n{'代码':<8} {'信号':<8} {'置信度':>10} {'价格':>10} {'RSI':>8} {'建议'}")
        print("-" * 70)
        
        for symbol, sig in sorted_signals:
            rsi = f"{sig['rsi']:.1f}" if sig['rsi'] else "N/A"
            emoji = "🟢" if sig['signal'] == "BUY" else "🔴" if sig['signal'] == "SELL" else "⚪"
            
            # 检查是否已有持仓
            action = "持有" if symbol in stock_positions else "建仓"
            if sig['signal'] == "SELL" and symbol in stock_positions:
                action = "卖出"
            elif sig['signal'] == "BUY" and symbol not in stock_positions:
                action = "买入"
                
            print(f"{symbol:<8} {emoji} {sig['signal']:<5} {sig['confidence']:>9.0%} ${sig['price']:>8.2f} {rsi:>8} {action}")
        
        # 5. 期权分析
        print("\n" + "=" * 80)
        print("📊 期权分析")
        print("=" * 80)
        
        for symbol, pos in stock_positions.items():
            if symbol in quotes:
                opt = OptionsAnalyzer.analyze(symbol, quotes[symbol], pos['quantity'])
                print(f"\n{symbol}:")
                print(f"   当前价: ${opt['current_price']:.2f}")
                print(f"   持仓: {opt['position_qty']} 股")
                print(f"   建议: {opt['recommendation']}")
        
        # 6. 执行建议
        print("\n" + "=" * 80)
        print("🎯 执行建议")
        print("=" * 80)
        
        # 买入信号
        buy_signals = [(s, sig) for s, sig in sorted_signals if sig['signal'] == "BUY" and sig['confidence'] > 0.6]
        if buy_signals:
            print("\n🟢 买入建议:")
            for symbol, sig in buy_signals:
                if symbol not in stock_positions:
                    # 计算买入数量
                    max_qty = int(account['cash_usd'] * CONFIG['max_position_pct'] / sig['price'])
                    print(f"   {symbol}: 买入 {max_qty} 股 @ ${sig['price']:.2f}")
        
        # 卖出信号
        sell_signals = [(s, sig) for s, sig in sorted_signals if sig['signal'] == "SELL"]
        if sell_signals:
            print("\n🔴 卖出建议:")
            for symbol, sig in sell_signals:
                if symbol in stock_positions:
                    pos = stock_positions[symbol]
                    print(f"   {symbol}: 卖出 {pos['quantity']} 股 @ ${sig['price']:.2f}")
        
        print("\n" + "=" * 80)
        
        # 保存报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "account": account,
            "positions": positions,
            "signals": {s: {k: float(v) if isinstance(v, (np.floating, np.integer)) else v for k, v in sig.items()} for s, sig in signals.items()}
        }
        
        os.makedirs("/tmp", exist_ok=True)
        with open("/tmp/trading_signal.json", "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n💾 报告已保存: /tmp/trading_signal.json")
        
        return signals


if __name__ == "__main__":
    system = RDAgentTradingSystem()
    system.run()
