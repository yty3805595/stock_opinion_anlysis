#!/usr/bin/env python3
"""
Akshare A股市场分析报告生成器
使用 akshare 获取免费 A股数据
"""

import os
import json
from datetime import datetime

def get_market_overview():
    """获取市场概览"""
    try:
        import akshare as ak
        
        print("📊 获取市场概览...")
        
        # 1. 指数实时行情
        index_df = ak.stock_zh_index_spot_em()
        
        # 提取关键指数
        key_indices = {
            "上证指数": index_df[index_df['代码'] == '000001'],
            "深证成指": index_df[index_df['代码'] == '399001'],
            "创业板指": index_df[index_df['代码'] == '399006'],
            "沪深300": index_df[index_df['代码'] == '000300'],
            "科创50": index_df[index_df['代码'] == '000688'],
        }
        
        return index_df, key_indices
    except Exception as e:
        print(f"❌ 获取市场概览失败: {e}")
        return None, None

def get_index_daily(symbol="sh000001"):
    """获取指数日线"""
    try:
        import akshare as ak
        df = ak.stock_zh_index_daily(symbol=symbol)
        return df
    except Exception as e:
        print(f"❌ 获取日线数据失败: {e}")
        return None

def generate_report():
    """生成分析报告"""
    
    print("=" * 80)
    print("📊 A股市场分析报告")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} GMT+8")
    print("=" * 80)
    
    # 获取市场概览
    index_df, key_indices = get_market_overview()
    
    if index_df is None:
        print("❌ 无法获取市场数据")
        return None
    
    # 构建报告
    report = f"""# 📊 A股市场分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} GMT+8  
**数据来源**: akshare (东方财富)

---

## 🌏 市场概览

### 核心指数

| 指数 | 最新价 | 涨跌幅 | 涨跌额 | 成交量 |
|------|--------|--------|--------|--------|
"""
    
    for name, df in key_indices.items():
        if len(df) > 0:
            row = df.iloc[0]
            report += f"| {name} | {row['最新价']} | {row['涨跌幅']}% | {row['涨跌额']} | {row['成交量']:,} |\n"
    
    # 获取上证指数日线
    sh_daily = get_index_daily("sh000001")
    
    if sh_daily is not None and len(sh_daily) > 0:
        recent = sh_daily.head(10)
        report += f"""

### 上证指数近期走势

| 日期 | 开盘 | 最高 | 最低 | 收盘 | 成交量 |
|------|------|------|------|------|--------|
"""
        for _, row in recent.iterrows():
            report += f"| {row['date']} | {row['open']} | {row['high']} | {row['low']} | {row['close']} | {int(row['volume']):,} |\n"
    
    # 市场分析
    report += f"""

## 📈 市场分析

### 今日表现

- **上证指数**: 
  - 最新: {key_indices['上证指数'].iloc[0]['最新价'] if len(key_indices['上证指数']) > 0 else 'N/A'}
  - 涨跌幅: {key_indices['上证指数'].iloc[0]['涨跌幅'] if len(key_indices['上证指数']) > 0 else 'N/A'}%

- **深证成指**:
  - 最新: {key_indices['深证成指'].iloc[0]['最新价'] if len(key_indices['深证成指']) > 0 else 'N/A'}
  - 涨跌幅: {key_indices['深证成指'].iloc[0]['涨跌幅'] if len(key_indices['深证成指']) > 0 else 'N/A'}%

- **创业板指**:
  - 最新: {key_indices['创业板指'].iloc[0]['最新价'] if len(key_indices['创业板指']) > 0 else 'N/A'}
  - 涨跌幅: {key_indices['创业板指'].iloc[0]['涨跌幅'] if len(key_indices['创业板指']) > 0 else 'N/A'}%

### 热点板块

(基于涨跌幅排行)

"""

    # 添加涨幅榜前5
    if len(index_df) > 0:
        top_gainers = index_df.nlargest(5, '涨跌幅')
        report += "#### 涨幅榜前5\n"
        for _, row in top_gainers.iterrows():
            report += f"- {row['名称']}: +{row['涨跌幅']}%\n"
        
        # 添加跌幅榜前5
        top_losers = index_df.nsmallest(5, '涨跌幅')
        report += "\n#### 跌幅榜前5\n"
        for _, row in top_losers.iterrows():
            report += f"- {row['名称']}: {row['涨跌幅']}%\n"

    report += f"""

---

## 🎯 明日展望

### 支撑位
- 上证指数: 待分析

### 压力位
- 上证指数: 待分析

### 风险提示
- 成交量变化
- 板块轮动
- 政策影响

---

*报告由 OpenClaw Agent Team 自动生成*  
*数据来源: akshare (东方财富)*
"""
    
    return report

def main():
    report = generate_report()
    
    if report:
        # 保存报告
        filename = f"github_reports/a_stock_{datetime.now().strftime('%Y-%m-%d')}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n✅ 报告已保存: {filename}")
        
        # 打印报告预览
        print("\n" + "=" * 80)
        print("📄 报告预览")
        print("=" * 80)
        print(report[:1500] + "...")
    else:
        print("❌ 生成报告失败")

if __name__ == "__main__":
    main()
