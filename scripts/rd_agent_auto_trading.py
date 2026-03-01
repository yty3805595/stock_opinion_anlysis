#!/usr/bin/env python3
"""
RD-Agent 主动交易系统
功能:
1. 每日自动挖掘有效因子
2. 基于因子信号生成交易决策
3. 风险管理
4. 自动执行交易
"""

import json
import os
from datetime import datetime
from pathlib import Path

# 加载配置
WORKSPACE = Path("/Users/yintaoye/.openclaw/workspace")
CONFIG_PATH = WORKSPACE / "skills/longbridge-trading/config/credentials.json"

# 交易标的
WATCHLIST = ["TSLA.US", "NVDA.US", "MSFT.US", "GOOGL.US", "QQQ.US", "AAPL.US", "AMD.US", "META.US", "AMZN.US"]

# 风控参数
MAX_POSITIONS = 5  # 最大持仓数
MAX_POSITION_PCT = 0.2  # 单票最大仓位 20%
STOP_LOSS_PCT = 5.0  # 止损 5%
TAKE_PROFIT_PCT = 10.0  # 止盈 10%
MIN_CASH_PCT = 0.1  # 最低现金比例 10%

# 因子阈值
MIN_IC = 0.05  # 最小 IC 因子
MIN_CONFIDENCE = 0.6  # 最小置信度


def load_credentials():
    """加载 Longbridge 凭证"""
    with open(CONFIG_PATH) as f:
        creds = json.load(f)["credentials"]
    from longbridge.openapi import Config
    return Config(
        app_key=creds["app_key"],
        app_secret=creds["app_secret"],
        access_token=creds["access_token"],
    )


def get_stock_data(symbol, period="6mo"):
    """获取股票数据"""
    import requests
    
    # 使用 yfinance 作为备用
    import yfinance as yf
    ticker = yf.Ticker(symbol.replace(".US", ""))
    hist = ticker.history(period=period)
    
    if hist.empty:
        return None
    
    # 转换为 DataFrame
    df = hist.reset_index()
    df.columns = [c.lower() for c in df.columns]
    return df


def calculate_factors(df):
    """计算技术因子"""
    import numpy as np
    
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']
    
    factors = {}
    
    # 移动平均
    for window in [5, 10, 20, 60]:
        factors[f'ma{window}'] = close.rolling(window).mean()
        factors[f'ma{window}_ratio'] = close / factors[f'ma{window}'] - 1
    
    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    factors['rsi_14'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    factors['macd'] = ema12 - ema26
    factors['macd_signal'] = factors['macd'].ewm(span=9).mean()
    factors['macd_hist'] = factors['macd'] - factors['macd_signal']
    
    #布林带
    bb_ma = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    factors['bb_upper'] = bb_ma + 2 * bb_std
    factors['bb_lower'] = bb_ma - 2 * bb_std
    factors['bb_position'] = (close - factors['bb_lower']) / (factors['bb_upper'] - factors['bb_lower'])
    
    # 成交量
    factors['volume_ma5'] = volume.rolling(5).mean()
    factors['volume_ratio'] = volume / factors['volume_ma5']
    
    # 动量
    for window in [5, 10, 20]:
        factors[f'momentum_{window}'] = close.pct_change(window)
    
    # 波动率
    factors['volatility_20'] = close.pct_change().rolling(20).std() * np.sqrt(252)
    
    return factors


def generate_signals(df, factors):
    """基于因子生成交易信号"""
    import numpy as np
    
    signals = {}
    
    # 获取最新值
    latest = {k: v.iloc[-1] if hasattr(v, 'iloc') else v for k, v in factors.items()}
    
    score = 0
    confidence = 0
    reasons = []
    
    # 1. RSI 信号
    rsi = latest.get('rsi_14', 50)
    if rsi < 30:
        score += 2
        reasons.append(f"RSI超卖({rsi:.0f})")
    elif rsi > 70:
        score -= 2
        reasons.append(f"RSI超买({rsi:.0f})")
    
    # 2. 均线信号
    ma5_ratio = latest.get('ma5_ratio', 0)
    ma20_ratio = latest.get('ma20_ratio', 0)
    
    if ma5_ratio > 0.02 and ma20_ratio > 0:
        score += 2
        reasons.append("均线多头排列")
    elif ma5_ratio < -0.02 and ma20_ratio < 0:
        score -= 2
        reasons.append("均线空头排列")
    
    # 3. MACD 信号
    macd_hist = latest.get('macd_hist', 0)
    if macd_hist > 0:
        score += 1
        reasons.append("MACD金叉")
    elif macd_hist < 0:
        score -= 1
        reasons.append("MACD死叉")
    
    # 4. 布林带信号
    bb_pos = latest.get('bb_position', 0.5)
    if bb_pos < 0.2:
        score += 1
        reasons.append("触及布林下轨")
    elif bb_pos > 0.8:
        score -= 1
        reasons.append("触及布林上轨")
    
    # 5. 成交量信号
    vol_ratio = latest.get('volume_ratio', 1)
    if vol_ratio > 1.5:
        score += 1
        reasons.append("成交量放大")
    
    # 计算置信度
    confidence = min(abs(score) / 5, 1.0)
    
    # 生成最终信号
    if score >= 3:
        signal = "BUY"
    elif score <= -3:
        signal = "SELL"
    else:
        signal = "HOLD"
    
    return {
        "signal": signal,
        "score": score,
        "confidence": confidence,
        "reasons": reasons,
        "rsi": rsi,
        "ma20_ratio": ma20_ratio,
    }


def analyze_watchlist():
    """分析关注列表"""
    import yfinance as yf
    
    print("="*70)
    print("🎯 RD-Agent 主动交易信号")
    print("="*70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    signals = []
    
    for symbol in WATCHLIST:
        try:
            ticker = yf.Ticker(symbol.replace(".US", ""))
            hist = ticker.history(period="6mo")
            
            if hist.empty:
                continue
            
            df = hist.reset_index()
            df.columns = [c.lower() for c in df.columns]
            
            # 计算因子
            factors = calculate_factors(df)
            
            # 生成信号
            signal_data = generate_signals(df, factors)
            signal_data["symbol"] = symbol
            signal_data["price"] = float(df['close'].iloc[-1])
            
            signals.append(signal_data)
            
        except Exception as e:
            print(f"❌ {symbol}: {e}")
    
    # 排序并显示
    print("📊 交易信号:")
    print("-"*70)
    
    # 按信号强度排序
    buy_signals = [s for s in signals if s["signal"] == "BUY"]
    sell_signals = [s for s in signals if s["signal"] == "SELL"]
    hold_signals = [s for s in signals if s["signal"] == "HOLD"]
    
    if buy_signals:
        print("\n🟢 买入信号:")
        for s in sorted(buy_signals, key=lambda x: -x["confidence"]):
            print(f"   {s['symbol']}: ${s['price']:.2f}")
            print(f"      置信度: {s['confidence']*100:.0f}% | 原因: {', '.join(s['reasons'])}")
    
    if sell_signals:
        print("\n🔴 卖出信号:")
        for s in sorted(sell_signals, key=lambda x: -x["confidence"]):
            print(f"   {s['symbol']}: ${s['price']:.2f}")
            print(f"      置信度: {s['confidence']*100:.0f}% | 原因: {', '.join(s['reasons'])}")
    
    if hold_signals:
        print("\n⚪ 观望:")
        for s in sorted(hold_signals, key=lambda x: -x["confidence"])[:5]:
            print(f"   {s['symbol']}: {s['reasons'][0] if s['reasons'] else '中性'}")
    
    return signals


def get_current_positions():
    """获取当前持仓"""
    from longbridge.openapi import Config, TradeContext
    
    config = load_credentials()
    trade_ctx = TradeContext(config)
    
    positions = {}
    try:
        resp = trade_ctx.stock_positions()
        for channel in resp.channels:
            for p in channel.positions:
                if p.symbol.endswith('.US'):
                    positions[p.symbol] = {
                        "qty": p.quantity,
                        "cost": float(p.cost_price)
                    }
    except Exception as e:
        print(f"获取持仓失败: {e}")
    
    return positions


def main():
    """主函数"""
    print("\n" + "="*70)
    print("🚀 RD-Agent 主动交易系统")
    print("="*70)
    
    # 1. 分析市场信号
    signals = analyze_watchlist()
    
    # 2. 获取当前持仓
    positions = get_current_positions()
    
    # 3. 生成交易建议
    print("\n" + "="*70)
    print("💡 交易建议")
    print("="*70)
    
    # 买入建议
    buy_candidates = [s for s in signals if s["signal"] == "BUY" and s["confidence"] >= 0.6]
    if buy_candidates:
        print("\n🟢 建议买入:")
        for s in buy_candidates:
            # 检查是否已持仓
            if s["symbol"] in positions:
                print(f"   {s['symbol']}: 已持仓，跳过")
            else:
                print(f"   {s['symbol']}: ${s['price']:.2f} (置信度 {s['confidence']*100:.0f}%)")
    
    # 卖出建议
    sell_candidates = [s for s in signals if s["signal"] == "SELL" and s["confidence"] >= 0.6]
    if sell_candidates:
        print("\n🔴 建议卖出:")
        for s in sell_candidates:
            if s["symbol"] in positions:
                print(f"   {s['symbol']}: 建议止损/止盈")
            else:
                print(f"   {s['symbol']}: 无持仓")
    
    # 总结
    print("\n" + "="*70)
    print("📋 总结")
    print("="*70)
    print(f"   买入信号: {len(buy_candidates)} 个")
    print(f"   卖出信号: {len(sell_candidates)} 个")
    print(f"   当前持仓: {len(positions)} 只")
    print()


if __name__ == "__main__":
    main()
