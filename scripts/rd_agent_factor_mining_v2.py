#!/usr/bin/env python3
"""
增强版 RD-Agent 因子挖掘系统
- 新增更多技术因子
- 新增市场情绪因子
- 新增波动率交易因子

运行: python3 scripts/rd_agent_factor_mining_v2.py
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from longbridge_data_fetcher import LongbridgeDataFetcher, Period

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class Factor:
    name: str
    ic: float
    rank_ic: float
    type: str
    description: str


class EnhancedFactorMiner:
    """增强版因子挖掘系统"""
    
    def __init__(self):
        self.factors: List[Factor] = []
        
    def calculate_all_factors(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算所有因子"""
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        open_price = df['open']
        
        factors = {}
        
        # ==================== 1. 移动平均因子 ====================
        for window in [5, 10, 20, 60, 120, 250]:
            if len(close) >= window:
                factors[f'ma{window}_ratio'] = close / close.rolling(window).mean() - 1
                factors[f'ma{window}_slope'] = close.rolling(window).mean().pct_change()
        
        # ==================== 2. 动量因子 ====================
        for window in [3, 5, 10, 20, 60, 120]:
            if len(close) >= window:
                factors[f'momentum_{window}'] = close / close.shift(window) - 1
        
        # ==================== 3. 相对强弱因子 ====================
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        factors['rsi_14'] = 100 - (100 / (1 + rs))
        factors['rsi_28'] = 100 - (100 / (1 + (gain.rolling(28).mean() / (loss.rolling(28).mean()).replace(0, np.nan))))
        
        # ==================== 4. 波动率因子 ====================
        returns = close.pct_change()
        for window in [5, 10, 20, 60]:
            factors[f'volatility_{window}'] = returns.rolling(window).std()
            factors[f'volatility_ratio_{window}'] = returns.rolling(window).std() / returns.rolling(window*2).mean()
        
        # ==================== 5. 成交量因子 ====================
        factors['volume_ma5'] = volume / volume.rolling(5).mean() - 1
        factors['volume_ma20'] = volume / volume.rolling(20).mean() - 1
        factors['volume_ma60'] = volume / volume.rolling(60).mean() - 1
        factors['volume_trend'] = volume.rolling(20).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0)
        
        # ==================== 6. OBV 能量潮 ====================
        obv = (np.sign(close.diff()) * volume).cumsum()
        factors['obv_ma5'] = obv / obv.rolling(5).mean() - 1
        factors['obv_ma20'] = obv / obv.rolling(20).mean() - 1
        factors['obv_momentum'] = obv / obv.shift(10) - 1
        
        # ==================== 7. 价格位置因子 ====================
        factors['high_low_ratio'] = (close - low) / (high - low + 1e-8)
        factors['close_position'] = (close - low) / (high - low + 1e-8)
        
        # ==================== 8. 布林带因子 ====================
        for window in [10, 20, 30]:
            ma = close.rolling(window).mean()
            std = close.rolling(window).std()
            factors[f'bb_upper_{window}'] = (high - ma) / (2 * std + 1e-8)
            factors[f'bb_lower_{window}'] = (low - ma) / (2 * std + 1e-8)
            factors[f'bb_width_{window}'] = (high - low) / (ma + 1e-8)
            factors[f'bb_position_{window}'] = (close - ma) / (2 * std + 1e-8)
        
        # ==================== 9. MACD 因子 ====================
        for fast, slow, signal in [(12, 26, 9), (8, 17, 9), (5, 35, 5)]:
            ema_fast = close.ewm(span=fast, adjust=False).mean()
            ema_slow = close.ewm(span=slow, adjust=False).mean()
            macd = ema_fast - ema_slow
            macd_signal = macd.ewm(span=signal, adjust=False).mean()
            factors[f'macd_{fast}_{slow}'] = macd - macd_signal
            factors[f'macd_hist_{fast}_{slow}'] = (macd - macd_signal) / close
            factors[f'macd_signal_{fast}_{slow}'] = macd_signal
        
        # ==================== 10. ATR 真实波幅因子 ====================
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        factors['atr_14'] = tr.rolling(14).mean()
        factors['atr_28'] = tr.rolling(28).mean()
        factors['atr_ratio'] = factors['atr_14'] / close
        factors['atr_trend'] = factors['atr_14'] / factors['atr_28'] - 1
        
        # ==================== 11. KDJ 随机指标 ====================
        for window in [9, 14]:
            lowest = low.rolling(window).min()
            highest = high.rolling(window).max()
            k = 100 * (close - lowest) / (highest - lowest + 1e-8)
            d = k.rolling(3).mean()
            j = 3 * k - 2 * d
            factors[f'k_{window}'] = k
            factors[f'd_{window}'] = d
            factors[f'j_{window}'] = j
            factors[f'k_d_cross_{window}'] = k - d
        
        # ==================== 12. Williams %R 威廉指标 ====================
        for window in [14, 28]:
            highest = high.rolling(window).max()
            lowest = low.rolling(window).min()
            factors[f'williams_r_{window}'] = -100 * (highest - close) / (highest - lowest + 1e-8)
        
        # ==================== 13. CCI 商品通道指数 ====================
        for window in [14, 20]:
            tp = (high + low + close) / 3
            sma = tp.rolling(window).mean()
            mad = tp.rolling(window).apply(lambda x: np.abs(x - x.mean()).mean())
            factors[f'cci_{window}'] = (tp - sma) / (0.015 * mad + 1e-8)
        
        # ==================== 14. ROC 价格变化率 ====================
        for window in [5, 10, 20]:
            factors[f'roc_{window}'] = (close - close.shift(window)) / (close.shift(window) + 1e-8) * 100
        
        # ==================== 15. 均线交叉因子 ====================
        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        
        factors['ma5_ma10_cross'] = ma5 / ma10 - 1
        factors['ma5_ma20_cross'] = ma5 / ma20 - 1
        factors['ma10_ma20_cross'] = ma10 / ma20 - 1
        factors['ma20_ma60_cross'] = ma20 / ma60 - 1
        
        # ==================== 16. 乖离率因子 ====================
        for window in [5, 10, 20]:
            ma = close.rolling(window).mean()
            factors[f'bias_{window}'] = (close - ma) / (ma + 1e-8) * 100
        
        # ==================== 17. 成交量持仓量因子 ====================
        factors['volume_price_trend'] = (close - close.shift(1)) * volume
        factors['volume_price_trend_ma5'] = factors['volume_price_trend'].rolling(5).mean()
        factors['volume_price_trend_ma20'] = factors['volume_price_trend'].rolling(20).mean()
        
        # ==================== 18. 突破因子 ====================
        factors['high_20'] = close / high.rolling(20).max() - 1
        factors['low_20'] = close / low.rolling(20).min() - 1
        factors['breakout_20'] = (close > close.rolling(20).max().shift(1)).astype(int)
        
        # ==================== 19. 趋势强度因子 ====================
        def trend_strength(series, window=20):
            x = np.arange(window)
            return series.rolling(window).apply(lambda y: np.polyfit(x, y, 1)[0] if len(y) == window and not np.isnan(y).any() else 0)
        
        factors['trend_strength_20'] = trend_strength(close, 20)
        factors['trend_strength_60'] = trend_strength(close, 60)
        
        # ==================== 20. 盘口因子 (如果有数据) ====================
        if 'ask_volume' in df.columns and 'bid_volume' in df.columns:
            factors['order_imbalance'] = (df['ask_volume'] - df['bid_volume']) / (df['ask_volume'] + df['bid_volume'] + 1e-8)
            factors['spread'] = (df['ask_price'] - df['bid_price']) / close
        
        # 清理 NaN
        factors = {k: v.replace([np.inf, -np.inf], np.nan) for k, v in factors.items()}
        
        return factors
    
    def evaluate_factors(self, df: pd.DataFrame, factors: Dict[str, pd.Series]) -> List[Factor]:
        """评估因子 IC"""
        returns = df['close'].pct_change().shift(-1)
        results = []
        
        for name, values in factors.items():
            if len(values) < 60:
                continue
            
            # 去除 NaN
            valid_idx = ~(values.isna() | returns.isna())
            if valid_idx.sum() < 60:
                continue
            
            ic = values[valid_idx].corr(returns[valid_idx])
            rank_ic = values[valid_idx].corr(returns[valid_idx], method='spearman')
            
            if not np.isnan(ic) and abs(ic) > 0.01:
                results.append(Factor(
                    name=name,
                    ic=ic,
                    rank_ic=rank_ic,
                    type='technical',
                    description=f'{name} IC={ic:.3f}'
                ))
        
        return sorted(results, key=lambda x: abs(x.ic), reverse=True)
    
    def run(self, symbol: str = "NVDA.US", lookback: int = 500):
        """运行因子挖掘"""
        logger.info(f"🔬 开始增强因子挖掘: {symbol}")
        
        # 获取数据
        fetcher = LongbridgeDataFetcher()
        df = fetcher.get_candlesticks(symbol, "day", count=lookback)
        
        if df is None or len(df) < 100:
            print(f"❌ 数据获取失败")
            return
        
        logger.info(f"✅ 获取 {len(df)} 条K线")
        
        # 计算因子
        factors = self.calculate_all_factors(df)
        logger.info(f"✅ 计算 {len(factors)} 个因子")
        
        # 评估因子
        valid_factors = self.evaluate_factors(df, factors)
        logger.info(f"✅ 有效因子 {len(valid_factors)} 个")
        
        # 输出 top 20
        print("\n" + "=" * 70)
        print("🎯 Top 20 有效因子")
        print("=" * 70)
        
        for i, f in enumerate(valid_factors[:20], 1):
            print(f"{i:2}. {f.name:<25} IC: {f.ic:+.4f}  RankIC: {f.rank_ic:+.4f}")
        
        # 保存结果
        result = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "total_factors": len(factors),
            "valid_factors": len(valid_factors),
            "top_factors": [
                {"name": f.name, "ic": f.ic, "rank_ic": f.rank_ic}
                for f in valid_factors[:50]
            ]
        }
        
        os.makedirs("/tmp", exist_ok=True)
        with open("/tmp/enhanced_factors.json", "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"\n💾 结果已保存: /tmp/enhanced_factors.json")
        
        return valid_factors


if __name__ == "__main__":
    miner = EnhancedFactorMiner()
    miner.run("NVDA.US", 500)
