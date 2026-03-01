#!/usr/bin/env python3
"""
RD-Agent 定时回测系统
- 每日自动回测
- 多标的比较
- 定期生成报告

运行: python3 scripts/rd_agent_backtest_scheduler.py
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from longbridge_data_fetcher import LongbridgeDataFetcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """回测配置"""
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float = 100000
    commission: float = 0.001  # 0.1%
    slippage: float = 0.001   # 0.1%


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


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.fetcher = LongbridgeDataFetcher()
        
    def load_data(self) -> pd.DataFrame:
        """加载历史数据"""
        days = (datetime.now() - datetime.strptime(self.config.start_date, "%Y-%m-%d")).days + 30
        df = self.fetcher.get_candlesticks(self.config.symbol, "day", count=days)
        
        if df is None or len(df) < 60:
            raise ValueError(f"数据不足: {len(df) if df is not None else 0} 条")
        
        # 过滤日期 (使用 datetime 索引)
        start_dt = pd.to_datetime(self.config.start_date)
        end_dt = pd.to_datetime(self.config.end_date)
        df = df[df.index >= start_dt]
        df = df[df.index <= end_dt]
        
        # 确保有必要的列
        if 'close' not in df.columns:
            raise ValueError("数据缺少 close 列")
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """生成交易信号"""
        close = df['close']
        
        # 简单的双均线策略
        ma5 = close.rolling(5).mean()
        ma20 = close.rolling(20).mean()
        
        # 信号: 1=多头, -1=空头, 0=观望
        signals = pd.Series(0, index=df.index)
        signals[ma5 > ma20] = 1   # 金叉做多
        signals[ma5 < ma20] = -1  # 死叉做空
        
        # RSI 过滤
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        # RSI > 70 过滤多头, RSI < 30 过滤空头
        signals[(rsi > 70) & (signals == 1)] = 0
        signals[(rsi < 30) & (signals == -1)] = 0
        
        return signals
    
    def run(self) -> BacktestResult:
        """运行回测"""
        logger.info(f"🔄 回测 {self.config.symbol}...")
        
        df = self.load_data()
        signals = self.generate_signals(df)
        
        # 计算收益
        returns = df['close'].pct_change()
        
        # 策略收益 (考虑手续费滑点)
        strategy_returns = signals.shift(1) * returns
        strategy_returns = strategy_returns - self.config.commission - self.config.slippage
        
        # 累计收益
        cumulative = (1 + strategy_returns).cumprod()
        
        # 计算指标
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
        num_trades = (trades != 0).sum()
        
        # 胜率
        trade_returns = []
        in_position = False
        entry_price = 0
        
        for i, (signal, ret) in enumerate(zip(signals, returns)):
            if signal != 0 and not in_position:
                in_position = True
                entry_price = df.iloc[i]['close']
            elif signal == 0 and in_position:
                exit_price = df.iloc[i]['close']
                trade_returns.append((exit_price - entry_price) / entry_price)
                in_position = False
        
        if trade_returns:
            win_rate = sum(1 for r in trade_returns if r > 0) / len(trade_returns)
            avg_profit = np.mean([r for r in trade_returns if r > 0]) if any(r > 0 for r in trade_returns) else 0
            avg_loss = np.mean([r for r in trade_returns if r < 0]) if any(r < 0 for r in trade_returns) else 0
        else:
            win_rate = 0
            avg_profit = 0
            avg_loss = 0
        
        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            num_trades=num_trades,
            avg_profit=avg_profit,
            avg_loss=avg_loss
        )


class ScheduledBacktest:
    """定时回测"""
    
    def __init__(self):
        self.symbols = ["QQQ", "NVDA", "TSLA", "GOOGL", "MSFT"]
        self.strategies = ["ma_cross", "rsi", "momentum"]
        
    def run_daily(self):
        """每日回测"""
        logger.info("🎯 开始每日回测...")
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        
        results = []
        
        for symbol in self.symbols:
            try:
                config = BacktestConfig(
                    symbol=f"{symbol}.US",
                    start_date=start_date,
                    end_date=end_date
                )
                engine = BacktestEngine(config)
                result = engine.run()
                
                results.append({
                    "symbol": symbol,
                    "total_return": float(result.total_return),
                    "annual_return": float(result.annual_return),
                    "max_drawdown": float(result.max_drawdown),
                    "sharpe_ratio": float(result.sharpe_ratio),
                    "win_rate": float(result.win_rate),
                    "num_trades": int(result.num_trades),
                    "avg_profit": float(result.avg_profit),
                    "avg_loss": float(result.avg_loss)
                })
                
                logger.info(f"  {symbol}: 收益 {result.total_return*100:+.1f}%, 夏普 {result.sharpe_ratio:.2f}")
                
            except Exception as e:
                logger.error(f"  {symbol}: 回测失败 - {e}")
        
        # 保存结果
        output = {
            "timestamp": datetime.now().isoformat(),
            "period": f"{start_date} ~ {end_date}",
            "results": results
        }
        
        os.makedirs("/tmp", exist_ok=True)
        with open("/tmp/daily_backtest.json", "w") as f:
            json.dump(output, f, indent=2)
        
        # 生成报告
        self.generate_report(results)
        
        return output
    
    def generate_report(self, results: List[Dict]):
        """生成回测报告"""
        print("\n" + "=" * 80)
        print("📊 每日回测报告")
        print("=" * 80)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("-" * 80)
        
        # 排序
        results_sorted = sorted(results, key=lambda x: x['total_return'], reverse=True)
        
        print(f"{'代码':<8} {'总收益':>10} {'年化收益':>10} {'最大回撤':>10} {'夏普':>8} {'胜率':>8}")
        print("-" * 80)
        
        for r in results_sorted:
            print(f"{r['symbol']:<8} {r['total_return']*100:+9.1f}% {r['annual_return']*100:+9.1f}% {r['max_drawdown']*100:9.1f}% {r['sharpe_ratio']:8.2f} {r['win_rate']*100:7.1f}%")
        
        # 最佳标的
        best = results_sorted[0]
        print("-" * 80)
        print(f"🏆 最佳: {best['symbol']} (收益 {best['total_return']*100:+.1f}%)")
        
        # 生成策略建议
        profitable = [r for r in results if r['total_return'] > 0]
        if profitable:
            avg_return = np.mean([r['total_return'] for r in profitable])
            print(f"📈 可做多: {', '.join([r['symbol'] for r in profitable])} (平均 +{avg_return*100:.1f}%)")
        
        losing = [r for r in results if r['total_return'] < 0]
        if losing:
            avg_loss = np.mean([r['total_return'] for r in losing])
            print(f"📉 避免: {', '.join([r['symbol'] for r in losing])} (平均 {avg_loss*100:.1f}%)")
        
        print("=" * 80)
        
        # 保存详细报告
        report = f"# 📊 回测报告 - {datetime.now().strftime('%Y-%m-%d')}\n\n"
        report += f"## 标的排名\n\n"
        report += f"| 代码 | 总收益 | 年化收益 | 最大回撤 | 夏普 | 胜率 |\n"
        report += f"|------|--------|----------|----------|------|------|\n"
        for r in results_sorted:
            report += f"| {r['symbol']} | {r['total_return']*100:+.1f}% | {r['annual_return']*100:+.1f}% | {r['max_drawdown']*100:.1f}% | {r['sharpe_ratio']:.2f} | {r['win_rate']*100:.1f}% |\n"
        
        with open("/tmp/backtest_report.md", "w") as f:
            f.write(report)
        
        print(f"\n💾 报告已保存: /tmp/backtest_report.md")


if __name__ == "__main__":
    backtest = ScheduledBacktest()
    backtest.run_daily()
