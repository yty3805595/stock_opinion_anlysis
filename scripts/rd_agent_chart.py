#!/usr/bin/env python3
"""
RD-Agent 因子可视化图表
生成 TradingView Lightweight Charts HTML 页面

运行: python3 scripts/rd_agent_chart.py
"""

import os
import sys
import json
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np


def calculate_indicators(df):
    """计算技术指标"""
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']
    
    # 均线
    df['ma5'] = close.rolling(5).mean()
    df['ma10'] = close.rolling(10).mean()
    df['ma20'] = close.rolling(20).mean()
    df['ma60'] = close.rolling(60).mean()
    
    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    return df


def generate_chart(symbol="NVDA"):
    """生成图表"""
    print(f"📊 生成 {symbol} 图表...")
    
    # 获取数据
    ticker = yf.Ticker(symbol)
    df = ticker.history(start="2025-01-01", end=datetime.now().strftime("%Y-%m-%d"))
    
    if df is None or len(df) < 60:
        print(f"❌ 数据不足")
        return
    
    df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
    df = calculate_indicators(df)
    
    # 准备数据
    candle_data = []
    volume_data = []
    rsi_data = []
    macd_data = []
    
    for i, row in df.tail(120).iterrows():  # 最近120天
        date_str = i.strftime('%Y-%m-%d')
        
        candle_data.append({
            "time": date_str,
            "open": float(row['open']),
            "high": float(row['high']),
            "low": float(row['low']),
            "close": float(row['close']),
            "ma5": float(row['ma5']) if pd.notna(row['ma5']) else None,
            "ma20": float(row['ma20']) if pd.notna(row['ma20']) else None,
        })
        
        volume_data.append({
            "time": date_str,
            "value": int(row['volume']),
            "color": '#26a69a' if row['close'] >= row['open'] else '#ef5350'
        })
        
        if pd.notna(row['rsi']):
            rsi_data.append({
                "time": date_str,
                "value": float(row['rsi'])
            })
        
        if pd.notna(row['macd']):
            macd_data.append({
                "time": date_str,
                "macd": float(row['macd_hist']),
                "signal": float(row['macd_signal']),
                "value": float(row['macd'])
            })
    
    # 当前值
    current = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else current
    
    price = float(current['close'])
    change = (price / float(prev['close']) - 1) * 100
    rsi = float(current['rsi']) if pd.notna(current['rsi']) else 50
    
    # 信号
    ma5 = float(current['ma5']) if pd.notna(current['ma5']) else price
    ma20 = float(current['ma20']) if pd.notna(current['ma20']) else price
    
    if ma5 > ma20 and rsi < 70:
        signal = "BUY"
        signal_class = "buy"
    elif ma5 < ma20 or rsi > 70:
        signal = "SELL"
        signal_class = "sell"
    else:
        signal = "HOLD"
        signal_class = "hold"
    
    # 因子表
    factor_table = f"""
        <tr><td>MA5/MA20</td><td>{ma5:.2f}/{ma20:.2f}</td><td class="signal-{signal_class}">{signal}</td><td>均线多头排列</td></tr>
        <tr><td>RSI(14)</td><td>{rsi:.1f}</td><td class="signal-{'buy' if rsi < 30 else 'sell' if rsi > 70 else 'hold'}">{'超卖' if rsi < 30 else '超买' if rsi > 70 else '正常'}</td><td>RSI > 70 超买, < 30 超卖</td></tr>
        <tr><td>MACD</td><td>{float(current['macd']):.2f}</td><td class="signal-{'buy' if float(current['macd']) > 0 else 'sell'}">{'多头' if float(current['macd']) > 0 else '空头'}</td><td>DIF > 0 多头</td></tr>
        <tr><td>成交量</td><td>{int(current['volume']/1000000):.1f}M</td><td class="signal-{'buy' if float(current['volume'])/float(df['volume'].rolling(20).mean().iloc[-1]) > 1.5 else 'hold'}">{'放量' if float(current['volume'])/float(df['volume'].rolling(20).mean().iloc[-1]) > 1.5 else '正常'}</td><td>> 150% 均线为放量</td></tr>
    """
    
    # 生成 HTML - 使用字符串替换
    candle_json = json.dumps(candle_data)
    volume_json = json.dumps(volume_data)
    rsi_json = json.dumps(rsi_data)
    macd_json = json.dumps(macd_data)
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{symbol} - RD-Agent 分析</title>
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #1a1a1a; color: #d1d4dc; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        .title {{ font-size: 24px; font-weight: bold; }}
        .stats {{ display: flex; gap: 20px; }}
        .stat {{ background: #2a2e39; padding: 10px 20px; border-radius: 8px; }}
        .stat-value {{ font-size: 18px; font-weight: bold; color: #fff; }}
        .stat-label {{ font-size: 12px; color: #787b86; }}
        .container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }}
        .chart-box {{ background: #2a2e39; border-radius: 12px; padding: 16px; }}
        .chart-title {{ font-size: 14px; margin-bottom: 10px; color: #787b86; }}
        .chart {{ width: 100%; height: 300px; }}
        .buy {{ color: #26a69a; }}
        .sell {{ color: #ef5350; }}
        .hold {{ color: #ff9800; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #363a45; }}
        th {{ color: #787b86; font-weight: normal; }}
        .signal-buy {{ color: #26a69a; }}
        .signal-sell {{ color: #ef5350; }}
        .signal-hold {{ color: #ff9800; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">RD-Agent {symbol} 分析</div>
        <div class="stats">
            <div class="stat">
                <div class="stat-value">${price:.2f}</div>
                <div class="stat-label">当前价格</div>
            </div>
            <div class="stat">
                <div class="stat-value">{change:+.2f}%</div>
                <div class="stat-label">涨跌幅</div>
            </div>
            <div class="stat">
                <div class="stat-value">{rsi:.1f}</div>
                <div class="stat-label">RSI</div>
            </div>
            <div class="stat">
                <div class="stat-value signal-{signal_class}">{signal}</div>
                <div class="stat-label">信号</div>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="chart-box">
            <div class="chart-title">K线 + 均线</div>
            <div id="candle-chart" class="chart"></div>
        </div>
        <div class="chart-box">
            <div class="chart-title">成交量</div>
            <div id="volume-chart" class="chart"></div>
        </div>
        <div class="chart-box">
            <div class="chart-title">RSI</div>
            <div id="rsi-chart" class="chart"></div>
        </div>
        <div class="chart-box">
            <div class="chart-title">MACD</div>
            <div id="macd-chart" class="chart"></div>
        </div>
    </div>
    
    <h3>因子信号</h3>
    <table>
        <tr>
            <th>因子</th>
            <th>当前值</th>
            <th>信号</th>
            <th>说明</th>
        </tr>
        {factor_table}
    </table>

    <script>
        // 数据
        const candleData = {candle_json};
        const volumeData = {volume_json};
        const rsiData = {rsi_json};
        const macdData = {macd_json};
        
        // 颜色配置
        const layout = {{
            background: {{ type: 'solid', color: '#2a2e39' }},
            textColor: '#d1d4dc',
        }};
        
        const candleColors = {{
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderUpColor: '#26a69a',
            borderDownColor: '#ef5350',
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        }};
        
        // K线图
        const candleChart = LightweightCharts.createChart(document.getElementById('candle-chart'), {{ layout, width: document.getElementById('candle-chart').clientWidth, height: 300 }});
        const candleSeries = candleChart.addCandlestickSeries(candleColors);
        candleSeries.setData(candleData);
        
        // 均线
        const ma5Line = candleChart.addLineSeries({{ color: '#2196F3', lineWidth: 1, priceLineVisible: false }});
        ma5Line.setData(candleData.map(d => ({{ time: d.time, value: d.ma5 }})));
        
        const ma20Line = candleChart.addLineSeries({{ color: '#FF9800', lineWidth: 1, priceLineVisible: false }});
        ma20Line.setData(candleData.map(d => ({{ time: d.time, value: d.ma20 }})));
        
        // 成交量图
        const volumeChart = LightweightCharts.createChart(document.getElementById('volume-chart'), {{ layout, width: document.getElementById('volume-chart').clientWidth, height: 300 }});
        const volumeSeries = volumeChart.addHistogramSeries({{ color: '#26a69a', priceFormat: {{ type: 'volume' }} }});
        volumeSeries.setData(volumeData);
        
        // RSI图
        const rsiChart = LightweightCharts.createChart(document.getElementById('rsi-chart'), {{ layout, width: document.getElementById('rsi-chart').clientWidth, height: 300 }});
        const rsiSeries = rsiChart.addLineSeries({{ color: '#9C27B0', lineWidth: 2 }});
        rsiSeries.setData(rsiData);
        
        // 添加 RSI 基准线
        rsiChart.addLineSeries({{ color: '#ef5350', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed }}).setData(rsiData.map(d => ({{ time: d.time, value: 70 }})));
        rsiChart.addLineSeries({{ color: '#26a69a', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed }}).setData(rsiData.map(d => ({{ time: d.time, value: 30 }})));
        
        // MACD图
        const macdChart = LightweightCharts.createChart(document.getElementById('macd-chart'), {{ layout, width: document.getElementById('macd-chart').clientWidth, height: 300 }});
        
        const macdLine = macdChart.addHistogramSeries({{ color: '#2196F3' }});
        macdLine.setData(macdData.map(d => ({{ time: d.time, value: d.macd, color: d.macd >= 0 ? '#26a69a' : '#ef5350' }})));
        
        const signalLine = macdChart.addLineSeries({{ color: '#FF9800', lineWidth: 1 }});
        signalLine.setData(macdData.map(d => ({{ time: d.time, value: d.signal }})));
        
        // 响应式调整
        window.addEventListener('resize', () => {{
            candleChart.resize(document.getElementById('candle-chart').clientWidth, 300);
            volumeChart.resize(document.getElementById('volume-chart').clientWidth, 300);
            rsiChart.resize(document.getElementById('rsi-chart').clientWidth, 300);
            macdChart.resize(document.getElementById('macd-chart').clientWidth, 300);
        }});
    </script>
</body>
</html>'''
    
    # 保存
    output_path = f"/tmp/rd_agent_{symbol}.html"
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"✅ 图表已生成: {output_path}")
    return output_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='RD-Agent 图表生成')
    parser.add_argument('--symbol', '-s', default='NVDA', help='股票代码')
    args = parser.parse_args()
    
    path = generate_chart(args.symbol)
    print(f"\n📂 打开图表: open {path}")
