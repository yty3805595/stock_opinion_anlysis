#!/usr/bin/env python3
"""
数据清洗模块
处理黑天鹅事件、异常值、缺失数据等
"""

import duckdb
from datetime import datetime, timedelta
import pandas as pd

DB_FILE = '/Users/yintaoye/.openclaw/workspace/data/market_data.duckdb'

def detect_black_swan(df, column='close', std_multiplier=3):
    """
    检测黑天鹅事件 (异常价格波动)
    
    使用方法: 如果日收益率超过 std_multiplier * 标准差，则标记为异常
    """
    if len(df) < 20:
        return []
    
    df = df.sort_values('timestamp')
    df['returns'] = df[column].pct_change()
    
    mean_return = df['returns'].mean()
    std_return = df['returns'].std()
    
    # 超过 N 倍标准差视为异常
    threshold = std_multiplier * std_return
    
    black_swan_indices = df[abs(df['returns']) > abs(threshold)].index.tolist()
    
    return black_swan_indices

def remove_outliers(df, columns=['close', 'volume'], std_multiplier=3):
    """
    移除异常值 (基于标准差)
    """
    df_clean = df.copy()
    
    for col in columns:
        if col in df_clean.columns:
            mean = df_clean[col].mean()
            std = df_clean[col].std()
            
            lower = mean - std_multiplier * std
            upper = mean + std_multiplier * std
            
            df_clean = df_clean[(df_clean[col] >= lower) & (df_clean[col] <= upper)]
    
    return df_clean

def fill_missing_data(df, method='forward'):
    """
    填充缺失数据
    方法: forward (前向填充), backward (后向填充), interpolate (插值)
    """
    df_clean = df.copy()
    
    if method == 'forward':
        df_clean = df_clean.fillna(method='ffill')
    elif method == 'backward':
        df_clean = df_clean.fillna(method='bfill')
    elif method == 'interpolate':
        df_clean = df_clean.interpolate(method='linear')
    
    return df_clean

def detect_gaps(df, column='close', gap_threshold=0.2):
    """
    检测价格跳空 (Gap)
    超过 threshold 比例的价格缺口
    """
    df = df.sort_values('timestamp')
    df['prev_close'] = df[column].shift(1)
    df['gap'] = (df[column] - df['prev_close']) / df['prev_close']
    
    gaps = df[abs(df['gap']) > gap_threshold]
    
    return gaps

def clean_options_data():
    """
    清洗期权数据
    """
    conn = duckdb.connect(DB_FILE)
    
    print("="*60)
    print("🧹 数据清洗 - 期权")
    print("="*60)
    
    # 1. 标记缺失数据
    missing_before = conn.execute("""
        SELECT COUNT(*) FROM options_quotes 
        WHERE last_done IS NULL OR last_done = 0
    """).fetchone()[0]
    
    print(f"\n📊 缺失数据: {missing_before} 条")
    
    # 2. 填充缺失数据 (使用前一时刻价格)
    conn.execute("""
        UPDATE options_quotes
        SET last_done = (
            SELECT o2.last_done 
            FROM options_quotes o2 
            WHERE o2.symbol = options_quotes.symbol 
            AND o2.timestamp < options_quotes.timestamp 
            ORDER BY o2.timestamp DESC 
            LIMIT 1
        )
        WHERE last_done IS NULL OR last_done = 0
    """)
    
    missing_after = conn.execute("""
        SELECT COUNT(*) FROM options_quotes 
        WHERE last_done IS NULL OR last_done = 0
    """).fetchone()[0]
    
    print(f"✅ 填充后缺失: {missing_after} 条")
    
    # 3. 检测异常价格 (超过50%日波动)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS options_anomalies AS
        SELECT symbol, timestamp, last_done, change,
               CASE 
                   WHEN ABS(change) > 0.5 THEN 'BLACK_SWAN'
                   WHEN ABS(change) > 0.3 THEN 'HIGH_VOLATILITY'
                   ELSE 'NORMAL'
               END as anomaly_type
        FROM options_quotes
        WHERE ABS(change) > 0.3
    """)
    
    anomaly_count = conn.execute("SELECT COUNT(*) FROM options_anomalies").fetchone()[0]
    print(f"⚠️  异常数据: {anomaly_count} 条")
    
    # 4. 过滤黑天鹅事件 (可选)
    # conn.execute("DELETE FROM options_quotes WHERE symbol IN (SELECT symbol FROM options_anomalies WHERE anomaly_type = 'BLACK_SWAN')")
    
    conn.close()

def clean_stock_data():
    """
    清洗股票数据
    """
    conn = duckdb.connect(DB_FILE)
    
    print("="*60)
    print("🧹 数据清洗 - 股票")
    print("="*60)
    
    # 1. 标记缺失数据
    missing = conn.execute("""
        SELECT COUNT(*) FROM stock_quotes 
        WHERE close IS NULL OR close = 0
    """).fetchone()[0]
    
    print(f"\n📊 缺失数据: {missing} 条")
    
    # 2. 填充
    conn.execute("""
        UPDATE stock_quotes
        SET close = (
            SELECT s2.close 
            FROM stock_quotes s2 
            WHERE s2.symbol = stock_quotes.symbol 
            AND s2.timestamp < stock_quotes.timestamp 
            ORDER BY s2.timestamp DESC 
            LIMIT 1
        )
        WHERE close IS NULL OR close = 0
    """)
    
    # 3. 创建清洗后的表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_quotes_clean AS
        SELECT *,
               CASE 
                   WHEN ABS(change_pct) > 0.2 THEN 'ANOMALY'
                   ELSE 'NORMAL'
               END as data_quality
        FROM (
            SELECT symbol, timestamp, open, high, low, close, volume, prev_close,
                   ROUND((close - prev_close) / prev_close * 100, 2) as change_pct
            FROM stock_quotes
        )
    """)
    
    anomaly = conn.execute("SELECT COUNT(*) FROM stock_quotes_clean WHERE data_quality = 'ANOMALY'").fetchone()[0]
    print(f"⚠️  异常数据: {anomaly} 条")
    
    conn.close()

def generate_report():
    """
    生成数据质量报告
    """
    conn = duckdb.connect(DB_FILE)
    
    print("\n" + "="*60)
    print("📊 数据质量报告")
    print("="*60)
    
    # 股票数据
    print("\n📈 股票数据:")
    result = conn.execute("""
        SELECT symbol, COUNT(*) as records,
               ROUND(AVG(close), 2) as avg_price,
               ROUND(MAX(change_pct), 2) as max_change,
               ROUND(MIN(change_pct), 2) as min_change
        FROM stock_quotes_clean
        GROUP BY symbol
    """).fetchdf()
    print(result.to_string(index=False))
    
    # 期权数据
    print("\n📊 期权数据:")
    result = conn.execute("""
        SELECT option_type, COUNT(*) as records,
               ROUND(AVG(last_done), 2) as avg_price
        FROM options_quotes
        WHERE last_done IS NOT NULL
        GROUP BY option_type
    """).fetchdf()
    print(result.to_string(index=False))
    
    conn.close()

if __name__ == '__main__':
    clean_stock_data()
    clean_options_data()
    generate_report()
    
    print("\n✅ 数据清洗完成!")
