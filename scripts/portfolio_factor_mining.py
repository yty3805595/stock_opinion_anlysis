#!/usr/bin/env python3
"""
美股持仓因子挖掘系统 - 针对用户持仓股票
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from longbridge_data_fetcher import LongbridgeDataFetcher
from rd_agent_factor_mining import FactorMiner, BacktestResult, RollingBacktestResult

# ============ 日志配置 ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 用户持仓配置
PORTFOLIO = {
    "QQQ": {"shares": 68, "avg_cost": 600.64},
    "NVDA": {"shares": 54, "avg_cost": 186.94},
    "TSLA": {"shares": 10, "avg_cost": 416.67},
    "GOOGL": {"shares": 33, "avg_cost": 309.00},
    "MSFT": {"shares": 25, "avg_cost": 401.78},
}


def mine_factors_for_symbol(symbol: str, fetcher: LongbridgeDataFetcher) -> Dict:
    """对单个股票进行因子挖掘"""
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 开始挖掘 {symbol} 的因子")
    logger.info(f"{'='*60}")
    
    # 获取K线数据
    df = fetcher.get_candlesticks(f"{symbol}.US", "day", 500)
    
    if len(df) == 0:
        logger.error(f"❌ 无法获取 {symbol} 数据")
        return None
    
    logger.info(f"✅ 获取 {symbol} 数据: {len(df)} 条")
    
    # 因子挖掘
    miner = FactorMiner(
        train_window=252,
        test_window=63,
        min_train_ic=0.02
    )
    
    factors = miner.mine_factors(df)
    
    # 滚动向前回测
    results = {}
    for factor in factors[:5]:  # 只对TOP5因子回测
        try:
            rolling_result = miner.rolling_forward_optimization(df, factor)
            results[factor.name] = {
                "factor": factor,
                "rolling_result": rolling_result,
                "ic": factor.ic,
                "rank_ic": factor.rank_ic,
                "total_return": rolling_result.combined_result.total_return,
                "annual_return": rolling_result.combined_result.annual_return,
                "max_drawdown": rolling_result.combined_result.max_drawdown,
                "sharpe": rolling_result.combined_result.sharpe_ratio,
                "win_rate": rolling_result.combined_result.win_rate,
                "robustness": rolling_result.robustness_score,
            }
        except Exception as e:
            logger.error(f"❌ {factor.name} 回测失败: {e}")
    
    return results


def generate_trading_signals(results: Dict[str, Dict]) -> Dict:
    """根据因子挖掘结果生成交易信号"""
    signals = {}
    
    for symbol, symbol_results in results.items():
        if not symbol_results:
            continue
        
        # 找到最佳因子
        best_factor = None
        best_score = -999
        
        for name, data in symbol_results.items():
            if isinstance(data, dict) and "robustness" in data:
                # 综合评分 = 稳健性 * 0.4 + 夏普 * 0.3 + 胜率 * 0.2 + 收益 * 0.1
                score = (
                    data["robustness"] * 0.4 +
                    min(data["sharpe"] / 3, 1) * 0.3 +
                    data["win_rate"] * 0.2 +
                    max(data["annual_return"], 0) * 0.1
                )
                if score > best_score:
                    best_score = score
                    best_factor = data
        
        if best_factor:
            # 生成信号
            if best_factor["annual_return"] > 0.1 and best_factor["sharpe"] > 0.5:
                level = "STRONG_BUY"
            elif best_factor["annual_return"] > 0 and best_factor["sharpe"] > 0:
                level = "BUY"
            elif best_factor["annual_return"] < 0 or best_factor["sharpe"] < 0:
                level = "SELL"
            else:
                level = "HOLD"
            
            signals[symbol] = {
                "signal_level": level,
                "best_factor": best_factor["factor"].name,
                "ic": best_factor["ic"],
                "annual_return": best_factor["annual_return"],
                "sharpe": best_factor["sharpe"],
                "win_rate": best_factor["win_rate"],
                "robustness": best_factor["robustness"],
                "confidence": best_factor["robustness"] * 100,
            }
    
    return signals


def print_summary(results: Dict, signals: Dict):
    """打印汇总报告"""
    print("\n" + "="*80)
    print("🎯 美股持仓因子挖掘汇总报告")
    print("="*80)
    
    # 有效因子汇总
    all_valid_factors = []
    for symbol, symbol_results in results.items():
        if not symbol_results:
            continue
        
        for name, data in symbol_results.items():
            if isinstance(data, dict) and "robustness" in data:
                all_valid_factors.append({
                    "symbol": symbol,
                    "factor": name,
                    "ic": data["ic"],
                    "direction": "正向" if data["ic"] > 0 else "反向",
                    "annual_return": data["annual_return"],
                    "sharpe": data["sharpe"],
                    "robustness": data["robustness"],
                })
    
    # 按稳健性排序
    all_valid_factors.sort(key=lambda x: x["robustness"], reverse=True)
    
    print(f"\n📊 有效因子汇总 (共 {len(all_valid_factors)} 个)")
    print("-"*80)
    print(f"{'股票':<8} {'因子名':<20} {'IC':<10} {'方向':<8} {'年化':<10} {'夏普':<8} {'稳健性':<8}")
    print("-"*80)
    
    for f in all_valid_factors:
        print(f"{f['symbol']:<8} {f['factor']:<20} {f['ic']:<10.4f} {f['direction']:<8} "
              f"{f['annual_return']*100:<9.1f}% {f['sharpe']:<8.2f} {f['robustness']:<8.2f}")
    
    # 交易信号
    print("\n" + "="*80)
    print("💰 交易信号")
    print("="*80)
    
    for symbol, data in signals.items():
        print(f"\n📌 {symbol}")
        print(f"   信号: {data['signal_level']}")
        print(f"   最佳因子: {data['best_factor']}")
        print(f"   IC: {data['ic']:.4f}")
        print(f"   年化收益: {data['annual_return']*100:.1f}%")
        print(f"   夏普比率: {data['sharpe']:.2f}")
        print(f"   胜率: {data['win_rate']*100:.1f}%")
        print(f"   稳健性: {data['robustness']:.2f}")
        print(f"   置信度: {data['confidence']:.0f}%")
    
    # 执行建议
    print("\n" + "="*80)
    print("🎯 执行建议")
    print("="*80)
    
    for symbol, data in signals.items():
        if data["signal_level"] in ["STRONG_BUY", "BUY"] and data["robustness"] > 0.4:
            position_info = PORTFOLIO.get(symbol, {})
            print(f"\n🟢 {symbol}: 建议买入/增持")
            print(f"   当前持仓: {position_info.get('shares', 0)} 股")
            print(f"   建议因子: {data['best_factor']}")
            print(f"   置信度: {data['confidence']:.0f}%")
        elif data["signal_level"] == "SELL" and data["robustness"] > 0.4:
            print(f"\n🔴 {symbol}: 建议减仓/止损")
        else:
            print(f"\n⚪ {symbol}: 建议持有 (置信度不足)")


def save_results(results: Dict, signals: Dict):
    """保存结果到文件"""
    output = {
        "timestamp": datetime.now().isoformat(),
        "portfolio": PORTFOLIO,
        "results": {},
        "signals": signals
    }
    
    for symbol, symbol_results in results.items():
        if not symbol_results:
            continue
        
        output["results"][symbol] = {}
        for name, data in symbol_results.items():
            if isinstance(data, dict):
                output["results"][symbol][name] = {
                    "factor_name": data["factor"].name if hasattr(data["factor"], "name") else name,
                    "ic": data["ic"],
                    "rank_ic": data.get("rank_ic", 0),
                    "annual_return": data["annual_return"],
                    "max_drawdown": data["max_drawdown"],
                    "sharpe": data["sharpe"],
                    "win_rate": data["win_rate"],
                    "robustness": data["robustness"],
                }
    
    with open("/tmp/portfolio_factor_results.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\n💾 结果已保存: /tmp/portfolio_factor_results.json")


def main():
    """主函数"""
    print("="*80)
    print("🎯 美股持仓因子挖掘系统")
    print("="*80)
    
    print(f"\n📊 监控持仓:")
    for symbol, info in PORTFOLIO.items():
        print(f"   {symbol}: {info['shares']} 股 @ ${info['avg_cost']}")
    
    # 初始化数据获取器
    fetcher = LongbridgeDataFetcher()
    
    # 对每只股票进行因子挖掘
    results = {}
    for symbol in PORTFOLIO.keys():
        results[symbol] = mine_factors_for_symbol(symbol, fetcher)
    
    # 生成交易信号
    signals = generate_trading_signals(results)
    
    # 打印汇总
    print_summary(results, signals)
    
    # 保存结果
    save_results(results, signals)


if __name__ == "__main__":
    main()
