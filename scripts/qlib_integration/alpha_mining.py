#!/usr/bin/env python3
"""
因子挖掘器 - 基于 RD-Agent 理念自动发现有效因子
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Factor:
    """因子"""
    name: str
    category: str  # technical, fundamental, sentiment
    ic: float = 0.0  # 信息系数
    ir: float = 0.0  # 信息比率
    turnover: float = 0.0  # 换手率
    score: float = 0.0  # 综合评分
    enabled: bool = True


class FactorMiner:
    """
    因子挖掘器
    
    基于 RD-Agent 理念，自动从数据中发现有效因子
    """
    
    def __init__(self):
        self.factor_library: List[Factor] = []
        self.categories = ["technical", "fundamental", "sentiment"]
        
    def mine_factors(self, df: pd.DataFrame) -> List[Factor]:
        """
        自动挖掘因子
        
        Args:
            df: 带有价格数据的 DataFrame
            
        Returns:
            发现的有效因子列表
        """
        factors = []
        
        # 1. 技术因子挖掘
        tech_factors = self._mine_technical_factors(df)
        factors.extend(tech_factors)
        
        # 2. 基本面因子挖掘
        fund_factors = self._mine_fundamental_factors(df)
        factors.extend(fund_factors)
        
        # 3. 组合因子
        combo_factors = self._mine_combo_factors(df)
        factors.extend(combo_factors)
        
        # 4. 评估所有因子
        for factor in factors:
            self._evaluate_factor(factor, df)
        
        # 5. 选择有效因子
        valid_factors = [f for f in factors if f.score > 0.5]
        
        self.factor_library = valid_factors
        
        return valid_factors
    
    def _mine_technical_factors(self, df: pd.DataFrame) -> List[Factor]:
        """挖掘技术因子"""
        factors = []
        
        # 趋势因子
        for window in [5, 10, 20, 60]:
            factors.append(Factor(
                name=f"ma{window}_ratio",
                category="technical",
                description=f"{window}日均线偏离率"
            ))
        
        # RSI 因子
        factors.append(Factor(name="rsi_14", category="technical"))
        
        # MACD 因子
        factors.append(Factor(name="macd_hist", category="technical"))
        
        # 布林带因子
        for col in ["bb_width", "bb_position"]:
            factors.append(Factor(name=col, category="technical"))
        
        # 动量因子
        for window in [10, 20, 60]:
            factors.append(Factor(
                name=f"momentum_{window}d",
                category="technical"
            ))
        
        # 波动率因子
        factors.append(Factor(name="volatility_20d", category="technical"))
        
        # 成交量因子
        factors.append(Factor(name="volume_ratio", category="technical"))
        
        # 价格位置
        factors.append(Factor(name="price_position", category="technical"))
        
        return factors
    
    def _mine_fundamental_factors(self, df: pd.DataFrame) -> List[Factor]:
        """挖掘基本面因子"""
        factors = []
        
        # 如果有基本面数据
        if "pe" in df.columns:
            factors.append(Factor(name="pe", category="fundamental"))
            factors.append(Factor(name="pb", category="fundamental"))
        
        if "eps" in df.columns:
            factors.append(Factor(name="eps", category="fundamental"))
        
        if "roe" in df.columns:
            factors.append(Factor(name="roe", category="fundamental"))
        
        # 财务比率因子
        factors.append(Factor(name="dividend_yield", category="fundamental"))
        factors.append(Factor(name="payout_ratio", category="fundamental"))
        
        return factors
    
    def _mine_sentiment_factors(self) -> List[Factor]:
        """挖掘情绪因子"""
        factors = []
        
        # Polymarket 情绪因子
        factors.append(Factor(name="polymarket_sentiment", category="sentiment"))
        
        # 新闻情绪因子
        factors.append(Factor(name="news_sentiment", category="sentiment"))
        
        # 社交媒体因子
        factors.append(Factor(name="social_sentiment", category="sentiment"))
        
        return factors
    
    def _mine_combo_factors(self, df: pd.DataFrame) -> List[Factor]:
        """挖掘组合因子"""
        factors = []
        
        # 价格 + 成交量组合
        factors.append(Factor(
            name="price_volume_trend",
            category="combo",
            description="价格与成交量趋势组合"
        ))
        
        # 动量 + 波动率组合
        factors.append(Factor(
            name="momentum_volatility",
            category="combo",
            description="动量与波动率组合"
        ))
        
        # 多时间框架组合
        factors.append(Factor(
            name="multi_timeframe_trend",
            category="combo",
            description="多时间框架趋势组合"
        ))
        
        return factors
    
    def _evaluate_factor(self, factor: Factor, df: pd.DataFrame):
        """
        评估因子有效性
        
        使用 IC (信息系数) 和 IR (信息比率) 评估
        """
        if factor.name not in df.columns:
            factor.score = 0.0
            return
        
        # 计算 IC
        if "return_5d" in df.columns:
            ic = df[factor.name].corr(df["return_5d"])
        else:
            ic = 0.0
        
        factor.ic = abs(ic) if not pd.isna(ic) else 0.0
        
        # 计算 IR (简化版)
        factor.ir = factor.ic * 10  # 简化计算
        
        # 计算换手率相关性 (如果有)
        if "volume_ratio" in df.columns:
            turnover_corr = df[factor.name].corr(df["volume_ratio"])
            factor.turnover = abs(turnover_corr) if not pd.isna(turnover_corr) else 0.1
        
        # 计算综合评分
        factor.score = (
            factor.ic * 0.5 +  # IC 权重 50%
            factor.ir * 0.3 +  # IR 权重 30%
            (1 - factor.turnover) * 0.2  # 换手率权重 20%
        )
    
    def get_top_factors(self, n: int = 20) -> List[Factor]:
        """获取评分最高的 N 个因子"""
        sorted_factors = sorted(
            self.factor_library,
            key=lambda x: x.score,
            reverse=True
        )
        return sorted_factors[:n]
    
    def generate_alpha(self, factors: List[Factor]) -> str:
        """
        生成 alpha 表达式
        
        用于 QLib 的因子表达式
        """
        if not factors:
            return "(close / close - 1)"
        
        # 选择最佳因子
        top_factors = self.get_top_factors(5)
        
        # 生成加权表达式
        alpha_expr = "("
        weights = []
        for i, factor in enumerate(top_factors):
            if factor.category == "technical":
                expr = f"(close / ta.SMA(close, {factor.name.replace('ma', '')}) - 1)"
            else:
                expr = f"(-{factor.name})"
            weights.append(expr)
        
        alpha_expr += " + ".join(weights) + ") / " + str(len(weights))
        
        return alpha_expr
    
    def backtest_factor(self, factor: Factor, df: pd.DataFrame) -> Dict:
        """
        回测单个因子
        
        Returns:
            回测结果
        """
        if factor.name not in df.columns:
            return {"return": 0, "win_rate": 0}
        
        # 分组回测
        df = df.copy()
        df["group"] = pd.qcut(df[factor.name], q=5, labels=False, duplicates="drop")
        
        # 计算各组收益
        if "return_5d" in df.columns:
            group_returns = df.groupby("group")["return_5d"].mean()
            
            # 多空组合收益
            long_short = group_returns.iloc[-1] - group_returns.iloc[0]
            
            return {
                "long_return": group_returns.iloc[-1],
                "short_return": group_returns.iloc[0],
                "long_short": long_short,
                "win_rate": (group_returns > 0).mean()
            }
        
        return {"return": 0, "win_rate": 0}


# 测试代码
if __name__ == "__main__":
    from data_handler import DataManager
    
    # 准备数据
    manager = DataManager({"symbols": ["QQQ"]})
    df = manager.get_klines("QQQ", period="365d")
    df = manager.create_features(df)
    
    # 挖掘因子
    miner = FactorMiner()
    factors = miner.mine_factors(df)
    
    print(f"发现 {len(factors)} 个因子")
    
    # 显示评分最高的因子
    top_factors = miner.get_top_factors(10)
    for factor in top_factors:
        print(f"  {factor.name}: IC={factor.ic:.3f}, IR={factor.ir:.3f}, Score={factor.score:.3f}")
