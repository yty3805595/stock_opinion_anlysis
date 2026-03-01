#!/usr/bin/env python3
"""
主动策略调整器

功能：
1. 监控市场状态变化
2. 基于 LLM 信号主动调整持仓
3. 自动执行止损止盈
4. 宏观环境自适应
5. 风险控制
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass

# ============ 策略配置 ============
STRATEGY_CONFIGS = {
    "EOF": {
        "bull_market": {"position": 0.8, "risk": 0.10},
        "neutral_market": {"position": 0.5, "risk": 0.05},
        "bear_market": {"position": 0.2, "risk": 0.02}
    },
    "3D": {
        "bull_market": {"position": 0.6, "risk": 0.08},
        "neutral_market": {"position": 0.4, "risk": 0.05},
        "bear_market": {"position": 0.1, "risk": 0.02}
    }
}


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float
    strategy: str
    stop_loss: float = 0.0
    take_profit: float = 0.0


class ActiveStrategyManager:
    """主动策略调整器"""
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.market_regime = "neutral"  # bull, neutral, bear
        self.risk_level = "normal"  # low, normal, high
        self.adjustment_history = []
    
    def analyze_market_regime(self, market_data: Dict) -> str:
        """
        分析市场状态
        
        返回：
        - bull: 牛市，增仓
        - neutral: 中性，持有
        - bear: 熊市，减仓
        """
        trend = market_data.get('trend', 'neutral')
        macro = market_data.get('macro', 'neutral')
        sentiment = market_data.get('sentiment', 50)
        
        # 综合判断
        if trend == 'crash' or macro == 'recession':
            return 'bear'
        elif trend == 'bull' and macro == 'recovery' and sentiment > 70:
            return 'bull'
        else:
            return 'neutral'
    
    def calculate_target_position(self, strategy: str, signal: Dict) -> Dict:
        """
        计算目标仓位
        
        基于：
        1. 市场状态
        2. 信号置信度
        3. 策略风险偏好
        """
        regime = self.market_regime
        config = STRATEGY_CONFIGS.get(strategy, STRATEGY_CONFIGS["EOF"])
        regime_config = config.get(regime, config['neutral_market'])
        
        confidence = signal.get('confidence', 0.5)
        
        # 置信度调整
        confidence_factor = confidence  # 0.5 ~ 1.0
        
        # 风险调整
        risk_factor = 1.0
        if self.risk_level == "high":
            risk_factor = 0.5
        elif self.risk_level == "low":
            risk_factor = 1.2
        
        # 目标仓位
        target_position = regime_config['position'] * confidence_factor * risk_factor
        
        return {
            "strategy": strategy,
            "market_regime": regime,
            "target_position": min(target_position, 1.0),
            "max_risk": regime_config['risk'],
            "confidence_factor": confidence_factor,
            "risk_factor": risk_factor
        }
    
    def check_stop_loss_take_profit(self, position: Position) -> List[Dict]:
        """
        检查止盈止损
        
        返回调整建议
        """
        alerts = []
        
        if position.current_price <= position.stop_loss:
            alerts.append({
                "type": "STOP_LOSS",
                "symbol": position.symbol,
                "current_price": position.current_price,
                "stop_loss": position.stop_loss,
                "loss_pct": (position.current_price - position.avg_cost) / position.avg_cost,
                "action": "SELL_ALL",
                "reason": "触及止损线"
            })
        
        elif position.current_price >= position.take_profit:
            alerts.append({
                "type": "TAKE_PROFIT",
                "symbol": position.symbol,
                "current_price": position.current_price,
                "take_profit": position.take_profit,
                "gain_pct": (position.current_price - position.avg_cost) / position.avg_cost,
                "action": "SELL_HALF",
                "reason": "达到止盈目标"
            })
        
        return alerts
    
    def check_market_adaption(self, market_data: Dict) -> List[Dict]:
        """
        检查市场适应性
        
        是否需要调整策略
        """
        new_regime = self.analyze_market_regime(market_data)
        adaptations = []
        
        if new_regime != self.market_regime:
            adaptations.append({
                "type": "REGIME_CHANGE",
                "from": self.market_regime,
                "to": new_regime,
                "action": self._get_regime_action(new_regime),
                "priority": "HIGH"
            })
            self.market_regime = new_regime
        
        # 检查宏观风险
        if market_data.get('macro') == 'recession':
            self.risk_level = "high"
            adaptations.append({
                "type": "RISK_ALERT",
                "level": "HIGH",
                "action": "降低仓位 50%",
                "priority": "CRITICAL"
            })
        
        return adaptations
    
    def _get_regime_action(self, regime: str) -> str:
        """获取状态调整建议"""
        actions = {
            "bull": "增加仓位至 80%",
            "neutral": "保持 50% 中性仓位",
            "bear": "降低至 20% 防御仓位"
        }
        return actions.get(regime, "保持现状")
    
    def run_active_adjustment(self, market_data: Dict, signals: List[Dict]) -> Dict:
        """
        运行主动策略调整
        
        流程：
        1. 分析市场状态
        2. 检查止盈止损
        3. 评估信号
        4. 生成调整计划
        """
        print("\n" + "=" * 70)
        print("🔄 主动策略调整")
        print("=" * 70)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "market_regime": self.market_regime,
            "adjustments": [],
            "signals_processed": 0,
            "actions": []
        }
        
        # 1. 市场适应性检查
        print("\n📊 1. 市场状态分析...")
        adaptations = self.check_market_adaption(market_data)
        
        for adp in adaptations:
            print(f"   • {adp['type']}: {adp.get('action', 'N/A')}")
            results['adjustments'].append(adp)
        
        # 2. 检查现有持仓
        print("\n💼 2. 持仓检查...")
        position_alerts = []
        
        for symbol, position in self.positions.items():
            alerts = self.check_stop_loss_take_profit(position)
            if alerts:
                position_alerts.extend(alerts)
                print(f"   ⚠️ {symbol}: {alerts[0]['type']}")
        
        results['position_alerts'] = position_alerts
        
        # 3. 处理信号
        print("\n📈 3. 信号处理...")
        signal_results = []
        
        for signal in signals:
            results['signals_processed'] += 1
            
            # 计算目标仓位
            target = self.calculate_target_position(
                signal.get('strategy', 'EOF'),
                signal
            )
            print(f"   • {signal.get('action', 'HOLD')} {signal.get('symbol', '')}: "
                  f"目标仓位 {target['target_position']:.0%}")
            
            signal_results.append({
                "signal": signal,
                "target_position": target
            })
        
        results['signal_results'] = signal_results
        
        # 4. 生成行动
        print("\n📤 4. 生成行动计划...")
        actions = []
        
        # 止盈止损
        for alert in position_alerts:
            actions.append({
                "priority": "CRITICAL",
                "action": alert['action'],
                "symbol": alert['symbol'],
                "reason": alert['reason']
            })
        
        # 状态调整
        for adp in adaptations:
            if adp['type'] == 'REGIME_CHANGE':
                actions.append({
                    "priority": "HIGH",
                    "action": "ADJUST_POSITION",
                    "details": adp['action']
                })
        
        results['actions'] = actions
        
        # 5. 总结
        print("\n📋 5. 调整总结...")
        print(f"   市场状态: {self.market_regime}")
        print(f"   风险等级: {self.risk_level}")
        print(f"   处理信号: {results['signals_processed']}")
        print(f"   需要操作: {len(actions)}")
        
        if actions:
            print("\n   🚨 建议操作:")
            for action in actions[:3]:
                print(f"      {action['priority']}: {action['action']} - {action.get('reason', '')}")
        
        print("\n" + "=" * 70)
        
        return results
    
    def add_position(self, position: Position):
        """添加持仓"""
        self.positions[position.symbol] = position
        print(f"✅ 添加持仓: {position.symbol} x{position.quantity}")
    
    def remove_position(self, symbol: str):
        """移除持仓"""
        if symbol in self.positions:
            del self.positions[symbol]
            print(f"🗑️ 移除持仓: {symbol}")


async def main():
    """测试主动策略调整器"""
    print("=" * 70)
    print("🔄 主动策略调整器测试")
    print("=" * 70)
    
    # 初始化
    manager = ActiveStrategyManager()
    
    # 添加测试持仓
    manager.add_position(Position(
        symbol="QQQ",
        quantity=68,
        avg_cost=600.64,
        current_price=601.92,
        strategy="EOF",
        stop_loss=570.00,
        take_profit=660.00
    ))
    
    manager.add_position(Position(
        symbol="NVDA",
        quantity=54,
        avg_cost=186.94,
        current_price=182.81,
        strategy="EOF",
        stop_loss=177.59,
        take_profit=205.63
    ))
    
    # 市场数据
    market_data = {
        "trend": "bull",
        "macro": "recovery",
        "sentiment": 65,
        "price": 600.00
    }
    
    # LLM 信号
    signals = [
        {
            "strategy": "EOF",
            "action": "HOLD",
            "symbol": "QQQ",
            "confidence": 0.85
        },
        {
            "strategy": "EOF",
            "action": "HOLD",
            "symbol": "NVDA",
            "confidence": 0.70
        }
    ]
    
    # 运行调整
    result = manager.run_active_adjustment(market_data, signals)
    
    # 保存结果
    with open('/tmp/active_adjustment.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("\n✅ 结果已保存: /tmp/active_adjustment.json")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
