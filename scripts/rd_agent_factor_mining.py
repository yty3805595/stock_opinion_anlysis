#!/usr/bin/env python3
"""
Qlib RD-Agent 因子挖掘系统 - Longbridge 真实数据版

支持：
1. 从 Longbridge 获取真实K线数据
2. 滚动向前优化 (Rolling Forward Optimization)
3. 单利计算 (避免复利夸大收益)
4. AI辅助因子生成

参考：A Backtesting Protocol in the Era of Machine Learning
"""

import os
import sys
import json
import logging
import statistics
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# 添加模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from longbridge_data_fetcher import LongbridgeDataFetcher

# ============ 日志配置 ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PositionSide(Enum):
    """持仓方向"""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class SignalLevel(Enum):
    """信号等级"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class Factor:
    """因子"""
    name: str
    ic: float  # 信息系数
    icir: float  # IC_IR
    rank_ic: float  # 排名IC
    type: str  # technical/fundamental/sentiment
    description: str = ""


@dataclass
class BacktestResult:
    """回测结果"""
    total_return: float  # 总收益 (单利)
    annual_return: float  # 年化收益
    max_drawdown: float  # 最大回撤
    sharpe_ratio: float  # 夏普比率
    win_rate: float  # 胜率
    profit_factor: float  # 盈亏比
    num_trades: int  # 交易次数
    avg_hold_days: float  # 平均持仓天数


@dataclass
class RollingBacktestResult:
    """滚动向前回测结果"""
    period_results: List[BacktestResult]
    combined_result: BacktestResult
    out_of_sample_return: float
    out_of_sample_sharpe: float
    robustness_score: float  # 稳健性分数


class FactorMiner:
    """
    因子挖掘系统
    """
    
    def __init__(self, 
                 train_window: int = 252,  # 训练窗口 (交易日)
                 test_window: int = 63,     # 测试窗口 (63交易日 ≈ 3个月)
                 min_train_ic: float = 0.03,  # 最小训练IC
                 ):
        """
        初始化
        
        Args:
            train_window: 训练窗口 (交易日)
            test_window: 测试窗口 (交易日)
            min_train_ic: 最小训练IC
        """
        self.train_window = train_window
        self.test_window = test_window
        self.min_train_ic = min_train_ic
        
        self.factors: List[Factor] = []
        
        logger.info(f"✅ 因子挖掘系统初始化完成")
        logger.info(f"   训练窗口: {train_window} 交易日 (~1年)")
        logger.info(f"   测试窗口: {test_window} 交易日 (~3个月)")
        logger.info(f"   最小训练IC: {min_train_ic}")
    
    def calculate_ic(self, factor_values: pd.Series, returns: pd.Series) -> float:
        """计算信息系数 (IC)"""
        # 去除NaN
        valid_mask = ~(factor_values.isna() | returns.isna())
        if valid_mask.sum() < 30:
            return 0.0
        
        factor_clean = factor_values[valid_mask]
        returns_clean = returns[valid_mask]
        
        # Spearman 秩相关系数
        try:
            ic = factor_clean.corr(returns_clean, method='spearman')
        except:
            ic = 0.0
        
        return ic if not pd.isna(ic) else 0.0
    
    def calculate_rank_ic(self, factor_values: pd.Series, returns: pd.Series) -> float:
        """计算排名IC"""
        return self.calculate_ic(
            factor_values.rank(pct=True), 
            returns.rank(pct=True)
        )
    
    def calculate_icir(self, ic_series: pd.Series) -> float:
        """计算IC_IR"""
        if ic_series.std() == 0 or pd.isna(ic_series.std()):
            return 0.0
        return ic_series.mean() / ic_series.std()
    
    def calculate_technical_factors(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算技术因子"""
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        factors = {}
        
        # 1. 移动平均因子
        factors['ma5'] = close / close.rolling(5).mean() - 1
        factors['ma10'] = close / close.rolling(10).mean() - 1
        factors['ma20'] = close / close.rolling(20).mean() - 1
        factors['ma60'] = close / close.rolling(60).mean() - 1
        factors['ma120'] = close / close.rolling(120).mean() - 1
        
        # 2. 动量因子
        factors['momentum_5'] = close / close.shift(5) - 1
        factors['momentum_10'] = close / close.shift(10) - 1
        factors['momentum_20'] = close / close.shift(20) - 1
        factors['momentum_60'] = close / close.shift(60) - 1
        
        # 3. RSI 因子
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        factors['rsi'] = 100 - (100 / (1 + rs))
        
        # 4. 波动率因子
        factors['volatility_5'] = close.pct_change().rolling(5).std()
        factors['volatility_20'] = close.pct_change().rolling(20).std()
        factors['volatility_60'] = close.pct_change().rolling(60).std()
        
        # 5. 成交量因子
        factors['volume_ma5'] = volume / volume.rolling(5).mean() - 1
        factors['volume_ma20'] = volume / volume.rolling(20).mean() - 1
        
        # 6. 价格位置因子
        factors['high_low_ratio'] = (close - low) / (high - low + 1e-8)
        
        # 7. 布林带因子
        ma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        factors['bollinger_position'] = (close - ma20) / (2 * std20 + 1e-8)
        
        # 8. MACD 因子
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        factors['macd'] = macd - signal
        factors['macd_histogram'] = (macd - signal) / close
        
        # 9. ATR 因子
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        factors['atr'] = tr.rolling(14).mean()
        factors['atr_ratio'] = factors['atr'] / close
        
        return factors
    
    def mine_factors(self, df: pd.DataFrame) -> List[Factor]:
        """
        因子挖掘
        """
        # 计算未来收益
        returns = df['close'].pct_change().shift(-1)
        
        # 技术因子
        tech_factors = self.calculate_technical_factors(df)
        for name, values in tech_factors.items():
            ic = self.calculate_ic(values, returns)
            if abs(ic) >= self.min_train_ic:
                self.factors.append(Factor(
                    name=name,
                    ic=ic,
                    icir=0.0,
                    rank_ic=self.calculate_rank_ic(values, returns),
                    type='technical',
                    description=f"技术因子: {name}"
                ))
        
        # 按IC排序
        self.factors.sort(key=lambda x: abs(x.ic), reverse=True)
        
        logger.info(f"✅ 因子挖掘完成: {len(self.factors)} 个有效因子")
        
        return self.factors
    
    def rolling_forward_optimization(self, 
                                    df: pd.DataFrame,
                                    factor: Factor,
                                    train_window: int = None,
                                    test_window: int = None) -> RollingBacktestResult:
        """
        滚动向前优化
        """
        train_window = train_window or self.train_window
        test_window = test_window or self.test_window
        
        # 计算因子值
        close = df['close']
        factor_values = self.extract_factor(df, factor.name)
        returns = close.pct_change().shift(-1)
        
        # 合并
        combined = pd.DataFrame({
            'factor': factor_values,
            'returns': returns
        })
        
        # 去除NaN
        combined = combined.dropna()
        
        if len(combined) < train_window + test_window:
            logger.warning(f"⚠️ 数据不足: {len(combined)} < {train_window + test_window}")
            return RollingBacktestResult(
                period_results=[],
                combined_result=BacktestResult(0,0,0,0,0,0,0,0),
                out_of_sample_return=0.0,
                out_of_sample_sharpe=0.0,
                robustness_score=0.0
            )
        
        total_length = len(combined)
        period_results = []
        
        i = train_window
        
        while i + test_window <= total_length:
            # 训练窗口
            train_data = combined.iloc[i-train_window:i]
            
            # 测试窗口
            test_data = combined.iloc[i:i+test_window]
            
            # 计算训练IC
            train_ic = self.calculate_ic(train_data['factor'], train_data['returns'])
            
            if abs(train_ic) >= self.min_train_ic:
                # 训练通过，执行测试期策略
                result = self.single_period_backtest(
                    test_data['factor'], 
                    test_data['returns'], 
                    threshold=train_ic
                )
                period_results.append(result)
            else:
                # 训练不通过，空仓
                period_results.append(BacktestResult(
                    total_return=0.0,
                    annual_return=0.0,
                    max_drawdown=0.0,
                    sharpe_ratio=0.0,
                    win_rate=0.0,
                    profit_factor=0.0,
                    num_trades=0,
                    avg_hold_days=test_window
                ))
            
            i += test_window
        
        # 合并结果
        if period_results:
            combined_result = self.combine_results(period_results)
            oos_return = combined_result.total_return
            oos_sharpe = combined_result.sharpe_ratio
            robustness = self.calculate_robustness(period_results)
        else:
            combined_result = BacktestResult(0,0,0,0,0,0,0,0)
            oos_return = 0.0
            oos_sharpe = 0.0
            robustness = 0.0
        
        return RollingBacktestResult(
            period_results=period_results,
            combined_result=combined_result,
            out_of_sample_return=oos_return,
            out_of_sample_sharpe=oos_sharpe,
            robustness_score=robustness
        )
    
    def extract_factor(self, df: pd.DataFrame, factor_name: str) -> pd.Series:
        """提取因子"""
        factors = self.calculate_technical_factors(df)
        if factor_name in factors:
            return factors[factor_name]
        
        # 尝试从原始列获取
        if factor_name in df.columns:
            return df[factor_name]
        
        logger.warning(f"⚠️ 因子 {factor_name} 不存在")
        return pd.Series(dtype=float)
    
    def single_period_backtest(self, 
                               factor_values: pd.Series, 
                               returns: pd.Series,
                               threshold: float = 0.0) -> BacktestResult:
        """
        单期回测 (使用单利计算)
        """
        if len(factor_values) == 0 or len(returns) == 0:
            return BacktestResult(0,0,0,0,0,0,0,0)
        
        # 计算持仓信号
        if threshold > 0:
            # 正向因子: 因子值高的做多
            position = (factor_values > factor_values.quantile(0.8)).astype(float) - \
                      (factor_values < factor_values.quantile(0.2)).astype(float)
        else:
            # 反向因子: 因子值高的做空
            position = (factor_values < factor_values.quantile(0.2)).astype(float) - \
                      (factor_values > factor_values.quantile(0.8)).astype(float)
        
        # 策略收益 (单利)
        strategy_returns = position.shift(1) * returns
        
        # 去除NaN
        strategy_returns = strategy_returns.dropna()
        
        if len(strategy_returns) == 0:
            return BacktestResult(0,0,0,0,0,0,0,0)
        
        # 计算指标 (单利)
        total_return = strategy_returns.sum()
        
        # 年化 (假设252交易日)
        annual_return = total_return * (252 / len(strategy_returns))
        
        # 最大回撤
        cumulative = (1 + strategy_returns).cumprod()
        peak = cumulative.expanding().max()
        drawdown = (cumulative - peak) / peak
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0.0
        
        # 夏普比率
        if strategy_returns.std() > 0:
            sharpe = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252)
        else:
            sharpe = 0.0
        
        # 胜率
        wins = (strategy_returns > 0).sum()
        total = len(strategy_returns)
        win_rate = wins / total if total > 0 else 0.0
        
        # 盈亏比
        profits = strategy_returns[strategy_returns > 0].sum() if wins > 0 else 0
        losses = abs(strategy_returns[strategy_returns < 0].sum()) if (total - wins) > 0 else 1e-8
        profit_factor = profits / losses
        
        # 交易次数
        position_changes = position.diff().abs().sum()
        num_trades = int(position_changes)
        
        # 平均持仓天数
        avg_hold_days = len(strategy_returns) / (num_trades + 1)
        
        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            profit_factor=profit_factor,
            num_trades=num_trades,
            avg_hold_days=avg_hold_days
        )
    
    def combine_results(self, results: List[BacktestResult]) -> BacktestResult:
        """合并多期回测结果"""
        if not results:
            return BacktestResult(0,0,0,0,0,0,0,0)
        
        total_trades = sum(r.num_trades for r in results) or 1
        
        combined = BacktestResult(
            total_return=sum(r.total_return * r.num_trades for r in results) / total_trades,
            annual_return=sum(r.annual_return * r.num_trades for r in results) / total_trades,
            max_drawdown=max(r.max_drawdown for r in results),
            sharpe_ratio=statistics.mean(r.sharpe_ratio for r in results),
            win_rate=sum(r.win_rate * r.num_trades for r in results) / total_trades,
            profit_factor=sum(r.profit_factor * r.num_trades for r in results) / total_trades,
            num_trades=sum(r.num_trades for r in results),
            avg_hold_days=sum(r.avg_hold_days * r.num_trades for r in results) / total_trades
        )
        
        return combined
    
    def calculate_robustness(self, results: List[BacktestResult]) -> float:
        """计算稳健性分数"""
        if not results:
            return 0.0
        
        # 正收益期占比
        win_periods = sum(1 for r in results if r.total_return > 0)
        win_rate_periods = win_periods / len(results)
        
        # 夏普比率平均
        avg_sharpe = statistics.mean(r.sharpe_ratio for r in results)
        
        # 最大回撤惩罚
        avg_drawdown = statistics.mean(r.max_drawdown for r in results)
        
        # 稳健性分数
        robustness = (
            win_rate_periods * 0.4 +
            min(avg_sharpe / 2, 1) * 0.4 +
            (1 - min(avg_drawdown * 2, 1)) * 0.2
        )
        
        return robustness
    
    def generate_report(self, factor: Factor, rolling_result: RollingBacktestResult) -> str:
        """生成因子回测报告"""
        r = rolling_result.combined_result
        oos = rolling_result
        
        report = f"""
{'='*70}
🎯 因子挖掘报告: {factor.name}
{'='*70}

📊 因子基本信息
├── 类型: {factor.type}
├── IC: {factor.ic:.4f}
├── Rank IC: {factor.rank_ic:.4f}
└── 描述: {factor.description}

📈 滚动向前回测结果
├── 训练窗口: {self.train_window} 交易日
├── 测试窗口: {self.test_window} 交易日
├── 测试期数: {len(rolling_result.period_results)}
│
├── 📊 综合表现 (单利)
│   ├── 总收益: {r.total_return*100:.2f}%
│   ├── 年化收益: {r.annual_return*100:.2f}%
│   ├── 最大回撤: {r.max_drawdown*100:.2f}%
│   ├── 夏普比率: {r.sharpe_ratio:.2f}
│   ├── 胜率: {r.win_rate*100:.1f}%
│   ├── 盈亏比: {r.profit_factor:.2f}
│   └── 交易次数: {r.num_trades}
│
├── 📊 样本外表现
│   ├── 样本外收益: {oos.out_of_sample_return*100:.2f}%
│   └── 样本外夏普: {oos.out_of_sample_sharpe:.2f}
│
└── 📊 稳健性评估
    └── 稳健性分数: {oos.robustness_score:.2f}/1.00

💡 评估标准
├── 稳健性 > 0.6: ✅ 因子稳健
├── 稳健性 0.4-0.6: ⚠️ 需进一步验证
└── 稳健性 < 0.4: ❌ 因子不稳定

{'='*70}
"""
        return report


def main():
    """主函数 - 使用 Longbridge 真实数据"""
    print("="*70)
    print("🎯 Qlib RD-Agent 因子挖掘系统 - Longbridge 真实数据版")
    print("="*70)
    
    # 监控的股票列表
    SYMBOLS = [
        "NVDA.US",
        "TSLA.US",
        "MSFT.US",
        "GOOGL.US",
        "QQQ.US",
        "AAPL.US",
        "AMD.US",
        "META.US",
        "AMZN.US",
        "PLTR.US",
    ]
    
    # 创建数据获取器
    print("\n📊 初始化 Longbridge 数据获取器...")
    data_fetcher = LongbridgeDataFetcher()
    
    # 获取 NVDA 数据进行测试
    print("\n📈 获取 NVDA 真实K线数据...")
    df = data_fetcher.get_candlesticks("NVDA.US", "day", 500)
    
    if len(df) == 0:
        print("❌ 无法获取数据，使用模拟数据")
        return
    
    print(f"\n✅ 获取数据: {len(df)} 条K线")
    print(f"   时间范围: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}")
    print(f"   价格范围: ${df['close'].min():.2f} ~ ${df['close'].max():.2f}")
    
    # 创建因子挖掘系统
    print("\n🔬 初始化因子挖掘系统...")
    miner = FactorMiner(
        train_window=252,
        test_window=63,
        min_train_ic=0.02
    )
    
    # 因子挖掘
    print("\n🔍 开始因子挖掘...")
    factors = miner.mine_factors(df)
    
    if factors:
        print(f"\n📊 发现 {len(factors)} 个有效因子:")
        for i, f in enumerate(factors[:10], 1):
            direction = "正向" if f.ic > 0 else "反向"
            print(f"  {i}. {f.name}: IC={f.ic:.4f} ({direction})")
        
        # 对TOP因子进行滚动向前回测
        print("\n📈 对TOP因子进行滚动向前回测...")
        top_factor = factors[0]
        
        rolling_result = miner.rolling_forward_optimization(df, top_factor)
        
        # 生成报告
        report = miner.generate_report(top_factor, rolling_result)
        print(report)
        
        # 保存结果
        results = {
            "symbol": "NVDA.US",
            "date": datetime.now().isoformat(),
            "factors": [
                {
                    "name": f.name,
                    "ic": f.ic,
                    "rank_ic": f.rank_ic,
                    "type": f.type
                }
                for f in factors[:10]
            ],
            "top_factor": top_factor.name,
            "rolling_result": {
                "total_return": rolling_result.combined_result.total_return,
                "annual_return": rolling_result.combined_result.annual_return,
                "max_drawdown": rolling_result.combined_result.max_drawdown,
                "sharpe_ratio": rolling_result.combined_result.sharpe_ratio,
                "win_rate": rolling_result.combined_result.win_rate,
                "robustness_score": rolling_result.robustness_score,
            }
        }
        
        with open("/tmp/factor_mining_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 结果已保存: /tmp/factor_mining_results.json")
    else:
        print("\n⚠️ 未发现有效因子")


if __name__ == "__main__":
    main()
