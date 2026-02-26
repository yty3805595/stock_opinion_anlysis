#!/usr/bin/env python3
"""
RD-Agent 全自动化因子挖掘与回测系统
- 自动挖掘有效因子
- 自动回测验证
- 自动生成复盘报告

运行: python3 scripts/rd_agent_auto_mining.py
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FactorMiner:
    """自动因子挖掘"""
    
    def __init__(self):
        self.all_factors = {}
        
    def calculate_factors(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算所有因子"""
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        open_price = df['open']
        
        factors = {}
        
        # 1. 均线因子
        for w in [5, 10, 20, 60, 120]:
            factors[f'ma{w}_ratio'] = close / close.rolling(w).mean() - 1
            factors[f'ma{w}_slope'] = close.rolling(w).mean().pct_change()
            
        # 2. 动量因子
        for w in [3, 5, 10, 20, 60]:
            factors[f'momentum_{w}'] = close / close.shift(w) - 1
            
        # 3. RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        factors['rsi_14'] = 100 - (100 / (1 + rs))
        
        # 4. 波动率
        ret = close.pct_change()
        for w in [5, 10, 20, 60]:
            factors[f'volatility_{w}'] = ret.rolling(w).std()
            
        # 5. 成交量
        factors['volume_ma5'] = volume / volume.rolling(5).mean() - 1
        factors['volume_ma20'] = volume / volume.rolling(20).mean() - 1
        
        # 6. 布林带
        ma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        factors['bb_position'] = (close - ma20) / (2 * std20 + 1e-8)
        
        # 7. MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        factors['macd'] = macd - signal
        factors['macd_hist'] = (macd - signal) / close
        
        # 8. KDJ
        lowest = low.rolling(9).min()
        highest = high.rolling(9).max()
        k = 100 * (close - lowest) / (highest - lowest + 1e-8)
        d = k.rolling(3).mean()
        j = 3 * k - 2 * d
        factors['k'] = k
        factors['d'] = d
        factors['j'] = j
        factors['k_d_cross'] = k - d
        
        # 9. ATR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        factors['atr_14'] = tr.rolling(14).mean()
        
        # 10. 威廉指标
        highest_r = high.rolling(14).max()
        lowest_r = low.rolling(14).min()
        factors['williams_r'] = -100 * (highest_r - close) / (highest_r - lowest_r + 1e-8)
        
        # 11. CCI
        tp = (high + low + close) / 3
        sma = tp.rolling(14).mean()
        mad = tp.rolling(14).apply(lambda x: np.abs(x - x.mean()).mean())
        factors['cci'] = (tp - sma) / (0.015 * mad + 1e-8)
        
        # 12. ROC
        for w in [5, 10, 20]:
            factors[f'roc_{w}'] = (close - close.shift(w)) / (close.shift(w) + 1e-8) * 100
            
        # 13. 乖离率
        for w in [5, 10, 20]:
            ma = close.rolling(w).mean()
            factors[f'bias_{w}'] = (close - ma) / (ma + 1e-8) * 100
            
        # 14. 均线交叉
        ma5, ma10, ma20, ma60 = close.rolling(5).mean(), close.rolling(10).mean(), close.rolling(20).mean(), close.rolling(60).mean()
        factors['ma5_ma10_cross'] = ma5 / ma10 - 1
        factors['ma5_ma20_cross'] = ma5 / ma20 - 1
        factors['ma10_ma20_cross'] = ma10 / ma20 - 1
        factors['ma20_ma60_cross'] = ma20 / ma60 - 1
        
        # 15. 突破
        factors['breakout_20'] = (close > close.rolling(20).max().shift(1)).astype(int)
        factors['close_to_high'] = close / high.rolling(20).max() - 1
        
        # 16. OBV
        obv = (np.sign(close.diff()) * volume).cumsum()
        factors['obv'] = obv / obv.rolling(10).mean() - 1
        
        # 清理
        factors = {k: v.replace([np.inf, -np.inf], np.nan) for k, v in factors.items()}
        return factors
    
    def evaluate_factors(self, df: pd.DataFrame, factors: Dict[str, pd.Series]) -> List[Tuple[str, float, float]]:
        """评估因子 IC"""
        returns = df['close'].pct_change().shift(-1)
        results = []
        
        for name, values in factors.items():
            if len(values.dropna()) < 60:
                continue
            
            valid = ~(values.isna() | returns.isna())
            if valid.sum() < 60:
                continue
            
            ic = values[valid].corr(returns[valid])
            rank_ic = values[valid].corr(returns[valid], method='spearman')
            
            if not np.isnan(ic) and abs(ic) > 0.01:
                results.append((name, ic, rank_ic))
        
        return sorted(results, key=lambda x: abs(x[1]), reverse=True)


class FactorBacktester:
    """因子回测"""
    
    def __init__(self, initial_capital=100000, commission=0.001):
        self.initial_capital = initial_capital
        self.commission = commission
        
    def backtest_factor(self, df: pd.DataFrame, factor_name: str, factor_values: pd.Series) -> Dict:
        """单因子回测"""
        signals = pd.Series(0, index=df.index)
        
        # 因子值 > 0 买入, < 0 卖出
        signals[factor_values > factor_values.quantile(0.7)] = 1
        signals[factor_values < factor_values.quantile(0.3)] = -1
        
        # 计算收益
        returns = df['close'].pct_change()
        strategy_returns = signals.shift(1) * returns
        strategy_returns = strategy_returns - self.commission
        
        cumulative = (1 + strategy_returns.fillna(0)).cumprod()
        
        # 指标
        total_return = cumulative.iloc[-1] - 1
        annual_return = (1 + total_return) ** (252 / len(df)) - 1
        peak = cumulative.cummax()
        max_drawdown = ((cumulative - peak) / peak).min()
        
        sharpe = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252) if strategy_returns.std() > 0 else 0
        
        # 交易次数
        trades = signals.diff().fillna(0)
        num_trades = ((trades == 1) | (trades == -1)).sum()
        
        return {
            'factor': factor_name,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe,
            'num_trades': num_trades
        }


class AutoMiningSystem:
    """全自动化挖掘回测系统"""
    
    def __init__(self):
        self.symbols = ["QQQ", "SPY", "NVDA", "GOOGL", "MSFT", "TSLA", "AAPL", "META"]
        self.miner = FactorMiner()
        
    def run(self):
        """运行自动化挖掘回测"""
        logger.info("🚀 开始自动因子挖掘与回测...")
        
        all_results = []
        
        for symbol in self.symbols:
            try:
                logger.info(f"\n📊 处理 {symbol}...")
                
                # 1. 获取数据
                ticker = yf.Ticker(symbol)
                df = ticker.history(start="2024-01-01", end=datetime.now().strftime("%Y-%m-%d"))
                
                if df is None or len(df) < 100:
                    continue
                
                df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
                
                # 2. 计算因子
                factors = self.miner.calculate_factors(df)
                logger.info(f"   计算了 {len(factors)} 个因子")
                
                # 3. 评估因子
                valid_factors = self.miner.evaluate_factors(df, factors)
                logger.info(f"   有效因子: {len(valid_factors)} 个")
                
                # 4. 回测 Top 因子
                backtester = FactorBacktester()
                top_results = []
                
                for name, ic, rank_ic in valid_factors[:10]:  # 回测前10
                    result = backtester.backtest_factor(df, name, factors[name])
                    result['ic'] = ic
                    result['rank_ic'] = rank_ic
                    top_results.append(result)
                    all_results.append({
                        'symbol': symbol,
                        **result
                    })
                
                # 输出 Top 3
                top3 = sorted(top_results, key=lambda x: x['total_return'], reverse=True)[:3]
                for i, r in enumerate(top3, 1):
                    logger.info(f"   #{i} {r['factor']}: IC={r['ic']:.3f}, 收益={r['total_return']*100:+.1f}%, 夏普={r['sharpe_ratio']:.2f}")
                    
            except Exception as e:
                logger.error(f"   {symbol} 失败: {e}")
        
        # 5. 生成汇总报告
        self.generate_report(all_results)
        
        return all_results
    
    def generate_report(self, results: List[Dict]):
        """生成复盘报告"""
        if not results:
            logger.warning("无结果")
            return
            
        # 按收益排序
        results_sorted = sorted(results, key=lambda x: x['total_return'], reverse=True)
        
        print("\n" + "=" * 80)
        print("📊 RD-Agent 自动因子挖掘与回测报告")
        print("=" * 80)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("-" * 80)
        
        # 全局 Top 10
        print("\n🏆 全局 Top 10 因子:")
        print(f"{'排名':<4} {'标的':<8} {'因子':<20} {'IC':>8} {'收益':>10} {'夏普':>8}")
        print("-" * 80)
        
        for i, r in enumerate(results_sorted[:10], 1):
            print(f"{i:<4} {r['symbol']:<8} {r['factor']:<20} {r.get('ic', 0):>8.3f} {r['total_return']*100:>+9.1f}% {r['sharpe_ratio']:>7.2f}")
        
        # 按标的汇总
        print("\n\n📈 各标的最佳因子:")
        by_symbol = {}
        for r in results:
            if r['symbol'] not in by_symbol:
                by_symbol[r['symbol']] = []
            by_symbol[r['symbol']].append(r)
        
        for symbol, sym_results in sorted(by_symbol.items()):
            best = max(sym_results, key=lambda x: x['total_return'])
            print(f"  {symbol}: {best['factor']} (收益 {best['total_return']*100:+.1f}%)")
        
        # 保存报告
        def convert(obj):
            if isinstance(obj, np.integer): return int(obj)
            if isinstance(obj, np.floating): return float(obj)
            if isinstance(obj, np.ndarray): return obj.tolist()
            return obj
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(results),
            "top_factors": [{k: convert(v) for k, v in r.items()} for r in results_sorted[:20]],
            "summary": {
                symbol: max(by_symbol[symbol], key=lambda x: x['total_return'])['factor']
                for symbol in by_symbol
            }
        }
        
        os.makedirs("/tmp", exist_ok=True)
        with open("/tmp/auto_mining_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Markdown 报告
        md = f"# 📊 自动因子挖掘与回测报告\n\n"
        md += f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        md += f"## 全局 Top 10 因子\n\n"
        md += f"| 排名 | 标的 | 因子 | IC | 收益 | 夏普 |\n"
        md += f"|------|------|------|-----|------|------|\n"
        for i, r in enumerate(results_sorted[:10], 1):
            md += f"| {i} | {r['symbol']} | {r['factor']} | {r.get('ic', 0):.3f} | {r['total_return']*100:+.1f}% | {r['sharpe_ratio']:.2f} |\n"
        
        with open("/tmp/auto_mining_report.md", "w") as f:
            f.write(md)
        
        print(f"\n💾 报告已保存: /tmp/auto_mining_report.md")
        print("=" * 80)


if __name__ == "__main__":
    system = AutoMiningSystem()
    system.run()
