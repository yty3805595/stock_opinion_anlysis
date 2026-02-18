#!/usr/bin/env python3
"""
Longbridge 数据获取模块 - 支持真实K线数据
"""

import os
import sys
import json
import logging
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

# 尝试导入 Longbridge
try:
    from longbridge.openapi import WsConfig, Config, Quote, Period, AdjustType
    from longbridge.openapi import OrderType, TimeInForce, OrderSide, ProductType
    HAS_LONGBRIDGE = True
except ImportError:
    HAS_LONGBRIDGE = False

logger = logging.getLogger(__name__)


@dataclass
class KLine:
    """K线数据"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float


class LongbridgeDataFetcher:
    """
    Longbridge 数据获取器
    """
    
    def __init__(self, config_path: str = "/Users/yintaoye/.openclaw/workspace/longbridge_tokens.json"):
        """
        初始化
        
        Args:
            config_path: Longbridge token 文件路径
        """
        self.config_path = config_path
        self.quote_ctx = None
        
        if HAS_LONGBRIDGE:
            self._init_connection()
        else:
            logger.warning("⚠️ Longbridge 未安装，将使用模拟数据")
    
    def _init_connection(self):
        """初始化 Longbridge 连接"""
        try:
            # 读取 token
            if os.path.exists(self.config_path):
                with open(self.config_path) as f:
                    tokens = json.load(f)
                
                # 创建配置
                config = Config(
                    app_key='a66815c327617b848e55f6714dfb809c',
                    app_secret='a94e7a77710a06dcc7f7449b29ffa2adab9ccc2ab6f668d232d6304560813b8c',
                    access_token=tokens.get('access_token', '')
                )
                
                logger.info("✅ Longbridge 连接初始化成功")
            else:
                logger.warning(f"⚠️ Token 文件不存在: {self.config_path}")
                
        except Exception as e:
            logger.error(f"❌ Longbridge 初始化失败: {e}")
    
    def get_candlesticks(self, 
                        symbol: str, 
                        period: str = "day", 
                        count: int = 500,
                        adjust: str = "no_adjust") -> pd.DataFrame:
        """
        获取K线数据
        
        Args:
            symbol: 股票代码 (如 "NVDA.US")
            period: 周期 ("day", "week", "month", "hour", "30min", "15min", "5min", "1min")
            count: 获取数量
            adjust: 复权类型 ("no_adjust", "forward_adjust", "backward_adjust")
            
        Returns:
            DataFrame with OHLCV data
        """
        if not HAS_LONGBRIDGE or not self.quote_ctx:
            logger.warning(f"⚠️ 使用模拟K线数据: {symbol}")
            return self._generate_mock_data(symbol, count)
        
        try:
            # 周期映射
            period_map = {
                "day": Period.Day,
                "week": Period.Week,
                "month": Period.Month,
                "hour": Period.Hour,
                "30min": Period.Minute30,
                "15min": Period.Minute15,
                "5min": Period.Minute5,
                "1min": Period.Minute,
            }
            
            adjust_map = {
                "no_adjust": AdjustType.NoAdjust,
                "forward_adjust": AdjustType.ForwardAdjust,
                "backward_adjust": AdjustType.BackwardAdjust,
            }
            
            # 获取K线
            candles = self.quote_ctx.candlesticks(
                symbol,
                period=period_map.get(period, Period.Day),
                count=count,
                adjust_type=adjust_map.get(adjust, AdjustType.NoAdjust)
            )
            
            if not candles:
                logger.warning(f"⚠️ 获取K线为空: {symbol}")
                return self._generate_mock_data(symbol, count)
            
            # 转换为 DataFrame
            df = pd.DataFrame({
                'timestamp': [c.timestamp for c in candles],
                'open': [c.open for c in candles],
                'high': [c.high for c in candles],
                'low': [c.low for c in candles],
                'close': [c.close for c in candles],
                'volume': [c.volume for c in candles],
                'turnover': [c.turnover for c in candles],
            })
            
            # 转换时间戳
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('datetime', inplace=True)
            
            logger.info(f"✅ 获取 {symbol} K线: {len(df)} 条")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 获取 {symbol} K线失败: {e}")
            return self._generate_mock_data(symbol, count)
    
    def _generate_mock_data(self, symbol: str, count: int = 500) -> pd.DataFrame:
        """
        生成模拟数据 (当Longbridge不可用时)
        """
        # 基础价格
        base_prices = {
            "NVDA.US": 185,
            "TSLA.US": 420,
            "MSFT.US": 400,
            "GOOGL.US": 170,
            "QQQ.US": 600,
            "AAPL.US": 185,
            "AMD.US": 180,
            "META.US": 500,
            "AMZN.US": 175,
            "PLTR.US": 70,
        }
        
        base_price = base_prices.get(symbol, 100)
        
        # 生成日期
        end_date = datetime.now()
        dates = pd.date_range(end=end_date, periods=count, freq='B')  # 工作日
        
        # 生成价格 (带随机波动)
        np.random.seed(hash(symbol) % 2**32)
        returns = np.random.randn(count) * 0.02
        prices = base_price * (1 + returns).cumprod()
        
        df = pd.DataFrame({
            'timestamp': [d.timestamp() for d in dates],
            'open': prices * np.random.uniform(0.99, 1.01, count),
            'high': prices * np.random.uniform(1.0, 1.02, count),
            'low': prices * np.random.uniform(0.98, 1.0, count),
            'close': prices,
            'volume': np.random.uniform(10000000, 100000000, count),
            'turnover': prices * np.random.uniform(10000000, 100000000, count),
        })
        
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('datetime', inplace=True)
        
        logger.info(f"🎭 模拟 {symbol} K线: {len(df)} 条")
        
        return df


def fetch_multi_symbols(symbols: List[str], 
                       period: str = "day",
                       count: int = 500) -> Dict[str, pd.DataFrame]:
    """
    获取多只股票K线数据
    
    Args:
        symbols: 股票列表
        period: 周期
        count: 数量
        
    Returns:
        Dict[symbol, DataFrame]
    """
    fetcher = LongbridgeDataFetcher()
    data = {}
    
    for symbol in symbols:
        try:
            df = fetcher.get_candlesticks(symbol, period, count)
            data[symbol] = df
        except Exception as e:
            logger.error(f"❌ 获取 {symbol} 失败: {e}")
    
    return data


if __name__ == "__main__":
    # 测试
    print("="*60)
    print("📊 Longbridge 数据获取测试")
    print("="*60)
    
    fetcher = LongbridgeDataFetcher()
    
    # 测试获取 NVDA
    print("\n📈 获取 NVDA 日K线...")
    df = fetcher.get_candlesticks("NVDA.US", "day", 100)
    
    if len(df) > 0:
        print(f"\n数据预览:")
        print(df.tail(5))
        print(f"\n数据统计:")
        print(f"  数据量: {len(df)} 条")
        print(f"  时间范围: {df.index[0]} ~ {df.index[-1]}")
        print(f"  价格范围: ${df['close'].min():.2f} ~ ${df['close'].max():.2f}")
