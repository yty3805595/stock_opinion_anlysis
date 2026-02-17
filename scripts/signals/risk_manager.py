#!/usr/bin/env python3
"""
风险管理器 - 实施严格的风险控制
"""

import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class RiskCheckResult:
    """风险检查结果"""
    passed: bool
    risk_level: RiskLevel
    action: str  # "pass", "reduce", "reject"
    reason: str
    adjusted_signal: dict = None


class RiskManager:
    """
    风险管理器
    
    实施以下风控措施：
    1. 仓位控制
    2. 止损机制
    3. 回撤控制
    4. 相关性检查
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {
            "max_single_position": 0.30,  # 单只最大 30%
            "max_sector_position": 0.50,  # 单板块最大 50%
            "stop_loss": 0.05,  # 止损 5%
            "take_profit": 0.10,  # 止盈 10%
            "max_drawdown": 0.10,  # 最大回撤 10%
            "max_portfolio_risk": 0.15,  # 组合最大风险
            "min_liquidity": 1000000  # 最小流动性 (日成交额)
        }
        
        self.current_drawdown = 0.0
        self.peak_value = 100000  # 模拟初始资金
        
    def check_signal(self, signal: dict, portfolio: dict = None) -> RiskCheckResult:
        """
        检查交易信号的风险
        
        Args:
            signal: 交易信号
            portfolio: 当前组合
            
        Returns:
            风险检查结果
        """
        # 1. 检查仓位
        check_result = self._check_position_size(signal)
        if not check_result.passed:
            return check_result
        
        # 2. 检查止损
        check_result = self._check_stop_loss(signal, portfolio)
        if not check_result.passed:
            return check_result
        
        # 3. 检查回撤
        check_result = self._check_drawdown()
        if not check_result.passed:
            return check_result
        
        # 4. 检查流动性
        check_result = self._check_liquidity(signal)
        if not check_result.passed:
            return check_result
        
        # 5. 检查组合风险
        check_result = self._check_portfolio_risk(signal, portfolio)
        if not check_result.passed:
            return check_result
        
        return RiskCheckResult(
            passed=True,
            risk_level=RiskLevel.LOW,
            action="pass",
            reason="所有风控检查通过",
            adjusted_signal=signal
        )
    
    def _check_position_size(self, signal: dict) -> RiskCheckResult:
        """检查仓位大小"""
        max_size = self.config["max_single_position"]
        position_size = signal.get("position_size", 0)
        
        if position_size > max_size:
            # 调整仓位
            adjusted_size = max_size
            adjusted_signal = signal.copy()
            adjusted_signal["position_size"] = adjusted_size
            
            return RiskCheckResult(
                passed=True,
                risk_level=RiskLevel.MEDIUM,
                action="reduce",
                reason=f"仓位 {position_size*100:.1f}% 超过上限 {max_size*100:.1f}%，已调整为 {adjusted_size*100:.1f}%",
                adjusted_signal=adjusted_signal
            )
        
        return RiskCheckResult(
            passed=True,
            risk_level=RiskLevel.LOW,
            action="pass",
            reason="仓位检查通过"
        )
    
    def _check_stop_loss(self, signal: dict, portfolio: dict = None) -> RiskCheckResult:
        """检查止损"""
        # 检查是否触发止损
        if portfolio is None:
            return RiskCheckResult(
                passed=True,
                risk_level=RiskLevel.LOW,
                action="pass",
                reason="无持仓数据，跳过止损检查"
            )
        
        symbol = signal.get("symbol")
        current_price = signal.get("current_price", 0)
        entry_price = portfolio.get("positions", {}).get(symbol, {}).get("entry_price", 0)
        
        if entry_price > 0 and current_price > 0:
            loss_pct = (current_price - entry_price) / entry_price
            
            if loss_pct < -self.config["stop_loss"]:
                return RiskCheckResult(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    action="reject",
                    reason=f"触发止损：亏损 {abs(loss_pct)*100:.1f}%，超过止损线 {self.config['stop_loss']*100:.1f}%",
                    adjusted_signal=None
                )
        
        return RiskCheckResult(
            passed=True,
            risk_level=RiskLevel.LOW,
            action="pass",
            reason="止损检查通过"
        )
    
    def _check_drawdown(self) -> RiskCheckResult:
        """检查回撤"""
        if self.current_drawdown > self.config["max_drawdown"]:
            return RiskCheckResult(
                passed=False,
                risk_level=RiskLevel.EXTREME,
                action="reject",
                reason=f"触发回撤限制：当前回撤 {self.current_drawdown*100:.1f}%，超过上限 {self.config['max_drawdown']*100:.1f}%",
                adjusted_signal=None
            )
        
        return RiskCheckResult(
            passed=True,
            risk_level=RiskLevel.LOW,
            action="pass",
            reason="回撤检查通过"
        )
    
    def _check_liquidity(self, signal: dict) -> RiskCheckResult:
        """检查流动性"""
        # 检查日成交额
        volume = signal.get("volume", 0)
        min_liquidity = self.config["min_liquidity"]
        
        if volume < min_liquidity:
            return RiskCheckResult(
                passed=False,
                risk_level=RiskLevel.MEDIUM,
                action="reject",
                reason=f"流动性不足：日成交额 {volume/1000000:.1f}M < {min_liquidity/1000000:.1f}M",
                adjusted_signal=None
            )
        
        return RiskCheckResult(
            passed=True,
            risk_level=RiskLevel.LOW,
            action="pass",
            reason="流动性检查通过"
        )
    
    def _check_portfolio_risk(self, signal: dict, portfolio: dict = None) -> RiskCheckResult:
        """检查组合整体风险"""
        if portfolio is None:
            return RiskCheckResult(
                passed=True,
                risk_level=RiskLevel.LOW,
                action="pass",
                reason="无组合数据，跳过组合风险检查"
            )
        
        # 计算当前组合风险
        positions = portfolio.get("positions", {})
        
        # 简单风险计算：基于持仓集中度
        total_exposure = sum(
            pos.get("size", 0) for pos in positions.values()
        )
        
        max_risk = self.config["max_portfolio_risk"]
        
        if total_exposure > max_risk:
            return RiskCheckResult(
                passed=False,
                risk_level=RiskLevel.HIGH,
                action="reject",
                reason=f"组合风险过高：当前敞口 {total_exposure*100:.1f}% > {max_risk*100:.1f}%",
                adjusted_signal=None
            )
        
        return RiskCheckResult(
            passed=True,
            risk_level=RiskLevel.LOW,
            action="pass",
            reason="组合风险检查通过"
        )
    
    def update_drawdown(self, current_value: float):
        """更新回撤"""
        if current_value > self.peak_value:
            self.peak_value = current_value
        
        self.current_drawdown = (self.peak_value - current_value) / self.peak_value
    
    def get_risk_report(self, signals: dict, portfolio: dict = None) -> dict:
        """生成风控报告"""
        report = {
            "timestamp": pd.Timestamp.now().isoformat(),
            "checks": [],
            "summary": {
                "total_signals": len(signals),
                "passed": 0,
                "adjusted": 0,
                "rejected": 0
            }
        }
        
        for symbol, signal in signals.items():
            check_result = self.check_signal(signal, portfolio)
            
            report["checks"].append({
                "symbol": symbol,
                "action": check_result.action,
                "reason": check_result.reason,
                "risk_level": check_result.risk_level.value
            })
            
            if check_result.action == "pass":
                report["summary"]["passed"] += 1
            elif check_result.action == "reduce":
                report["summary"]["adjusted"] += 1
            else:
                report["summary"]["rejected"] += 1
        
        return report


# 测试代码
if __name__ == "__main__":
    # 创建风控管理器
    risk_manager = RiskManager()
    
    # 测试信号
    signal = {
        "symbol": "QQQ",
        "position_size": 0.35,  # 超过 30%
        "volume": 50000000,
        "direction": "long"
    }
    
    # 检查信号
    result = risk_manager.check_signal(signal)
    
    print(f"信号: {signal['symbol']}")
    print(f"检查结果: {result.action}")
    print(f"原因: {result.reason}")
    print(f"风险等级: {result.risk_level.value}")
    
    if result.adjusted_signal:
        print(f"调整后仓位: {result.adjusted_signal['position_size']*100:.1f}%")
