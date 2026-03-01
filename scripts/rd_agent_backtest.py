#!/usr/bin/env python3
"""
RD-Agent 交易建议自动回测系统
"""

import os, sys, json, numpy as np, pandas as pd
from datetime import datetime
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scripts.longbridge_data_fetcher import LongbridgeDataFetcher

@dataclass
class BacktestResult:
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe: float
    win_rate: float
    num_trades: int


class RDAgentBacktester:
    def __init__(self, capital=100000):
        self.fetcher = LongbridgeDataFetcher()
        self.capital = capital
        
    def get_signal(self, df, factor, direction):
        close = df['close'].astype(float)
        
        if factor == 'ma120':
            fv = close / close.rolling(120).mean() - 1
        elif factor == 'ma60':
            fv = close / close.rolling(60).mean() - 1
        elif factor == 'ma5':
            fv = close / close.rolling(5).mean() - 1
        elif factor == 'momentum_5':
            fv = close / close.shift(5) - 1
        elif factor == 'momentum_10':
            fv = close / close.shift(10) - 1
        elif factor == 'volatility_20':
            fv = close.pct_change().rolling(20).std()
        elif factor == 'volatility_10':
            fv = close.pct_change().rolling(10).std()
        else:
            fv = pd.Series([0] * len(close))
        
        # 交易信号
        if direction == 'long':
            return (fv > 0).astype(int)
        else:
            return (fv < 0).astype(int)
    
    def backtest(self, symbol, factor, direction, stop_loss=0.05, take_profit=0.10):
        print(f"🔄 回测: {symbol} {factor} ({direction})")
        
        df = self.fetcher.get_candlesticks(symbol, 'day', 300)
        if len(df) < 150:
            return None
        
        close = df['close'].astype(float)
        signal = self.get_signal(df, factor, direction)
        returns = close.pct_change()
        
        # 模拟交易
        position = 0
        entry_price = 0
        trades = []
        values = [self.capital]
        
        for i in range(50, len(df) - 1):
            if position == 0 and signal.iloc[i] == 1:
                position = 1
                entry_price = close.iloc[i]
            elif position == 1 and signal.iloc[i] == 0:
                ret = close.iloc[i] / entry_price - 1
                ret = max(-stop_loss, min(take_profit, ret))
                trades.append(ret)
                position = 0
            
            if position == 1:
                values.append(values[-1] * (1 + returns.iloc[i]))
            else:
                values.append(values[-1])
        
        if not trades:
            return BacktestResult(0, 0, 0, 0, 0, 0)
        
        # 指标计算
        final = values[-1]
        total_ret = (final / self.capital - 1) * 100
        
        # 最大回撤
        peak = np.maximum.accumulate(values)
        dd = (np.array(values) - peak) / peak
        max_dd = abs(np.min(dd)) * 100
        
        # 夏普
        std = np.std(trades)
        sharpe = (np.mean(trades) - 0.03) / std if std > 0 else 0
        
        # 胜率
        win = sum(1 for t in trades if t > 0) / len(trades)
        
        return BacktestResult(
            total_return=total_ret,
            annual_return=total_ret * (252 / len(df)),
            max_drawdown=max_dd,
            sharpe=sharpe,
            win_rate=win,
            num_trades=len(trades)
        )


def main():
    print("="*60)
    print("🎯 RD-Agent 交易建议自动回测")
    print("="*60)
    
    signals = [
        ('GOOGL', 'ma120', 'short'),
        ('TSLA', 'ma60', 'short'),
        ('QQQ', 'volatility_20', 'long'),
        ('NVDA', 'momentum_5', 'short'),
        ('MSFT', 'ma60', 'long'),
    ]
    
    tester = RDAgentBacktester(100000)
    results = {}
    
    print("\n📊 回测结果:")
    print("-"*60)
    
    for symbol, factor, direction in signals:
        r = tester.backtest(symbol, factor, direction)
        if r:
            results[f"{symbol}_{factor}"] = r
            emoji = "🟢" if r.total_return > 0 else "🔴"
            print(f"{emoji} {symbol:6} {factor:15} {direction:5} | 收益:{r.total_return:+6.1f}% | 回撤:{r.max_drawdown:5.1f}% | 胜率:{r.win_rate:4.0%} | 交易:{r.num_trades}")
    
    # 汇总
    if results:
        avg_ret = np.mean([r.total_return for r in results.values()])
        avg_dd = np.mean([r.max_drawdown for r in results.values()])
        avg_win = np.mean([r.win_rate for r in results.values()])
        
        print("-"*60)
        print(f"📈 平均收益: {avg_ret:+.1f}%")
        print(f"📉 平均回撤: {avg_dd:.1f}%")
        print(f"🎯 平均胜率: {avg_win:.0%}")
    
    # 保存
    with open('/tmp/backtest_results.json', 'w') as f:
        json.dump({k: {
            'total_return': v.total_return,
            'max_drawdown': v.max_drawdown,
            'sharpe': v.sharpe,
            'win_rate': v.win_rate,
            'num_trades': v.num_trades
        } for k, v in results.items()}, f, indent=2)
    
    print("\n💾 已保存: /tmp/backtest_results.json")


if __name__ == '__main__':
    main()
