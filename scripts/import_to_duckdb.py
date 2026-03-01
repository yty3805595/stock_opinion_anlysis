#!/usr/bin/env python3
"""
改进的数据导入 + 清洗模块
"""

import json
import duckdb
from datetime import datetime, date
from longbridge.openapi import Config, QuoteContext as Quote

CREDENTIALS_FILE = '/Users/yintaoye/.openclaw/workspace/skills/longbridge-trading/config/credentials.json'
DB_FILE = '/Users/yintaoye/.openclaw/workspace/data/market_data.duckdb'

def load_credentials():
    with open(CREDENTIALS_FILE) as f:
        return json.load(f).get('credentials', {})

def init_db():
    """初始化数据库"""
    conn = duckdb.connect(DB_FILE)
    
    # 股票行情表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_quotes (
            symbol VARCHAR,
            timestamp TIMESTAMP,
            open DOUBLE, high DOUBLE, low DOUBLE,
            close DOUBLE, volume BIGINT, prev_close DOUBLE,
            change_pct DOUBLE,
            is_clean BOOLEAN DEFAULT TRUE
        )
    """)
    
    # 期权行情表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS options_quotes (
            symbol VARCHAR, timestamp TIMESTAMP,
            last_done DOUBLE, change DOUBLE, volume BIGINT,
            implied_volatility DOUBLE, strike_price DOUBLE,
            expiry_date VARCHAR, option_type VARCHAR,
            is_clean BOOLEAN DEFAULT TRUE
        )
    """)
    
    # 异常记录表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY,
            symbol VARCHAR, timestamp TIMESTAMP,
            value DOUBLE, threshold_value DOUBLE,
            anomaly_type VARCHAR
        )
    """)
    
    conn.close()

def fetch_and_import():
    """获取并导入数据"""
    creds = load_credentials()
    quote = Quote(Config(
        app_key=creds['app_key'],
        app_secret=creds['app_secret'],
        access_token=creds['access_token']
    ))
    
    conn = duckdb.connect(DB_FILE)
    now = datetime.now()
    
    stocks = ['QQQ.US', 'NVDA.US', 'TSLA.US', 'GOOGL.US', 'MSFT.US', 'AMD.US', 'META.US']
    
    print("="*60)
    print("📥 导入股票数据")
    print("="*60)
    
    for sym in stocks:
        try:
            q = quote.quote([sym])[0]
            close = float(q.last_done) if q.last_done else float(q.prev_close)
            prev = float(q.prev_close)
            change = (close - prev) / prev * 100
            
            # 检测异常
            is_clean = abs(change) < 20  # 超过20%标记为异常
            
            conn.execute("""
                INSERT INTO stock_quotes 
                (symbol, timestamp, open, high, low, close, volume, prev_close, change_pct, is_clean)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                sym, now,
                float(q.open) if q.open else None,
                float(q.high) if q.high else None,
                float(q.low) if q.low else None,
                close,
                int(q.volume) if q.volume else 0,
                prev, change, is_clean
            ])
            
            # 记录异常
            if not is_clean:
                conn.execute("""
                    INSERT INTO anomalies (symbol, timestamp, value, threshold_value, anomaly_type)
                    VALUES (?, ?, ?, ?, ?)
                """, [sym, now, change, 20, 'PRICE_GAP'])
                print(f"  ⚠️ {sym}: {change:+.2f}% (异常)")
            else:
                print(f"  ✅ {sym}: {change:+.2f}%")
                
        except Exception as e:
            print(f"  ❌ {sym}: {e}")
    
    print("\n" + "="*60)
    print("📥 导入期权数据")
    print("="*60)
    
    # 期权数据 (简化版)
    option_stocks = ['NVDA.US', 'QQQ.US']
    
    for sym in option_stocks:
        try:
            expiries = quote.option_chain_expiry_date_list(sym)
            if not expiries:
                continue
            
            expiry = expiries[0]
            if isinstance(expiry, str):
                expiry_date = expiry
            else:
                expiry_date = expiry.strftime('%Y-%m-%d')
            
            chains = quote.option_chain_info_by_date(sym, expiry)
            
            # 正股价格
            stock_q = quote.quote([sym])[0]
            current = float(stock_q.last_done)
            atm = round(current / 5) * 5
            
            count = 0
            for c in chains:
                if abs(c.price - atm) <= 10:
                    for opt_type, opt_sym in [('call', c.call_symbol), ('put', c.put_symbol)]:
                        if opt_sym:
                            try:
                                opt_q = quote.quote([opt_sym])[0]
                                last = getattr(opt_q, 'last_done', None)
                                prev = getattr(opt_q, 'prev_close', None)
                                vol = getattr(opt_q, 'volume', 0)
                                
                                if last and last > 0:
                                    conn.execute("""
                                        INSERT INTO options_quotes 
                                        (symbol, timestamp, last_done, change, volume, strike_price, expiry_date, option_type, is_clean)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, [
                                        opt_sym, now,
                                        float(last),
                                        float(last - prev) if prev else 0,
                                        int(vol) if vol else 0,
                                        float(c.price),
                                        expiry_date,
                                        opt_type,
                                        True
                                    ])
                                    count += 1
                            except:
                                pass
            
            print(f"  ✅ {sym}: {count} 期权")
            
        except Exception as e:
            print(f"  ❌ {sym}: {e}")
    
    conn.close()

def show_report():
    """显示报告"""
    conn = duckdb.connect(DB_FILE)
    
    print("\n" + "="*60)
    print("📊 数据报告")
    print("="*60)
    
    # 股票
    print("\n📈 股票行情:")
    df = conn.execute("""
        SELECT symbol, close, prev_close, change_pct, is_clean
        FROM stock_quotes
        WHERE timestamp = (SELECT MAX(timestamp) FROM stock_quotes)
        ORDER BY change_pct DESC
    """).fetchdf()
    print(df.to_string(index=False))
    
    # 异常
    print("\n⚠️ 异常记录:")
    df = conn.execute("SELECT * FROM anomalies ORDER BY timestamp DESC LIMIT 5").fetchdf()
    if len(df) > 0:
        print(df.to_string(index=False))
    else:
        print("  无异常")
    
    # 期权
    print("\n📊 期权 (NVDA ATM):")
    df = conn.execute("""
        SELECT symbol, option_type, strike_price, last_done, change
        FROM options_quotes
        WHERE symbol LIKE 'NVDA%'
        ORDER BY strike_price, option_type
        LIMIT 6
    """).fetchdf()
    print(df.to_string(index=False))
    
    conn.close()

if __name__ == '__main__':
    import os
    os.makedirs('/Users/yintaoye/.openclaw/workspace/data', exist_ok=True)
    
    init_db()
    fetch_and_import()
    show_report()
    
    print("\n✅ 完成!")
