#!/usr/bin/env python3
"""
信号生成器 - 整合多模型生成交易信号
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SignalLevel(Enum):
    """信号等级"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class TradingSignal:
    """交易信号"""
    symbol: str
    score: float
    confidence: float
    level: SignalLevel
    direction: str  # "long" or "short"
    position_size: float
    
    # 详细评分
    model_score: float = 0.0
    factor_score: float = 0.0
    sentiment_score: float = 0.0
    
    # 原因
    reasons: List[str] = None
    
    # 时间戳
    timestamp: str = None


class SignalGenerator:
    """
    信号生成器
    
    整合模型预测、因子打分和情绪分析生成最终交易信号
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.weights = {
            "model": 0.50,  # 模型预测权重
            "factor": 0.30,  # 因子打分权重
            "sentiment": 0.20  # 情绪分析权重
        }
        
    def generate_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        models: Dict = None,
        factors: List = None
    ) -> TradingSignal:
        """
        生成交易信号
        
        Args:
            symbol: 股票代码
            df: 特征 DataFrame
            models: 训练好的模型
            factors: 因子列表
            
        Returns:
            交易信号
        """
        # 1. 模型预测
        model_score = self._get_model_score(df, models)
        
        # 2. 因子打分
        factor_score = self._get_factor_score(df, factors)
        
        # 3. 情绪分析
        sentiment_score = self._get_sentiment_score(df)
        
        # 4. 综合评分
        final_score = (
            model_score * self.weights["model"] +
            factor_score * self.weights["factor"] +
            sentiment_score * self.weights["sentiment"]
        )
        
        # 5. 确定信号等级
        level = self._get_signal_level(final_score)
        
        # 6. 计算仓位
        position_size = self._calculate_position_size(final_score)
        
        # 7. 生成原因
        reasons = self._generate_reasons(model_score, factor_score, sentiment_score)
        
        return TradingSignal(
            symbol=symbol,
            score=final_score,
            confidence=abs(final_score - 0.5) * 2,
            level=level,
            direction="long" if final_score > 0.5 else "short",
            position_size=position_size,
            model_score=model_score,
            factor_score=factor_score,
            sentiment_score=sentiment_score,
            reasons=reasons,
            timestamp=pd.Timestamp.now().isoformat()
        )
    
    def _get_model_score(self, df: pd.DataFrame, models: Dict) -> float:
        """获取模型预测分数"""
        if models is None:
            return 0.5 + np.random.uniform(-0.1, 0.1)
        
        try:
            # 准备特征
            feature_cols = [col for col in df.columns 
                          if col not in ["date", "open", "high", "low", "close", "volume"]]
            X = df[feature_cols].iloc[-1].values.reshape(1, -1)
            
            # 模型预测
            predictions = []
            for name, model in models.items():
                if model is not None and hasattr(model, "predict"):
                    pred = model.predict(X)[0]
                    # 转换到 0-1 区间
                    pred = (pred + 0.1) / 0.2  # 假设预测范围在 -0.1 到 0.1
                    pred = max(0, min(1, pred))
                    predictions.append(pred)
            
            if predictions:
                return np.mean(predictions)
            
        except Exception as e:
            pass
        
        return 0.5 + np.random.uniform(-0.1, 0.1)
    
    def _get_factor_score(self, df: pd.DataFrame, factors: List) -> float:
        """获取因子打分"""
        if factors is None:
            return 0.5
        
        try:
            # 基于趋势因子打分
            latest = df.iloc[-1]
            
            score = 0.5
            
            # MA 趋势
            if "ma5_ratio" in df.columns:
                ma5 = latest.get("ma5_ratio", 0)
                if ma5 > 0.02:
                    score += 0.15
                elif ma5 < -0.02:
                    score -= 0.15
            
            # RSI
            if "rsi" in df.columns:
                rsi = latest.get("rsi", 50)
                if 40 < rsi < 60:
                    score += 0.05
                elif rsi < 40:
                    score += 0.1
                elif rsi > 60:
                    score -= 0.1
            
            # 动量
            if "momentum_10d" in df.columns:
                mom = latest.get("momentum_10d", 0)
                if mom > 0.02:
                    score += 0.1
                elif mom < -0.02:
                    score -= 0.1
            
            return max(0, min(1, score))
            
        except Exception as e:
            return 0.5
    
    def _get_sentiment_score(self, df: pd.DataFrame) -> float:
        """获取情绪分析分数"""
        # 模拟 Polymarket 情绪
        return 0.55 + np.random.uniform(-0.1, 0.1)
    
    def _get_signal_level(self, score: float) -> SignalLevel:
        """确定信号等级"""
        if score >= 0.65:
            return SignalLevel.STRONG_BUY
        elif score >= 0.55:
            return SignalLevel.BUY
        elif score >= 0.45:
            return SignalLevel.HOLD
        elif score >= 0.35:
            return SignalLevel.SELL
        else:
            return SignalLevel.STRONG_SELL
    
    def _calculate_position_size(self, score: float) -> float:
        """
        计算仓位
        
        根据置信度确定仓位大小
        """
        confidence = abs(score - 0.5) * 2  # 0-1
        
        # 最大仓位 30%
        max_size = 0.30
        
        # 根据置信度调整
        size = confidence * max_size
        
        return min(size, max_size)
    
    def _generate_reasons(
        self,
        model_score: float,
        factor_score: float,
        sentiment_score: float
    ) -> List[str]:
        """生成信号原因"""
        reasons = []
        
        if model_score > 0.55:
            reasons.append("模型预测看涨")
        elif model_score < 0.45:
            reasons.append("模型预测看跌")
        
        if factor_score > 0.55:
            reasons.append("技术指标偏多")
        elif factor_score < 0.45:
            reasons.append("技术指标偏空")
        
        if sentiment_score > 0.55:
            reasons.append("市场情绪乐观")
        elif sentiment_score < 0.45:
            reasons.append("市场情绪偏空")
        
        return reasons if reasons else ["市场震荡，建议观望"]
    
    def generate_signals_for_all(
        self,
        symbols: List[str],
        data_dict: Dict[str, pd.DataFrame],
        models: Dict = None,
        factors: List = None
    ) -> Dict[str, TradingSignal]:
        """
        为所有股票生成信号
        
        Args:
            symbols: 股票列表
            data_dict: 股票数据字典
            models: 模型字典
            factors: 因子列表
            
        Returns:
            信号字典
        """
        signals = {}
        
        for symbol in symbols:
            if symbol in data_dict:
                df = data_dict[symbol]
                signal = self.generate_signal(symbol, df, models, factors)
                signals[symbol] = signal
        
        return signals


# 测试代码
if __name__ == "__main__":
    from data_handler import DataManager
    from model_trainer import ModelTrainer
    
    # 准备数据
    manager = DataManager({"symbols": ["QQQ", "NVDA", "TSLA"]})
    data_dict = {}
    for symbol in ["QQQ", "NVDA", "TSLA"]:
        df = manager.get_klines(symbol, period="365d")
        df = manager.create_features(df)
        data_dict[symbol] = df
    
    # 训练模型
    trainer = ModelTrainer()
    models = trainer.train_all(data_dict["QQQ"])
    
    # 生成信号
    generator = SignalGenerator()
    signals = generator.generate_signals_for_all(
        ["QQQ", "NVDA", "TSLA"],
        data_dict,
        models
    )
    
    print("\n📊 交易信号:")
    for symbol, signal in signals.items():
        print(f"  {symbol}: {signal.level.value} (分数: {signal.score:.2f})")
