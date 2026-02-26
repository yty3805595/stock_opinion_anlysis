#!/usr/bin/env python3
"""
RD-Agent 增强回测系统 v2
- 使用 yfinance 真实数据
- 多策略组合
- 改进的风控

运行: python3 scripts/rd_agent_backtest_v2.py
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
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """回测配置"""
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float = 100000
    commission: float = 0.001
    slippage: float = 0.001


@dataclass
class BacktestResult:
    """回测结果"""
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    num_trades: int
    avg_profit: float
    avg_loss: float
    profit_factor: float


class EnhancedBacktestEngine:
    """增强版回测引擎"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        
    def load_data(self) -> pd.DataFrame:
        """使用 yfinance 加载真实数据"""
        logger.info(f"📥 获取 {self.config.symbol} 数据...")
        
        ticker = yf.Ticker(self.config.symbol)
        df = ticker.history(start=self.config.start_date, end=self.config.end_date)
        
        if df is None or len(df) < 60:
            raise ValueError(f"数据不足: {len(df) if df is not None else 0} 条")
        
        df = df.rename(columns={
            'Open': 'open',
            'High': 'high', 
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        logger.info(f"✅ 获取 {len(df)} 条K线")
        
        return df
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        close = df['close']
        
        # 均线
        df['ma5'] = close.rolling(5).mean()
        df['ma10'] = close.rolling(10).mean()
        df['ma20'] = close.rolling(20).mean()
        df['ma60'] = close.rolling(60).mean()
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 布林带
        ma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        df['bb_upper'] = ma20 + 2 * std20
        df['bb_lower'] = ma20 - 2 * std20
        df['bb_position'] = (close - ma20) / (2 * std20 + 1e-8)
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - close.shift())
        low_close = abs(df['low'] - close.shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        
        # 波动率
        df['volatility'] = close.pct_change().rolling(20).std()
        
        # 成交量均线
        df['volume_ma20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma20']
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """生成交易信号 - 多策略组合"""
        signals = pd.Series(0, index=df.index)
        
        # 策略1: 均线多头排列
        ma_bullish = (df['ma5'] > df['ma10']) & (df['ma10'] > df['ma20']) & (df['ma20'] > df['ma60'])
        
        # 策略2: RSI 超卖反弹
        rsi_oversold = df['rsi'] < 35
        rsi_recovery = (df['rsi'] > df['rsi'].shift(1)) & (df['rsi'].shift(1) <= df['rsi'].shift(2))
        
        # 策略3: MACD 金叉
        macd_cross = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
        
        # 策略4: 布林带超卖
        bb_oversold = df['close'] < df['bb_lower']
        
        # 策略5: 成交量放大
        volume_surge = df['volume_ratio'] > 1.5
        
        # 买入信号: 满足多个条件
        buy_conditions = 0
        buy_conditions += ma_bullish.astype(int)
        buy_conditions += (rsi_oversold & rsi_recovery).astype(int)
        buy_conditions += macd_cross.astype(int)
        buy_conditions += bb_oversold.astype(int)
        buy_conditions += volume_surge.astype(int)
        
        signals[buy_conditions >= 2] = 1  # 满足2个及以上条件买入
        
        # 卖出信号
        # 策略1: 均线死叉
        ma_bearish = (df['ma5'] < df['ma10']) & (df['ma10'] < df['ma20'])
        
        # 策略2: RSI 超买
        rsi_overbought = df['rsi'] > 70
        
        # 策略3: MACD 死叉
        macd_death = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))
        
        # 策略4: 布林带上轨
        bb_overbought = df['close'] > df['bb_upper']
        
        # 策略5: 止盈/止损
        # (由风控模块处理)
        
        sell_conditions = 0
        sell_conditions += ma_bearish.astype(int)
        sell_conditions += rsi_overbought.astype(int)
        sell_conditions += macd_death.astype(int)
        sell_conditions += bb_overbought.astype(int)
        
        signals[sell_conditions >= 2] = -1  # 满足2个及以上条件卖出
        
        # 过滤: RSI 极端值
        signals[(df['rsi'] > 80) & (signals == 1)] = 0
        signals[(df['rsi'] < 20) & (signals == -1)] = 0
        
        return signals
    
    def run(self) -> BacktestResult:
        """运行回测"""
        logger.info(f"🔄 回测 {self.config.symbol}...")
        
        df = self.load_data()
        df = self.calculate_indicators(df)
        signals = self.generate_signals(df)
        
        # 计算收益
        returns = df['close'].pct_change()
        
        # 策略收益
        strategy_returns = signals.shift(1) * returns
        strategy_returns = strategy_returns - self.config.commission
        
        # 累计收益
        cumulative = (1 + strategy_returns.fillna(0)).cumprod()
        
        # 指标计算
        total_return = cumulative.iloc[-1] - 1
        annual_return = (1 + total_return) ** (252 / len(df)) - 1
        
        # 最大回撤
        peak = cumulative.cummax()
        drawdown = (cumulative - peak) / peak
        max_drawdown = drawdown.min()
        
        # 夏普比率
        if strategy_returns.std() > 0:
            sharpe = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252)
        else:
            sharpe = 0
        
        # 交易统计
        trades = signals.diff().fillna(0)
        num_trades = ((trades == 1) | (trades == -1)).sum()
        
        # 胜率计算
        position_returns = []
        in_position = False
        entry_idx = 0
        
        for i in range(len(signals)):
            if signals.iloc[i] == 1 and not in_position:
                in_position = True
                entry_idx = i
            elif signals.iloc[i] == -1 and in_position:
                in_position = False
                trade_ret = (df['close'].iloc[i] - df['close'].iloc[entry_idx]) / df['close'].iloc[entry_idx]
                position_returns.append(trade_ret)
        
        if position_returns:
            wins = [r for r in position_returns if r > 0]
            losses = [r for r in position_returns if r < 0]
            win_rate = len(wins) / len(position_returns) if position_returns else 0
            avg_profit = np.mean(wins) if wins else 0
            avg_loss = np.mean(losses) if losses else 0
            profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0
        else:
            win_rate = 0
            avg_profit = 0
            avg_loss = 0
            profit_factor = 0
        
        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            num_trades=num_trades,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_factor=profit_factor
        )


class ScheduledBacktestV2:
    """增强版定时回测"""
    
    def __init__(self):
        self.symbols = [
            "QQQ",    # 纳指100
            "NVDA",   # 英伟达
            "TSLA",   # 特斯拉
            "GOOGL",  # 谷歌
            "MSFT",   # 微软
            "SPY",    # 标普500
            "AAPL",   # 苹果
            "META",   # Meta
        ]
        
    def run_daily(self):
        """每日回测"""
        logger.info("🎯 开始增强版每日回测...")
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        
        results = []
        
        for symbol in self.symbols:
            try:
                full_symbol = f"{symbol}"
                config = BacktestConfig(
                    symbol=full_symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                engine = EnhancedBacktestEngine(config)
                result = engine.run()
                
                results.append({
                    "symbol": symbol,
                    "total_return": float(result.total_return),
                    "annual_return": float(result.annual_return),
                    "max_drawdown": float(result.max_drawdown),
                    "sharpe_ratio": float(result.sharpe_ratio),
                    "win_rate": float(result.win_rate),
                    "num_trades": int(result.num_trades),
                    "profit_factor": float(result.profit_factor)
                })
                
                logger.info(f"  {symbol}: 收益 {result.total_return*100:+.1f}%, 夏普 {result.sharpe_ratio:.2f}")
                
            except Exception as e:
                logger.error(f"  {symbol}: 回测失败 - {e}")
        
        # 保存结果
        output = {
            "timestamp": datetime.now().isoformat(),
            "period": f"{start_date} ~ {end_date}",
            "data_source": "yfinance (real data)",
            "results": results
        }
        
        os.makedirs("/tmp", exist_ok=True)
        with open("/tmp/backtest_v2.json", "w") as f:
            json.dump(output, f, indent=2)
        
        # 生成报告
        self.generate_report(results)
        
        return output
    
    def generate_report(self, results: List[Dict]):
        """生成回测报告"""
        print("\n" + "=" * 80)
        print("📊 增强版每日回测报告 (真实数据)")
        print("=" * 80)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"数据源: Yahoo Finance (真实数据)")
        print("-" * 80)
        
        # 排序
        results_sorted = sorted(results, key=lambda x: x['total_return'], reverse=True)
        
        print(f"{'代码':<8} {'总收益':>10} {'年化收益':>10} {'最大回撤':>10} {'夏普':>8} {'胜率':>8} {'盈亏比':>8}")
        print("-" * 80)
        
        for r in results_sorted:
            print(f"{r['symbol']:<8} {r['total_return']*100:+9.1f}% {r['annual_return']*100:+9.1f}% {r['max_drawdown']*100:9.1f}% {r['sharpe_ratio']:8.2f} {r['win_rate']*100:7.1f}% {r['profit_factor']:7.2f}")
        
        # 最佳标的
        best = results_sorted[0]
        worst = results_sorted[-1]
        
        print("-" * 80)
        print(f"🏆 最佳: {best['symbol']} (收益 {best['total_return']*100:+.1f}%)")
        print(f"⚠️ 最差: {worst['symbol']} (收益 {worst['total_return']*100:+.1f}%)")
        
        # 策略建议
        profitable = [r for r in results if r['total_return'] > 0 and r['sharpe_ratio'] > 0.5]
        if profitable:
            print(f"📈 推荐做多: {', '.join([r['symbol'] for r in profitable])}")
        
        # 保存报告
        report = f"# 📊 回测报告 - {datetime.now().strftime('%Y-%m-%d')}\n\n"
        report += f"**数据源**: Yahoo Finance (真实数据)\n\n"
        report += f"## 标的排名\n\n"
        report += f"| 代码 | 总收益 | 年化收益 | 最大回撤 | 夏普 | 胜率 | 盈亏比 |\n"
        report += f"|------|--------|----------|----------|------|------|--------|\n"
        for r in results_sorted:
            report += f"| {r['symbol']} | {r['total_return']*100:+.1f}% | {r['annual_return']*100:+.1f}% | {r['max_drawdown']*100:.1f}% | {r['sharpe_ratio']:.2f} | {r['win_rate']*100:.1f}% | {r['profit_factor']:.2f} |\n"
        
        with open("/tmp/backtest_v2_report.md", "w") as f:
            f.write(report)
        
        print(f"\n💾 报告已保存: /tmp/backtest_v2_report.md")
        print("=" * 80)


if __name__ == "__main__":
    backtest = ScheduledBacktestV2()
    backtest.run_daily()
