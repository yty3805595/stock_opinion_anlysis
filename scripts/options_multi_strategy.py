#!/usr/bin/env python3
"""
RD-Agent 多策略期权分析器
提供多种期权策略选择
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent))


# ============ 策略定义 ============
class OptionStrategies:
    """期权策略"""
    
    STRATEGIES = {
        "protective_put": {
            "name": "保护性看跌",
            "emoji": "🛡️",
            "description": "持有股票 + 买入看跌期权保护下行",
            "when": "任何持仓都可以使用",
            "cost": "权利金",
            "max_loss": "股票下跌 - 权利金",
            "profit": "无限 (股票上涨)"
        },
        "collar": {
            "name": "领口策略",
            "emoji": "🎯",
            "description": "买入看跌 + 卖出看涨，锁定收益",
            "when": "有大幅盈利需要保护时",
            "cost": "净权利金 (可能为0或收入)",
            "max_loss": "股票下跌 - (行权价差 - 收入)",
            "profit": "股票上涨 - 行权价差 + 收入"
        },
        "cash_secured_put": {
            "name": "现金担保看跌",
            "emoji": "💰",
            "description": "卖出看跌期权，收权利金并准备买入",
            "when": "想以更低价格买入股票",
            "cost": "需要现金保证金",
            "max_loss": "股票跌到0 - 收到的权利金",
            "profit": "收到的权利金 (如果未被行权)"
        },
        "bull_call_spread": {
            "name": "牛市看涨价差",
            "emoji": "🐂",
            "description": "买入低行权价看涨 + 卖出高行权价看涨",
            "when": "温和看涨时",
            "cost": "净权利金",
            "max_loss": "支付的权利金",
            "profit": "行权价差 - 支付的权利金"
        },
        "bottom_fish": {
            "name": "抄底期权",
            "emoji": "🎣",
            "description": "买入看跌期权博反弹 (实际上是看涨)",
            "when": "RSI超卖 + 支撑位",
            "cost": "权利金 (可能100%损失)",
            "profit": "股票反弹 - 权利金"
        }
    }


def get_option_params(symbol: str) -> Dict:
    """获取期权参数"""
    params = {
        "QQQ": {"strike_multiplier": 5, "min_premium": 15, "contract_size": 100},
        "NVDA": {"strike_multiplier": 5, "min_premium": 10, "contract_size": 100},
        "AMD": {"strike_multiplier": 2.5, "min_premium": 5, "contract_size": 100},
        "PLTR": {"strike_multiplier": 2.5, "min_premium": 3, "contract_size": 100},
        "TSLA": {"strike_multiplier": 10, "min_premium": 10, "contract_size": 100},
        "MSFT": {"strike_multiplier": 5, "min_premium": 10, "contract_size": 100},
        "GOOGL": {"strike_multiplier": 5, "min_premium": 10, "contract_size": 100},
        "AAPL": {"strike_multiplier": 2.5, "min_premium": 5, "contract_size": 100},
        "META": {"strike_multiplier": 10, "min_premium": 15, "contract_size": 100},
        "AMZN": {"strike_multiplier": 5, "min_premium": 10, "contract_size": 100},
    }
    return params.get(symbol, params["QQQ"])


def analyze_market_condition(price: float, ma20: float, rsi: float, 
                            volatility: float, pnl_pct: float) -> Dict:
    """分析市场状况"""
    # 趋势
    if price > ma20 * 1.02:
        trend = "bullish"
    elif price < ma20 * 0.98:
        trend = "bearish"
    else:
        trend = "neutral"
    
    # 动量
    if rsi > 70:
        momentum = "overbought"
    elif rsi < 30:
        momentum = "oversold"
    else:
        momentum = "neutral"
    
    # 波动率
    if volatility > 0.4:
        vol_regime = "high"
    elif volatility < 0.2:
        vol_regime = "low"
    else:
        vol_regime = "normal"
    
    # 持仓状况
    if pnl_pct > 10:
        position_status = "profit_high"
    elif pnl_pct > 3:
        position_status = "profit_medium"
    elif pnl_pct > 0:
        position_status = "profit_low"
    elif pnl_pct > -3:
        position_status = "loss_low"
    elif pnl_pct > -10:
        position_status = "loss_medium"
    else:
        position_status = "loss_high"
    
    return {
        "trend": trend,
        "momentum": momentum,
        "volatility": vol_regime,
        "position_status": position_status
    }


def recommend_strategies(symbol: str, price: float, ma20: float, 
                        rsi: float, volatility: float, 
                        pnl_pct: float, holding_value: float) -> List[Dict]:
    """推荐策略"""
    
    condition = analyze_market_condition(price, ma20, rsi, volatility, pnl_pct)
    params = get_option_params(symbol)
    
    strategies = []
    
    # 策略1: 保护性看跌 (适合所有情况)
    strategies.append({
        "strategy": "protective_put",
        "name": "🛡️ 保护性看跌",
        "strike": round(price * 0.95 / params["strike_multiplier"]) * params["strike_multiplier"],
        "expiry_days": 30,
        "premium": round(params["min_premium"] + price * 0.02, 2),
        "cost": round((params["min_premium"] + price * 0.02) * params["contract_size"], 2),
        "reason": "保护下行风险，持有股票时必备",
        "suitability": "⭐⭐⭐⭐⭐"
    })
    
    # 策略2: 领口策略 (大幅盈利时)
    if condition["position_status"].startswith("profit"):
        call_strike = round(price * 1.05 / params["strike_multiplier"]) * params["strike_multiplier"]
        put_strike = round(price * 0.95 / params["strike_multiplier"]) * params["strike_multiplier"]
        
        call_premium = params["min_premium"] + price * 0.025
        put_premium = params["min_premium"] + price * 0.02
        net_credit = round((call_premium - put_premium) * params["contract_size"], 2)
        
        strategies.append({
            "strategy": "collar",
            "name": "🎯 领口策略",
            "strike_call": call_strike,
            "strike_put": put_strike,
            "expiry_days": 30,
            "net_credit": net_credit,
            "reason": f"锁定 {pnl_pct:.1f}% 盈利，减少仓位",
            "suitability": "⭐⭐⭐⭐⭐"
        })
    
    # 策略3: 抄底期权 (RSI超卖)
    if condition["momentum"] == "oversold":
        strategies.append({
            "strategy": "bottom_fish",
            "name": "🎣 抄底期权",
            "strike": round(price * 0.90 / params["strike_multiplier"]) * params["strike_multiplier"],
            "expiry_days": 60,
            "premium": round(params["min_premium"] + price * 0.03, 2),
            "cost": round((params["min_premium"] + price * 0.03) * params["contract_size"], 2),
            "reason": "RSI超卖，博反弹",
            "suitability": "⭐⭐⭐"
        })
    
    # 策略4: 现金担保看跌 (震荡或看跌)
    if condition["trend"] in ["neutral", "bearish"]:
        strategies.append({
            "strategy": "cash_secured_put",
            "name": "💰 现金担保看跌",
            "strike": round(price * 0.92 / params["strike_multiplier"]) * params["strike_multiplier"],
            "expiry_days": 30,
            "premium": round(params["min_premium"] + price * 0.02, 2),
            "credit": round((params["min_premium"] + price * 0.02) * params["contract_size"], 2),
            "margin_required": round(price * params["strike_multiplier"] * 0.1, 0),
            "reason": "以更低价格买入或赚取权利金",
            "suitability": "⭐⭐⭐⭐"
        })
    
    # 策略5: 牛市价差 (温和看涨)
    if condition["trend"] == "bullish":
        strategies.append({
            "strategy": "bull_call_spread",
            "name": "🐂 牛市看涨价差",
            "strike_low": round(price * 0.98 / params["strike_multiplier"]) * params["strike_multiplier"],
            "strike_high": round(price * 1.03 / params["strike_multiplier"]) * params["strike_multiplier"],
            "expiry_days": 30,
            "debit": round((params["min_premium"] * 2) * params["contract_size"], 2),
            "reason": "温和看涨，限制风险",
            "suitability": "⭐⭐⭐⭐"
        })
    
    return strategies


def print_analysis(portfolio: Dict):
    """打印分析"""
    print("="*70)
    print("📊 RD-AGENT 多策略期权分析")
    print("="*70)
    print(f"\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # 打印持仓
    print("\n💼 你的持仓")
    print("-"*70)
    
    total_value = 0
    total_pnl = 0
    
    for symbol, pos in portfolio["positions"].items():
        emoji = "🟢" if pos["pnl"] >= 0 else "🔴"
        print(f"  {symbol}: {pos['quantity']:.1f}股 @ ${pos['cost_price']:.0f} = ${pos['market_value']:,.0f} {emoji} ${pos['pnl']:,.0f} ({pos['pnl_pct']:+.1f}%)")
        total_value += pos["market_value"]
        total_pnl += pos["pnl"]
    
    print("-"*70)
    print(f"  总市值: ${total_value:,.0f}")
    print(f"  总盈亏: ${total_pnl:,.0f}")
    
    # 策略分析
    print(f"\n" + "="*70)
    print("🎯 期权策略推荐")
    print("="*70)
    
    all_strategies = []
    
    for symbol, pos in portfolio["positions"].items():
        price = pos["current_price"]
        ma20 = price * 1.01
        rsi = 50 if abs(pos["pnl_pct"]) < 3 else (35 if pos["pnl_pct"] < -3 else 65 if pos["pnl_pct"] > 3 else 50)
        volatility = 0.35
        
        strategies = recommend_strategies(
            symbol, price, ma20, rsi, volatility,
            pos["pnl_pct"], pos["market_value"]
        )
        
        if strategies:
            print(f"\n{'📈' if pos['pnl'] >= 0 else '📉'} {symbol} (${price:.2f}, {pos['pnl_pct']:+.1f}%)")
            print("-"*70)
            
            for i, s in enumerate(strategies, 1):
                print(f"\n  {i}. {s['name']}")
                print(f"     策略: {s['strategy']}")
                print(f"     适合: {s['reason']}")
                
                if "strike" in s:
                    print(f"     行权价: ${s['strike']:.0f}")
                if "strike_call" in s:
                    print(f"     Call行权: ${s['strike_call']:.0f} | Put行权: ${s['strike_put']:.0f}")
                if "strike_low" in s:
                    print(f"     低行权: ${s['strike_low']:.0f} | 高行权: ${s['strike_high']:.0f}")
                
                print(f"     到期: {s['expiry_days']}天后")
                
                if "cost" in s:
                    print(f"     成本: ${s['cost']:,}")
                if "net_credit" in s:
                    print(f"     净收入: ${s['net_credit']:,}")
                if "credit" in s:
                    print(f"     收入: ${s['credit']:,}")
                if "debit" in s:
                    print(f"     成本: ${s['debit']:,}")
                
                print(f"     评分: {s['suitability']}")
    
    # 推荐总结
    print(f"\n" + "="*70)
    print("🏆 最佳策略推荐")
    print("="*70)
    
    recommendations = [
        {
            "strategy": "protective_put",
            "name": "🛡️ 保护性看跌",
            "desc": "为每只持仓购买看跌期权保护",
            "priority": "最高",
            "when": "任何时候"
        },
        {
            "strategy": "collar",
            "name": "🎯 领口策略",
            "desc": "大幅盈利时，锁定收益",
            "priority": "盈利 > 10% 时",
            "when": "有可观盈利时"
        },
        {
            "strategy": "cash_secured_put",
            "name": "💰 现金担保看跌",
            "desc": "想以更低价格买入",
            "priority": "震荡市场",
            "when": "中性或看跌"
        },
        {
            "strategy": "bottom_fish",
            "name": "🎣 抄底期权",
            "desc": "RSI超卖时博反弹",
            "priority": "RSI < 30",
            "when": "超卖时"
        }
    ]
    
    for r in recommendations:
        print(f"\n  {r['name']}")
        print(f"     {r['desc']}")
        print(f"     优先级: {r['priority']}")
        print(f"     时机: {r['when']}")
    
    print("\n" + "="*70)


def main():
    """主函数"""
    # 读取长桥数据
    with open("/tmp/longbridge_portfolio.json") as f:
        portfolio = json.load(f)
    
    print_analysis(portfolio)


if __name__ == "__main__":
    main()
