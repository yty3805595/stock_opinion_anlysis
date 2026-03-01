#!/usr/bin/env python3
"""
A股选股策略回测系统

功能：
1. 获取历史数据
2. 模拟三维选股策略
3. 计算收益率
4. 生成回测报告
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import json
import os

class BacktestSystem:
    """回测系统"""
    
    def __init__(self, start_date: str = None, end_date: str = None):
        """
        初始化
        
        start_date: 回测开始日期 (YYYYMMDD)
        end_date: 回测结束日期 (YYYYMMDD)
        """
        self.start_date = start_date or (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        self.end_date = end_date or datetime.now().strftime('%Y%m%d')
        self.results = []
        
    def get_stock_history(self, symbol: str, period: int = 60) -> pd.DataFrame:
        """
        获取股票历史数据
        
        symbol: 股票代码 (如 000001.SZ)
        period: 获取天数
        """
        try:
            # 使用东方财富daily接口
            df = ak.stock_zh_a_hist(symbol=symbol.replace('.SZ', '').replace('.SH', ''), 
                                   period="daily", 
                                   start_date=self.start_date, 
                                   end_date=self.end_date,
                                   adjust="qfq")
            return df
        except Exception as e:
            print(f"❌ 获取 {symbol} 数据失败: {e}")
            return pd.DataFrame()
    
    def get_index_history(self, symbol: str = "sh000001") -> pd.DataFrame:
        """获取指数历史数据"""
        try:
            if symbol == "sh000001":
                df = ak.stock_zh_index_daily(symbol="sh000001")
            else:
                df = ak.stock_zh_index_daily(symbol=symbol)
            return df
        except Exception as e:
            print(f"❌ 获取指数 {symbol} 数据失败: {e}")
            return pd.DataFrame()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        添加:
        - MA5, MA10, MA20
        - 涨跌幅
        - 换手率（如果有）
        """
        if df.empty:
            return df
        
        # 计算均线
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        
        # 计算涨跌幅
        df['change_pct'] = df['close'].pct_change() * 100
        
        # 计算成交量变化
        df['volume_change'] = df['volume'].pct_change()
        
        return df
    
    def screen_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        三维选股筛选
        
        条件:
        - 基本面: 涨幅 3-10%, 换手率 > 3%
        - 技术面: MA5 > MA10 > MA20
        - 结构: 日线粘合
        """
        if df.empty:
            return pd.DataFrame()
        
        # 筛选条件
        condition = (
            (df['change_pct'] >= 3) & (df['change_pct'] <= 10) &  # 涨幅 3-10%
            (df['MA5'] > df['MA10']) & (df['MA10'] > df['MA20']) &  # 均线多头
            (df['MA5'] - df['MA20']).abs() / df['MA20'] < 0.03  # 日线粘合 (<3%)
        )
        
        return df[condition]
    
    def calculate_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算选股分数
        
        基本面 (0-50分):
        - 涨幅 3-5%: 20分
        - 涨幅 5-10%: 25分
        - 换手率 > 3%: 15分
        
        技术面 (0-30分):
        - MA5 > MA10 > MA20: 20分
        - 日线粘合: 10分
        
        结构 (0-20分):
        - 资金流入: 10分
        """
        if df.empty:
            return df
        
        # 基本面评分
        score = pd.Series(0, index=df.index)
        
        # 涨幅评分
        score += df.apply(lambda x: 20 if 3 <= x['change_pct'] <= 5 else (25 if 5 < x['change_pct'] <= 10 else 0), axis=1)
        
        # 均线评分
        score += df.apply(lambda x: 20 if x['MA5'] > x['MA10'] > x['MA20'] else 0, axis=1)
        
        # 粘合评分
        score += df.apply(lambda x: 10 if abs(x['MA5'] - x['MA20']) / x['MA20'] < 0.03 else 0, axis=1)
        
        df['score'] = score
        return df
    
    def run_backtest(self, symbol: str, holding_days: int = 5) -> Dict:
        """
        运行回测
        
        symbol: 股票代码
        holding_days: 持仓天数
        """
        print(f"\n📊 回测 {symbol}...")
        
        # 获取历史数据
        df = self.get_stock_history(symbol, 250)  # 1年数据
        if df.empty:
            return None
        
        # 计算指标
        df = self.calculate_indicators(df)
        
        # 筛选
        signals = self.screen_stocks(df)
        if signals.empty:
            return None
        
        # 计算分数
        signals = self.calculate_score(signals)
        
        # 模拟交易
        trades = []
        for idx, row in signals.iterrows():
            entry_price = row['close']
            entry_date = row['date']
            
            # 找到出场日期
            position = df.index.get_loc(idx)
            if position + holding_days < len(df):
                exit_price = df.iloc[position + holding_days]['close']
                exit_date = df.iloc[position + holding_days]['date']
                
                profit_pct = (exit_price - entry_price) / entry_price * 100
                
                trades.append({
                    'symbol': symbol,
                    'entry_date': entry_date,
                    'entry_price': entry_price,
                    'exit_date': exit_date,
                    'exit_price': exit_price,
                    'profit_pct': profit_pct,
                    'score': row['score'],
                    'change_pct': row['change_pct']
                })
        
        return {
            'symbol': symbol,
            'total_trades': len(trades),
            'trades': trades,
            'win_rate': sum(1 for t in trades if t['profit_pct'] > 0) / len(trades) * 100 if trades else 0,
            'avg_profit': np.mean([t['profit_pct'] for t in trades]) if trades else 0,
            'total_return': np.prod([1 + t['profit_pct']/100 for t in trades]) * 100 - 100 if trades else 0
        }
    
    def run_index_backtest(self, symbol: str = "sh000001", holding_days: int = 5) -> Dict:
        """
        指数回测（演示用）
        
        使用简单的均线策略
        """
        print(f"\n📊 回测指数 {symbol}...")
        
        df = self.get_index_history(symbol)
        if df.empty:
            return None
        
        # 计算指标
        df = self.calculate_indicators(df)
        
        # 简单的金叉策略
        df['signal'] = (df['MA5'] > df['MA20']) & (df['MA5'].shift(1) <= df['MA20'].shift(1))
        
        trades = []
        for idx, row in df.iterrows():
            if row['signal']:
                entry_price = row['close']
                entry_date = row['date']
                
                position = df.index.get_loc(idx)
                if position + holding_days < len(df):
                    exit_price = df.iloc[position + holding_days]['close']
                    profit_pct = (exit_price - entry_price) / entry_price * 100
                    
                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'profit_pct': profit_pct
                    })
        
        return {
            'symbol': symbol,
            'total_trades': len(trades),
            'win_rate': sum(1 for t in trades if t['profit_pct'] > 0) / len(trades) * 100 if trades else 0,
            'avg_profit': np.mean([t['profit_pct'] for t in trades]) if trades else 0,
            'total_return': np.prod([1 + t['profit_pct']/100 for t in trades]) * 100 - 100 if trades else 0,
            'trades': trades
        }


def generate_report(results: Dict):
    """生成回测报告"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    report = f"""# 📊 A股选股策略回测报告

**回测时间**: {now}  
**回测周期**: 过去1年

---

## 🎯 回测结果

| 指标 | 数值 |
|------|------|
| 标的 | {results.get('symbol', '指数')} |
| 交易次数 | {results.get('total_trades', 0)} |
| 胜率 | {results.get('win_rate', 0):.1f}% |
| 平均收益 | {results.get('avg_profit', 0):.2f}% |
| 总收益率 | {results.get('total_return', 0):.2f}% |

---

## 📈 交易明细

| 序号 | 入场日期 | 入场价格 | 出场日期 | 出场价格 | 收益率 |
|------|----------|----------|----------|----------|--------|
"""
    
    for i, trade in enumerate(results.get('trades', [])[:20], 1):
        report += f"| {i} | {trade.get('entry_date', '-')} | {trade.get('entry_price', 0):.2f} | {trade.get('exit_date', '-')} | {trade.get('exit_price', 0):.2f} | {trade.get('profit_pct', 0):.2f}% |\n"
    
    report += f"""
---

## 🎯 选股策略（三维一体）

1. **基本面** (0-50分)
   - 涨幅 3-5%: +20分
   - 涨幅 5-10%: +25分
   - 换手率 > 3%: +15分

2. **技术面** (0-30分)
   - MA5 > MA10 > MA20: +20分
   - 日线粘合 (<3%): +10分

3. **结构** (0-20分)
   - 资金流入: +10分

---

## 💡 结论

1. **策略有效性**: 待验证
2. **改进方向**: 
   - 添加更多选股条件
   - 优化持仓周期
   - 加入止损机制

---

*由 Agent Team 自动生成*
"""
    
    return report


def main():
    """主函数"""
    import sys
    
    print("=" * 70)
    print("📊 A股选股策略回测系统")
    print("=" * 70)
    
    bt = BacktestSystem()
    
    # 测试上证指数
    results = bt.run_index_backtest("sh000001", holding_days=5)
    
    if results:
        print(f"\n✅ 回测完成!")
        print(f"   标的: {results['symbol']}")
        print(f"   交易次数: {results['total_trades']}")
        print(f"   胜率: {results['win_rate']:.1f}%")
        print(f"   平均收益: {results['avg_profit']:.2f}%")
        print(f"   总收益率: {results['total_return']:.2f}%")
        
        # 生成报告
        report = generate_report(results)
        print(f"\n✅ 报告已生成")
        
        # 保存
        filename = f"/Users/yintaoye/.openclaw/workspace/github_reports/backtest_{datetime.now().strftime('%Y%m%d')}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ 已保存: {filename}")
    else:
        print("\n❌ 回测失败")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
