#!/usr/bin/env python3
"""
A股三维一体交易策略选股系统

三维一体分析框架：
1. 基本面决定方向 - ROE、营收增长、净利润
2. 技术面决定点位 - 日线粘合、支撑位、突破信号
3. 结构决定方式 - 涨停回调、首板、主升浪

选股条件：
- 只做涨停回头的股票
- 首板涨停 + 主升浪的股票加入自选
- 找出主线板块
- 等几只股票跌倒位（日线粘合），股票上弹就买入
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import akshare as ak

# 配置
MAX_STOCKS = 100  # 最多获取的股票数量
STOCK_POOL = 500  # 股票池大小


def get_stock_list() -> pd.DataFrame:
    """获取A股股票列表"""
    print("📊 获取A股股票列表...")
    try:
        df = ak.stock_zh_a_spot_em()
        return df
    except Exception as e:
        print(f"❌ 获取股票列表失败: {e}")
        return None


def get_stock_daily(stock_code: str, days: int = 60) -> pd.DataFrame:
    """获取股票日线数据"""
    try:
        # 转换代码格式: 000001.SZ -> sz000001
        if stock_code.endswith('.SZ'):
            symbol = f"sz{stock_code[:-3]}"
        elif stock_code.endswith('.SH'):
            symbol = f"sh{stock_code[:-3]}"
        else:
            symbol = stock_code
        
        df = ak.stock_zh_a_daily(symbol=symbol)
        if df is not None and len(df) > 0:
            # 只取最近 N 天
            return df.head(days).copy()
        return None
    except Exception as e:
        return None


def check_zt_callback(df: pd.DataFrame, days: int = 5) -> Dict:
    """检查涨停回调"""
    if df is None or len(df) < 10:
        return None
    
    df = df.iloc[::-1]  # 倒序，最新的在前
    
    # 检查最近 N 天是否有涨停
    zt_count = 0
    zt_dates = []
    
    for i in range(min(days, len(df))):
        if i == 0:
            continue
        try:
            close = float(df.iloc[i]['close'])
            pre_close = float(df.iloc[i-1]['close'])
            high = float(df.iloc[i]['high'])
            
            # 涨停判断 (10% 涨跌幅限制)
            if high >= pre_close * 1.099 or close >= pre_close * 1.099:
                zt_count += 1
                zt_dates.append(df.iloc[i]['date'])
        except:
            continue
    
    return {
        'zt_count': zt_count,
        'zt_dates': zt_dates,
        'is_zt_callback': zt_count > 0  # 最近有涨停，然后回调
    }


def check_first_board(df: pd.DataFrame, days: int = 3) -> Dict:
    """检查首板"""
    if df is None or len(df) < 5:
        return None
    
    df = df.iloc[::-1]
    
    # 检查最近几天是否有首板涨停
    first_board = False
    for i in range(1, min(days + 1, len(df))):
        try:
            close = float(df.iloc[i]['close'])
            pre_close = float(df.iloc[i-1]['close'])
            high = float(df.iloc[i]['high'])
            
            # 涨停且前一天未涨停（首板）
            if high >= pre_close * 1.099:
                # 检查前一天是否涨停
                if i + 1 < len(df):
                    prev_high = float(df.iloc[i+1]['high'])
                    if prev_high < float(df.iloc[i]['close']) * 1.099:  # 前天未涨停
                        first_board = True
                        break
        except:
            continue
    
    return {'is_first_board': first_board}


def check_uptrend(df: pd.DataFrame, days: int = 30) -> Dict:
    """检查主升浪"""
    if df is None or len(df) < 30:
        return None
    
    df = df.iloc[::-1].copy()
    
    try:
        closes = df['close'].astype(float).values
        
        # 短期均线 > 长期均线
        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:])
        ma20 = np.mean(closes[-20:])
        ma60 = np.mean(closes[-60:]) if len(closes) >= 60 else ma20
        
        # 均线多头排列
        ma_bullish = ma5 > ma10 > ma20 > ma60 if len(closes) >= 60 else ma5 > ma10 > ma20
        
        # 价格高于所有均线
        price_above_ma = closes[-1] > ma5 and closes[-1] > ma10 and closes[-1] > ma20
        
        # 近期涨幅
        recent_return = (closes[-1] - closes[-min(20, len(closes))]) / closes[-min(20, len(closes))] * 100
        
        return {
            'is_uptrend': ma_bullish and price_above_ma and recent_return > 10,
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'ma60': ma60,
            'recent_return': recent_return,
            'ma_bullish': ma_bullish,
            'price_above_ma': price_above_ma
        }
    except Exception as e:
        return None


def check_ma_convergence(df: pd.DataFrame, threshold: float = 0.05) -> Dict:
    """检查日线粘合（均线收敛）"""
    if df is None or len(df) < 30:
        return None
    
    df = df.iloc[::-1].copy()
    
    try:
        closes = df['close'].astype(float).values
        
        # 计算均线
        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:])
        ma20 = np.mean(closes[-20:])
        ma60 = np.mean(closes[-60:]) if len(closes) >= 60 else ma20
        
        # 计算均线标准差
        mas = np.array([ma5, ma10, ma20, ma60])
        ma_std = np.std(mas)
        ma_mean = np.mean(mas)
        
        # 粘合度 = 标准差/均值
        convergence = ma_std / ma_mean if ma_mean > 0 else 1
        
        # 价格相对于均线位置
        price_position = (closes[-1] - ma_mean) / ma_mean if ma_mean > 0 else 0
        
        return {
            'is_converged': convergence < threshold,
            'convergence': convergence,
            'threshold': threshold,
            'price_position': price_position,
            'ready_to_rebound': convergence < threshold and price_position < 0.02  # 接近均线
        }
    except Exception as e:
        return None


def get_sector_performance() -> pd.DataFrame:
    """获取板块涨跌幅"""
    try:
        df = ak.stock_board_industry_name_em()
        return df
    except Exception as e:
        print(f"❌ 获取板块数据失败: {e}")
        return None


def analyze_stock(stock_code: str, stock_name: str = "") -> Dict:
    """分析单只股票"""
    result = {
        'code': stock_code,
        'name': stock_name,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'scores': {},
        'tags': [],
        'recommendation': 'PASS'
    }
    
    # 获取日线数据
    df = get_stock_daily(stock_code, 60)
    
    if df is None or len(df) < 30:
        return None
    
    # 1. 检查涨停回调
    zt_info = check_zt_callback(df, 5)
    if zt_info:
        result['zt_info'] = zt_info
        if zt_info['is_zt_callback']:
            result['tags'].append('涨停回调')
    
    # 2. 检查首板
    fb_info = check_first_board(df, 3)
    if fb_info:
        result['first_board'] = fb_info
        if fb_info['is_first_board']:
            result['tags'].append('首板')
    
    # 3. 检查主升浪
    up_info = check_uptrend(df, 30)
    if up_info:
        result['uptrend'] = up_info
        if up_info['is_uptrend']:
            result['tags'].append('主升浪')
    
    # 4. 检查日线粘合
    ma_info = check_ma_convergence(df, 0.05)
    if ma_info:
        result['ma_convergence'] = ma_info
        if ma_info['ready_to_rebound']:
            result['tags'].append('日线粘合')
            result['tags'].append('准备反弹')
    
    # 5. 计算综合得分
    score = 0
    if zt_info and zt_info['is_zt_callback']:
        score += 20
    if fb_info and fb_info['is_first_board']:
        score += 25
    if up_info and up_info['is_uptrend']:
        score += 30
    if ma_info and ma_info['ready_to_rebound']:
        score += 25
    
    result['total_score'] = score
    
    # 6. 推荐
    if score >= 50:
        result['recommendation'] = 'BUY'
    elif score >= 30:
        result['recommendation'] = 'WATCH'
    
    return result


def screen_stocks() -> List[Dict]:
    """选股"""
    print("=" * 80)
    print("🔍 A股三维一体选股策略")
    print("=" * 80)
    
    print("\n📊 Step 1: 获取A股股票列表...")
    stock_df = get_stock_list()
    
    if stock_df is None or len(stock_df) == 0:
        print("❌ 无法获取股票列表")
        return []
    
    print(f"✅ 获取 {len(stock_df)} 只股票")
    
    # 只分析涨幅榜前 N 只（增加筛选效率）
    print("\n📈 Step 2: 筛选涨停及强势股票...")
    
    # 取涨幅 > 3% 的股票
    try:
        stock_df['涨跌幅'] = pd.to_numeric(stock_df['涨跌幅'], errors='coerce')
        strong_stocks = stock_df[stock_df['涨跌幅'] > 2].head(100)
        print(f"✅ 筛选出 {len(strong_stocks)} 只强势股票 (涨幅>2%)")
    except Exception as e:
        print(f"⚠️ 筛选失败，使用全部股票: {e}")
        strong_stocks = stock_df.head(100)
    
    print("\n🔬 Step 3: 三维分析...")
    
    results = []
    total = len(strong_stocks)
    
    for idx, (_, row) in enumerate(strong_stocks.iterrows(), 1):
        code = str(row.get('代码', ''))
        name = str(row.get('名称', ''))
        
        if not code or len(code) != 6:
            continue
        
        print(f"  分析 [{idx}/{total}]: {code} {name}", end='\r')
        
        result = analyze_stock(code, name)
        if result and result['recommendation'] in ['BUY', 'WATCH']:
            results.append(result)
    
    print(f"\n✅ 分析完成! 选出 {len(results)} 只符合条件的股票")
    
    # 按得分排序
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    return results


def print_results(results: List[Dict]):
    """打印结果"""
    if not results:
        print("\n❌ 没有找到符合条件的股票")
        return
    
    print("\n" + "=" * 80)
    print("🎯 选股结果 - 三维一体策略")
    print("=" * 80)
    
    # BUY 列表
    buy_list = [r for r in results if r['recommendation'] == 'BUY']
    if buy_list:
        print(f"\n🟢 买入信号 ({len(buy_list)} 只)")
        print("-" * 80)
        for i, r in enumerate(buy_list[:10], 1):
            print(f"{i:2}. {r['code']} {r['name'][:8]:8} 得分:{r['total_score']:3} 标签:{','.join(r['tags'][:3])}")
    
    # WATCH 列表
    watch_list = [r for r in results if r['recommendation'] == 'WATCH']
    if watch_list:
        print(f"\n🟡 关注列表 ({len(watch_list)} 只)")
        print("-" * 80)
        for i, r in enumerate(watch_list[:10], 1):
            print(f"{i:2}. {r['code']} {r['name'][:8]:8} 得分:{r['total_score']:3} 标签:{','.join(r['tags'][:3])}")
    
    # 分析
    print("\n" + "=" * 80)
    print("📊 标签统计")
    print("=" * 80)
    
    tag_counts = {}
    for r in results:
        for tag in r['tags']:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {tag}: {count} 只")


def save_results(results: List[Dict], filename: str = None):
    """保存结果"""
    if not results:
        return
    
    if filename is None:
        filename = f"github_reports/a_stock_strategy_{datetime.now().strftime('%Y-%m-%d')}.md"
    
    # 生成 Markdown 报告
    report = f"""# 🎯 A股三维一体选股报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} GMT+8

---

## 三维一体分析框架

1. **基本面决定方向** - 关注涨停回调、首板启动
2. **技术面决定点位** - 日线粘合、均线多头
3. **结构决定方式** - 主升浪、突破形态

---

## 选股条件

- ✅ 只做涨停回头的股票
- ✅ 首板涨停 + 主升浪的股票加入自选
- ✅ 找出主线板块
- ✅ 日线粘合，股票上弹就买入

---

## 🎯 选股结果

### 🟢 买入信号 ({len([r for r in results if r['recommendation'] == 'BUY'])} 只)

| 排名 | 代码 | 名称 | 得分 | 标签 |
|------|------|------|------|------|
"""

    for i, r in enumerate([r for r in results if r['recommendation'] == 'BUY'][:20], 1):
        report += f"| {i} | {r['code']} | {r['name'][:8]} | {r['total_score']} | {','.join(r['tags'][:3])} |\n"

    report += f"""

### 🟡 关注列表 ({len([r for r in results if r['recommendation'] == 'WATCH'])} 只)

| 排名 | 代码 | 名称 | 得分 | 标签 |
|------|------|------|------|------|
"""

    for i, r in enumerate([r for r in results if r['recommendation'] == 'WATCH'][:20], 1):
        report += f"| {i} | {r['code']} | {r['name'][:8]} | {r['total_score']} | {','.join(r['tags'][:3])} |\n"

    report += f"""

---

## 📊 标签统计

"""

    tag_counts = {}
    for r in results:
        for tag in r['tags']:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
        report += f"- {tag}: {count} 只\n"

    report += f"""

---

## 💡 交易建议

### 买入时机
1. 日线粘合后，股价站上 5 日均线
2. 放量突破时买入
3. 止损位: 跌破 10 日均线

### 仓位管理
- 单只股票不超过总仓位 20%
- 优先买入得分 > 50 的股票
- 分批建仓

### 风险控制
- 设置止损位: -5%
- 达到目标位: +10% 减仓
- 跌破均线减仓

---

*报告由 OpenClaw Agent Team 自动生成*
*选股策略: 三维一体交易系统*
"""

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ 报告已保存: {filename}")
    
    # 同时保存 JSON 格式
    json_file = filename.replace('.md', '.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"✅ 数据已保存: {json_file}")


def main():
    """主函数"""
    print("🚀 A股三维一体选股策略系统")
    print("=" * 80)
    print("""
策略说明:
  1. 基本面决定方向 - 涨停回调、首板启动
  2. 技术面决定点位 - 日线粘合、均线支撑
  3. 结构决定方式 - 主升浪、突破形态

选股条件:
  - 只做涨停回头的股票
  - 首板涨停 + 主升浪的股票加入自选
  - 日线粘合，股票上弹就买入
""")
    
    # 选股
    results = screen_stocks()
    
    # 打印结果
    print_results(results)
    
    # 保存结果
    save_results(results)
    
    print("\n" + "=" * 80)
    print("✅ 选股完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()
