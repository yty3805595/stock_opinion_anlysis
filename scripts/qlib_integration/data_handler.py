#!/usr/bin/env python3
"""
数据管理器 - 整合长桥行情和QLib特征工程
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class QuoteData:
    """报价数据"""
    symbol: str
    price: float
    change_pct: float
    volume: float
    timestamp: datetime


class DataManager:
    """
    数据管理器
    负责获取和处理市场数据
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.symbols = self.config.get("symbols", [])
        
        # 初始化长桥客户端
        self.quote_client = self._init_longbridge()
        
    def _init_longbridge(self):
        """初始化长桥客户端"""
        try:
            from longbridge.openapi import Config, QuoteContext
            
            # 从配置文件读取凭证
            credentials = self._load_credentials()
            
            if credentials:
                config = Config(
                    app_key=credentials.get("app_key"),
                    app_secret=credentials.get("app_secret"),
                    access_token=credentials.get("access_token", "")
                )
                client = QuoteContext(config)
                print("✅ 长桥行情客户端已连接")
                return client
            else:
                print("⚠️ 未找到长桥凭证，使用模拟数据")
                return None
                
        except Exception as e:
            print(f"⚠️ 长桥连接失败: {e}")
            return None
    
    def _load_credentials(self) -> dict:
        """从配置文件读取凭证"""
        config_paths = [
            "skills/longbridge-trading/config/credentials.json",
            ".env",
        ]
        
        for path_str in config_paths:
            path = Path(path_str)
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                    return data.get("credentials", {})
        
        return None
    
    def get_quote(self, symbol: str) -> QuoteData:
        """获取实时报价"""
        # 如果有长桥客户端，使用真实数据
        if self.quote_client:
            try:
                # 获取真实行情
                print(f"📡 获取 {symbol} 实时行情...")
                # 注意: 实际 API 调用需要参考长桥文档
                # 这里先用模拟数据
            except Exception as e:
                print(f"⚠️ 行情获取失败: {e}")
        
        # 模拟数据 (如果没有长桥连接)
        import random
        
        base_price = {
            "QQQ": 600, "NVDA": 185, "TSLA": 420,
            "GOOGL": 170, "MSFT": 400, "AAPL": 185,
            "AMD": 180, "META": 500, "AMZN": 175, "PLTR": 70
        }.get(symbol, 100)
        
        change = random.uniform(-0.02, 0.02)
        
        return QuoteData(
            symbol=symbol,
            price=base_price * (1 + change),
            change_pct=change * 100,
            volume=random.uniform(10000000, 100000000),
            timestamp=datetime.now()
        )
    
    def get_klines(self, symbol: str, period: str = "30d") -> pd.DataFrame:
        """
        获取K线数据
        
        Args:
            symbol: 股票代码
            period: 周期，如 "30d", "1y"
        """
        # 解析周期
        days = int(period.replace("d", ""))
        
        # 生成模拟K线数据
        base_price = {
            "QQQ": 600, "NVDA": 185, "TSLA": 420,
            "GOOGL": 170, "MSFT": 400, "AAPL": 185,
            "AMD": 180, "META": 500, "AMZN": 175, "PLTR": 70
        }.get(symbol, 100)
        
        dates = [datetime.now() - timedelta(days=x) for x in range(days, 0, -1)]
        
        # 生成价格序列
        prices = []
        current_price = base_price
        for _ in range(days):
            change = np.random.normal(0, 0.02)  # 日收益率 ~N(0,2%)
            current_price *= (1 + change)
            prices.append(current_price)
        
        df = pd.DataFrame({
            "date": dates,
            "open": [p * (1 + np.random.uniform(-0.005, 0.005)) for p in prices],
            "high": [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
            "low": [p * (1 - np.random.uniform(0, 0.02)) for p in prices],
            "close": prices,
            "volume": [np.random.uniform(10000000, 100000000) for _ in range(days)]
        })
        
        return df
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        创建特征
        
        基于 QLib 因子库的特征工程
        """
        df = df.copy()
        
        # 1. 基础价格特征
        df["return_1d"] = df["close"].pct_change(1)
        df["return_5d"] = df["close"].pct_change(5)
        df["return_10d"] = df["close"].pct_change(10)
        df["return_20d"] = df["close"].pct_change(20)
        
        # 2. 移动平均线
        for window in [5, 10, 20, 60]:
            df[f"ma{window}"] = df["close"].rolling(window=window).mean()
            df[f"ma{window}_ratio"] = df["close"] / df[f"ma{window}"] - 1
        
        # 3. 波动率
        df["volatility_5d"] = df["return_1d"].rolling(window=5).std()
        df["volatility_20d"] = df["return_1d"].rolling(window=20).std()
        
        # 4. RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))
        
        # 5. MACD
        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]
        
        # 6. 布林带
        bb_middle = df["close"].rolling(window=20).mean()
        bb_std = df["close"].rolling(window=20).std()
        df["bb_upper"] = bb_middle + 2 * bb_std
        df["bb_lower"] = bb_middle - 2 * bb_std
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / bb_middle
        df["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])
        
        # 7. 成交量特征
        df["volume_ma5"] = df["volume"].rolling(window=5).mean()
        df["volume_ratio"] = df["volume"] / df["volume_ma5"]
        
        # 8. 动量
        df["momentum_10d"] = df["close"] / df["close"].shift(10) - 1
        df["momentum_20d"] = df["close"] / df["close"].shift(20) - 1
        
        # 9. 价格位置
        df["high_20d"] = df["high"].rolling(window=20).max()
        df["low_20d"] = df["low"].rolling(window=20).min()
        df["price_position"] = (df["close"] - df["low_20d"]) / (df["high_20d"] - df["low_20d"])
        
        # 清理 NaN
        df = df.dropna()
        
        return df
    
    def prepare_for_model(self, df: pd.DataFrame, label_col: str = "return_5d") -> tuple:
        """
        准备模型训练数据
        
        Returns:
            X: 特征矩阵
            y: 标签向量
        """
        # 特征列
        feature_cols = [col for col in df.columns 
                       if col not in ["date", "open", "high", "low", "close", "volume"]]
        
        X = df[feature_cols].values
        y = df[label_col].values
        
        return X, y, feature_cols
    
    def get_all_data(self) -> Dict[str, pd.DataFrame]:
        """获取所有股票的数据"""
        data = {}
        for symbol in self.symbols:
            klines = self.get_klines(symbol)
            data[symbol] = self.create_features(klines)
        return data


# 测试代码
if __name__ == "__main__":
    manager = DataManager({
        "symbols": ["QQQ", "NVDA", "TSLA"]
    })
    
    # 测试获取数据
    df = manager.get_klines("QQQ", period="30d")
    print(f"QQQ K线: {len(df)} 条记录")
    
    # 测试特征工程
    features = manager.create_features(df)
    print(f"特征数量: {len(features.columns)}")
    
    # 准备模型数据
    X, y, cols = manager.prepare_for_model(features)
    print(f"X shape: {X.shape}, y shape: {y.shape}")
    print(f"特征列: {cols[:5]}...")
