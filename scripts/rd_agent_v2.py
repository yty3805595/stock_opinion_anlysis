#!/usr/bin/env python3
"""
RD-Agent 增强因子挖掘系统 v2
"""

import os, sys, json, logging
import numpy as np
import pandas as pd
from datetime import datetime
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from longbridge_data_fetcher import LongbridgeDataFetcher

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

@dataclass
class FactorResult:
    name: str
    ic: float
    sharpe: float
    robustness: float
    return_pct: float
    
    def score(self) -> float:
        return (
            min(abs(self.ic) / 0.1, 1) * 0.3 +
            min(self.sharpe / 2, 1) * 0.3 +
            self.robustness * 0.4
        )

class RDAgentV2:
    def __init__(self):
        self.fetcher = LongbridgeDataFetcher()
        
    def get_factor_value(self, df: pd.DataFrame, name: str) -> pd.Series:
        """计算因子值"""
        close = df['close'].astype(float)
        o, h, l = df['open'].astype(float), df['high'].astype(float), df['low'].astype(float)
        v = df['volume'].astype(float) if 'volume' in df.columns else pd.Series([1]*len(close))
        
        if name == 'momentum_5': return close / close.shift(5) - 1
        if name == 'momentum_10': return close / close.shift(10) - 1
        if name == 'momentum_20': return close / close.shift(20) - 1
        if name == 'ma5': return close / close.rolling(5).mean() - 1
        if name == 'ma10': return close / close.rolling(10).mean() - 1
        if name == 'ma20': return close / close.rolling(20).mean() - 1
        if name == 'ma60': return close / close.rolling(60).mean() - 1
        if name == 'ma120': return close / close.rolling(120).mean() - 1
        if name == 'rsi_14':
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            return 100 - (100 / (1 + gain / loss))
        if name == 'volatility_10': return close.pct_change().rolling(10).std()
        if name == 'volatility_20': return close.pct_change().rolling(20).std()
        if name == 'volume_ma5': return v / v.rolling(5).mean() - 1
        if name == 'volume_ma20': return v / v.rolling(20).mean() - 1
        if name == 'bollinger':
            bb = close.rolling(20)
            return (close - bb.mean()) / (2 * bb.std())
        if name == 'macd_hist':
            ema12, ema26 = close.ewm(span=12).mean(), close.ewm(span=26).mean()
            signal = (ema12 - ema26).ewm(span=9).mean()
            return (ema12 - ema26) - signal
        return pd.Series([0] * len(close))
    
    def evaluate(self, symbol: str) -> list:
        """评估因子"""
        df = self.fetcher.get_candlesticks(symbol, 'day', 300)
        if len(df) < 100:
            return []
        
        close = df['close'].astype(float)
        future_ret = close.pct_change(10).shift(-10)
        
        results = []
        factor_names = ['momentum_5', 'momentum_10', 'momentum_20', 
                       'ma5', 'ma10', 'ma20', 'ma60', 'ma120',
                       'rsi_14', 'volatility_10', 'volatility_20',
                       'volume_ma5', 'volume_ma20', 'bollinger', 'macd_hist']
        
        for fname in factor_names:
            fv = self.get_factor_value(df, fname)
            valid = fv.notna() & future_ret.notna()
            if valid.sum() < 50:
                continue
            
            ic = fv[valid].corr(future_ret[valid])
            if abs(ic) < 0.02:
                continue
            
            # 计算收益序列
            returns = []
            for i in range(50, len(fv)-10, 15):
                fv_w = fv.iloc[i-30:i]
                fr_w = future_ret.iloc[i-30:i]
                v = fv_w.notna() & fr_w.notna()
                if v.sum() > 15:
                    returns.append(fr_w[v].mean())
            
            if not returns:
                continue
            
            ret_pct = np.mean(returns) * 100
            sharpe = ret_pct / (np.std(returns) * 100) if np.std(returns) > 0 else 0
            win_rate = sum(1 for r in returns if r > 0) / len(returns)
            robustness = win_rate * 0.5 + min(abs(sharpe)/2, 1) * 0.5
            
            results.append(FactorResult(
                name=fname,
                ic=ic,
                sharpe=sharpe,
                robustness=robustness,
                return_pct=ret_pct
            ))
        
        results.sort(key=lambda x: x.score(), reverse=True)
        return results[:5]  # Top 5

def main():
    print("="*60)
    print("🎯 RD-Agent 增强因子挖掘 v2")
    print("="*60)
    
    system = RDAgentV2()
    
    all_results = {}
    for symbol in ['NVDA.US', 'QQQ.US', 'TSLA.US', 'GOOGL.US', 'MSFT.US']:
        try:
            results = system.evaluate(symbol)
            all_results[symbol] = [asdict(r) for r in results]
            print(f"\n✅ {symbol}: {len(results)} 个有效因子")
            for r in results[:3]:
                print(f"   {r.name}: IC={r.ic:.3f}, Sharpe={r.sharpe:.2f}, Rob={r.robustness:.2f}")
        except Exception as e:
            print(f"\n❌ {symbol}: {e}")
    
    # 保存
    with open('/tmp/rdagent_v2_results.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n💾 已保存: /tmp/rdagent_v2_results.json")

if __name__ == '__main__':
    main()
