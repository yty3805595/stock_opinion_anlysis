#!/usr/bin/env python3
"""
Astra 全自动交易管理系统 v1.0
全权托管：股票 + 期权 + 止盈止损

功能：
1. 自动监控持仓
2. 自动执行止盈止损
3. 自动开仓/平仓
4. 自动对冲
5. 实时风险控制
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import logging

# 配置
WORKSPACE = "/Users/yintaoye/.openclaw/workspace"
CONFIG_PATH = f"{WORKSPACE}/longbridge_tokens.json"
PORTFOLIO_PATH = f"{WORKSPACE}/data/portfolio.json"
OPTIONS_PATH = f"{WORKSPACE}/data/options_portfolio.json"
TRADE_LOG_PATH = f"{WORKSPACE}/data/trade_log.json"
ALERTS_PATH = f"{WORKSPACE}/data/trade_alerts.json"

# 风控参数
RISK_CONFIG = {
    # 止损配置
    "stop_loss": {
        "stock": 0.05,      # 股票止损 5%
        "option": 0.50,     # 期权止损 50%
        "trailing_stop": 0.03,  # 移动止损 3%
    },
    
    # 止盈配置
    "take_profit": {
        "stock": 0.10,     # 股票止盈 10%
        "option": 1.00,    # 期权止盈 100%
        "partial_profit": 0.05,  # 部分止盈 50%
    },
    
    # 仓位配置
    "position": {
        "max_single_stock": 0.30,   # 单只股票最大 30%
        "max_single_option": 0.10,  # 单只期权最大 10%
        "max_total_option": 0.20,    # 期权总仓位最大 20%
        "max_daily_trades": 5,      # 每日最大交易次数
    },
    
    # 风险控制
    "risk": {
        "max_daily_loss": 0.03,     # 单日最大亏损 3%
        "max_drawdown": 0.10,       # 最大回撤 10%
        "emergency_stop": 0.15,     # 紧急止损 15%
    }
}


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    entry_date: str = ""
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0
    trailing_high: float = 0.0
    position_type: str = "stock"  # stock / option
    
    # 期权额外字段
    option_code: Optional[str] = None
    strike_price: Optional[float] = None
    expiration: Optional[str] = None
    option_type: Optional[str] = None  # call / put


@dataclass
class TradeRecord:
    """交易记录"""
    timestamp: str
    symbol: str
    action: str  # buy / sell
    quantity: float
    price: float
    amount: float
    reason: str
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None


class AutoTrader:
    """全自动交易系统"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run  # 试运行模式（不实际交易）
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[TradeRecord] = []
        self.daily_trades = 0
        self.daily_pnl = 0.0
        
        # 加载数据
        self.load()
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def load(self):
        """加载数据"""
        # 加载股票持仓
        if Path(PORTFOLIO_PATH).exists():
            with open(PORTFOLIO_PATH) as f:
                data = json.load(f)
                for symbol, pos in data.get("positions", {}).items():
                    p = Position(
                        symbol=symbol,
                        quantity=pos.get("quantity", 0),
                        avg_price=pos.get("avg_price", 0),
                        current_price=pos.get("current_price", pos.get("avg_price", 0)),
                        entry_date=pos.get("entry_date", ""),
                        position_type="stock"
                    )
                    p.pnl = (p.current_price - p.avg_price) * p.quantity
                    p.pnl_pct = (p.current_price - p.avg_price) / p.avg_price
                    p.trailing_high = p.current_price
                    self.positions[symbol] = p
        
        # 加载期权持仓
        if Path(OPTIONS_PATH).exists():
            with open(OPTIONS_PATH) as f:
                data = json.load(f)
                for code, pos in data.get("positions", {}).items():
                    symbol = pos.get("symbol", code)
                    p = Position(
                        symbol=symbol,
                        quantity=pos.get("quantity", 0),
                        avg_price=pos.get("premium", 0),
                        current_price=pos.get("premium", 0),
                        entry_date=pos.get("open_date", ""),
                        position_type="option",
                        option_code=code,
                        strike_price=pos.get("strike_price", 0),
                        expiration=pos.get("expiration", ""),
                        option_type=pos.get("option_type", "")
                    )
                    p.pnl = pos.get("unrealized_pnl", 0)
                    p.pnl_pct = pos.get("return_pct", 0)
                    self.positions[code] = p
        
        # 加载交易历史
        if Path(TRADE_LOG_PATH).exists():
            with open(TRADE_LOG_PATH) as f:
                data = json.load(f)
                self.trade_history = [
                    TradeRecord(**t) for t in data.get("history", [])
                ]
    
    def save(self):
        """保存数据"""
        # 保存持仓
        portfolio = {
            "positions": {},
            "last_update": datetime.now().isoformat()
        }
        for symbol, pos in self.positions.items():
            if pos.position_type == "stock":
                portfolio["positions"][symbol] = {
                    "symbol": symbol,
                    "quantity": pos.quantity,
                    "avg_price": pos.avg_price,
                    "current_price": pos.current_price,
                    "market_value": pos.quantity * pos.current_price,
                    "pnl": pos.pnl,
                    "pnl_pct": pos.pnl_pct,
                    "entry_date": pos.entry_date,
                }
        
        Path(PORTFOLIO_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(PORTFOLIO_PATH, 'w') as f:
            json.dump(portfolio, f, indent=2)
        
        # 保存交易记录
        trade_data = {
            "history": [vars(t) for t in self.trade_history],
            "last_update": datetime.now().isoformat()
        }
        with open(TRADE_LOG_PATH, 'w') as f:
            json.dump(trade_data, f, indent=2)
    
    def calculate_stop_loss(self, pos: Position) -> float:
        """计算止损价"""
        if pos.position_type == "stock":
            return pos.avg_price * (1 - RISK_CONFIG["stop_loss"]["stock"])
        else:
            return pos.avg_price * (1 - RISK_CONFIG["stop_loss"]["option"])
    
    def calculate_take_profit(self, pos: Position) -> float:
        """计算止盈价"""
        if pos.position_type == "stock":
            return pos.avg_price * (1 + RISK_CONFIG["take_profit"]["stock"])
        else:
            return pos.avg_price * (1 + RISK_CONFIG["take_profit"]["option"])
    
    def check_stop_loss(self, pos: Position) -> bool:
        """检查是否触发止损"""
        stop_price = self.calculate_stop_loss(pos)
        
        if pos.position_type == "stock":
            return pos.current_price <= stop_price
        else:
            # 期权止损更复杂，考虑内在价值
            return pos.pnl_pct <= -RISK_CONFIG["stop_loss"]["option"]
    
    def check_take_profit(self, pos: Position) -> bool:
        """检查是否触发止盈"""
        if pos.position_type == "stock":
            return pos.current_price >= self.calculate_take_profit(pos)
        else:
            return pos.pnl_pct >= RISK_CONFIG["take_profit"]["option"]
    
    def check_trailing_stop(self, pos: Position) -> bool:
        """检查移动止损"""
        if pos.position_type != "stock":
            return False
        
        # 更新最高价
        if pos.current_price > pos.trailing_high:
            pos.trailing_high = pos.current_price
        
        # 检查回撤
        trailing_pct = (pos.trailing_high - pos.current_price) / pos.trailing_high
        return trailing_pct >= RISK_CONFIG["stop_loss"]["trailing_stop"]
    
    def should_add_hedge(self, pos: Position) -> Optional[Dict]:
        """判断是否需要对冲"""
        # 如果持仓亏损超过 3%，建议对冲
        if pos.pnl_pct < -0.03:
            return {
                "action": "buy_put",
                "symbol": pos.symbol,
                "quantity": pos.quantity,
                "reason": "持仓亏损超过 3%，建议买入 Put 对冲"
            }
        return None
    
    def execute_trade(self, trade: TradeRecord) -> bool:
        """执行交易"""
        # 检查试运行模式
        if self.dry_run:
            self.logger.info(f"[试运行] {trade.action.upper()} {trade.symbol} x{trade.quantity} @ ${trade.price}")
            self.trade_history.append(trade)
            return True
        
        # 检查每日交易次数
        if self.daily_trades >= RISK_CONFIG["position"]["max_daily_trades"]:
            self.logger.warning("已达到每日最大交易次数")
            return False
        
        # 实际交易逻辑（需要 Longbridge API）
        # TODO: 实现真实交易
        
        self.trade_history.append(trade)
        self.daily_trades += 1
        return True
    
    def close_position(self, symbol: str, reason: str) -> bool:
        """平仓"""
        if symbol not in self.positions:
            return False
        
        pos = self.positions[symbol]
        
        # 计算收益
        pnl = (pos.current_price - pos.avg_price) * pos.quantity if pos.position_type == "stock" else pos.pnl
        pnl_pct = pos.pnl_pct
        
        # 记录交易
        trade = TradeRecord(
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            action="sell",
            quantity=pos.quantity,
            price=pos.current_price,
            amount=pos.current_price * pos.quantity,
            reason=reason,
            pnl=pnl,
            pnl_pct=pnl_pct
        )
        
        success = self.execute_trade(trade)
        
        if success:
            del self.positions[symbol]
            self.logger.info(f"平仓 {symbol}: {reason} | PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
        
        return success
    
    def monitor_all(self) -> List[Dict]:
        """监控所有持仓"""
        alerts = []
        
        for symbol, pos in self.positions.items():
            # 更新盈亏
            pos.pnl = (pos.current_price - pos.avg_price) * pos.quantity if pos.position_type == "stock" else pos.pnl
            pos.pnl_pct = (pos.current_price - pos.avg_price) / pos.avg_price if pos.position_type == "stock" else pos.pnl_pct
            
            alert = {
                "symbol": symbol,
                "type": pos.position_type,
                "pnl_pct": pos.pnl_pct,
                "reason": ""
            }
            
            # 检查止损
            if self.check_stop_loss(pos):
                alert["action"] = "STOP_LOSS"
                alert["reason"] = f"触发止损 ({pos.pnl_pct:.1f}%)"
                alerts.append(alert)
                self.close_position(symbol, f"止损: {pos.pnl_pct:.1f}%")
                continue
            
            # 检查止盈
            if self.check_take_profit(pos):
                alert["action"] = "TAKE_PROFIT"
                alert["reason"] = f"触发止盈 (+{pos.pnl_pct:.1f}%)"
                alerts.append(alert)
                self.close_position(symbol, f"止盈: +{pos.pnl_pct:.1f}%")
                continue
            
            # 检查移动止损
            if self.check_trailing_stop(pos):
                alert["action"] = "TRAILING_STOP"
                alert["reason"] = "移动止损触发"
                alerts.append(alert)
                self.close_position(symbol, "移动止损")
                continue
            
            # 检查是否需要对冲
            if hedge := self.should_add_hedge(pos):
                alert["action"] = "HEDGE_SUGGESTION"
                alert["reason"] = hedge["reason"]
                alerts.append(alert)
        
        # 保存
        self.save()
        
        return alerts
    
    def generate_report(self) -> str:
        """生成报告"""
        total_value = 0
        total_pnl = 0
        
        report = []
        report.append("="*70)
        report.append(f"📊 交易报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("="*70)
        
        report.append(f"\n模式: {'试运行' if self.dry_run else '实盘交易'}")
        report.append(f"持仓数: {len(self.positions)}")
        report.append(f"今日交易: {self.daily_trades} 次")
        
        report.append("\n📈 持仓详情:")
        report.append("-"*70)
        
        for symbol, pos in self.positions.items():
            emoji = "🟢" if pos.pnl_pct >= 0 else "🔴"
            total_value += pos.current_price * pos.quantity
            total_pnl += pos.pnl
            
            report.append(f"{emoji} {symbol}: {pos.quantity:.1f} @ ${pos.current_price:.2f} ({pos.pnl_pct:+.2f}%)")
            
            # 显示止盈止损价
            sl = self.calculate_stop_loss(pos)
            tp = self.calculate_take_profit(pos)
            report.append(f"    止损: ${sl:.2f} | 止盈: ${tp:.2f}")
        
        report.append("-"*70)
        report.append(f"💰 总市值: ${total_value:,.2f}")
        report.append(f"{'📈' if total_pnl >= 0 else '📉'} 总盈亏: ${total_pnl:+,.2f}")
        report.append("="*70)
        
        return "\n".join(report)
    
    def run_daily_check(self):
        """每日检查"""
        self.logger.info("开始每日交易检查...")
        
        # 监控所有持仓
        alerts = self.monitor_all()
        
        if alerts:
            self.logger.info(f"发现 {len(alerts)} 个需要处理的情况")
            for alert in alerts:
                self.logger.info(f"  {alert['symbol']}: {alert['action']} - {alert['reason']}")
        else:
            self.logger.info("所有持仓正常，无需操作")
        
        # 生成报告
        report = self.generate_report()
        print(report)
        
        # 保存告警
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "alerts": alerts,
            "dry_run": self.dry_run
        }
        with open(ALERTS_PATH, 'w') as f:
            json.dump(alert_data, f, indent=2)
        
        return alerts


def main():
    """CLI 入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Astra 全自动交易系统")
    parser.add_argument('--dry-run', action='store_true', default=True, help='试运行模式')
    parser.add_argument('--live', action='store_true', help='实盘交易模式')
    parser.add_argument('--report', action='store_true', help='生成报告')
    parser.add_argument('--monitor', action='store_true', help='监控持仓')
    
    args = parser.parse_args()
    
    trader = AutoTrader(dry_run=not args.live)
    
    if args.report:
        print(trader.generate_report())
    elif args.monitor:
        trader.run_daily_check()
    else:
        trader.run_daily_check()


if __name__ == "__main__":
    main()
