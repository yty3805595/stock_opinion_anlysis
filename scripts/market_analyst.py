#!/usr/bin/env python3
"""
市场分析师 Agent
功能:
1. 获取市场数据 (VIX, 国债, 黄金, 比特币)
2. 分析市场情绪和热点
3. 生成交易机会报告

网络问题: 目前外部新闻网站受限，优先使用市场数据分析
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# 工作目录
WORKSPACE = Path("/Users/yintaoye/.openclaw/workspace")


def fetch_news_simple() -> List[Dict]:
    """简单获取新闻方式"""
    news = []
    
    # 方式1: 使用 yfinance 获取个股新闻
    try:
        import yfinance as yf
        
        # 获取热点股票的新闻
        tickers = ["NVDA", "TSLA", "AAPL", "MSFT", "GOOGL", "META", "AMD", "AMZN"]
        for sym in tickers:
            try:
                ticker = yf.Ticker(sym)
                # 尝试获取新闻
                if hasattr(ticker, 'news') and ticker.news:
                    for n in ticker.news[:2]:
                        news.append({
                            "source": "Yahoo",
                            "title": n.get('title', '')[:100],
                            "symbol": sym,
                            "timestamp": datetime.now().isoformat()
                        })
            except:
                pass
    except Exception as e:
        print(f"获取新闻失败: {e}")
    
    # 如果 yfinance 没新闻，添加默认分析
    if not news:
        news.append({
            "source": "Analysis",
            "title": "市场观望，等待财报季",
            "symbol": "ALL",
            "timestamp": datetime.now().isoformat()
        })
    
    return news


def get_market_data() -> Dict:
    """获取市场数据"""
    import yfinance as yf
    
    data = {}
    
    # 主要指数
    indices = {
        "SPY": "S&P 500",
        "QQQ": "Nasdaq 100", 
        "DIA": "Dow Jones",
        "IWM": "Russell 2000"
    }
    
    # 恐慌指数
    vix = yf.Ticker("^VIX")
    try:
        vix_data = vix.history(period="1d")
        if not vix_data.empty:
            data["VIX"] = float(vix_data['Close'].iloc[-1])
    except:
        data["VIX"] = None
    
    # 债券收益率
    try:
        tlt = yf.Ticker("TLT")
        tlt_data = tlt.history(period="1d")
        if not tlt_data.empty:
            data["TLT"] = float(tlt_data['Close'].iloc[-1])
    except:
        data["TLT"] = None
    
    # 黄金
    try:
        gld = yf.Ticker("GLD")
        gld_data = gld.history(period="1d")
        if not gld_data.empty:
            data["GLD"] = float(gld_data['Close'].iloc[-1])
    except:
        data["GLD"] = None
    
    # 比特币
    try:
        btc = yf.Ticker("BTC-USD")
        btc_data = btc.history(period="1d")
        if not btc_data.empty:
            data["BTC"] = float(btc_data['Close'].iloc[-1])
    except:
        data["BTC"] = None
    
    return data


def analyze_sentiment(market_data: Dict) -> Dict:
    """分析市场情绪"""
    sentiment = {
        "market": "neutral",
        "risk_level": "medium",
        "hot_sectors": [],
        "recommendations": []
    }
    
    # VIX 分析
    vix = market_data.get("VIX")
    if vix:
        if vix > 25:
            sentiment["market"] = "fear"
            sentiment["risk_level"] = "high"
            sentiment["recommendations"].append("恐慌指数高，建议降低仓位")
        elif vix < 15:
            sentiment["market"] = "greed"
            sentiment["risk_level"] = "low"
            sentiment["recommendations"].append("恐慌指数低，可适度加仓")
    
    return sentiment


def identify_opportunities(market_data: Dict) -> List[Dict]:
    """识别交易机会"""
    opportunities = []
    
    # 基于市场数据的简单分析
    vix = market_data.get("VIX", 20)
    
    # 1. 恐慌买入机会
    if vix > 25:
        opportunities.append({
            "type": "BUY",
            "name": "恐慌买入",
            "logic": "VIX > 25，市场恐慌，可能是买入机会",
            "tickers": ["QQQ", "SPY"],
            "risk": "medium"
        })
    
    # 2. 避险机会
    if vix > 20:
        opportunities.append({
            "type": "HEDGE",
            "name": "避险配置",
            "logic": "市场波动加大，增加避险配置",
            "tickers": ["GLD", "TLT"],
            "risk": "low"
        })
    
    # 3. 科技股回调机会
    opportunities.append({
        "type": "WATCH",
        "name": "科技股观察",
        "logic": "等待财报季，观望为主",
        "tickers": ["NVDA", "MSFT", "GOOGL"],
        "risk": "medium"
    })
    
    return opportunities


def generate_report():
    """生成分析报告"""
    print("="*70)
    print("📊 市场分析师报告")
    print("="*70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # 获取市场数据
    print("\n📈 正在获取市场数据...")
    market_data = get_market_data()
    
    print("\n" + "-"*70)
    print("🌐 市场指标")
    print("-"*70)
    
    if "VIX" in market_data:
        vix_val = market_data["VIX"]
        vix_status = "🟢" if vix_val < 15 else "🟡" if vix_val < 25 else "🔴"
        print(f"   VIX 恐慌指数: {vix_status} {vix_val:.2f}")
    
    if "TLT" in market_data:
        print(f"   TLT (20年国债): ${market_data['TLT']:.2f}")
    
    if "GLD" in market_data:
        print(f"   GLD (黄金): ${market_data['GLD']:.2f}")
    
    if "BTC" in market_data:
        print(f"   BTC: ${market_data['BTC']:,.0f}")
    
    # 情绪分析
    sentiment = analyze_sentiment(market_data)
    
    print("\n" + "-"*70)
    print("🎭 市场情绪")
    print("-"*70)
    emoji = "🟢" if sentiment["market"] == "greed" else "🟡" if sentiment["market"] == "neutral" else "🔴"
    print(f"   情绪: {emoji} {sentiment['market'].upper()}")
    print(f"   风险等级: {sentiment['risk_level']}")
    
    if sentiment["recommendations"]:
        print("\n   建议:")
        for rec in sentiment["recommendations"]:
            print(f"   - {rec}")
    
    # 交易机会
    opportunities = identify_opportunities(market_data)
    
    print("\n" + "-"*70)
    print("🎯 交易机会")
    print("-"*70)
    
    for opp in opportunities:
        emoji = "🟢" if opp["type"] == "BUY" else "🔴" if opp["type"] == "SELL" else "⚪"
        print(f"\n{emoji} {opp['name']}")
        print(f"   逻辑: {opp['logic']}")
        print(f"   标的: {', '.join(opp['tickers'])}")
        print(f"   风险: {opp['risk']}")
    
    # 总结
    print("\n" + "="*70)
    print("📋 总结")
    print("="*70)
    
    buy_opps = [o for o in opportunities if o["type"] == "BUY"]
    print(f"   买入信号: {len(buy_opps)} 个")
    print(f"   观察标的: {len(opportunities)} 个")
    
    print("\n" + "="*70)
    
    return {
        "market_data": market_data,
        "sentiment": sentiment,
        "opportunities": opportunities
    }


if __name__ == "__main__":
    generate_report()
