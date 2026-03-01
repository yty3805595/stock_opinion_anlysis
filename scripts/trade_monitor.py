#!/usr/bin/env python3
"""
交易记录与监控系统
用户下单后记录，并进行监控
"""

import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

class PositionStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"

class TradeLogger:
    """交易记录器"""
    
    def __init__(self, filename: str = "trades.json"):
        self.filename = filename
        self.trades = self.load_trades()
    
    def load_trades(self) -> List[Dict]:
        """加载交易记录"""
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                return json.load(f)
        return []
    
    def save_trades(self):
        """保存交易记录"""
        with open(self.filename, 'w') as f:
            json.dump(self.trades, f, ensure_ascii=False, indent=2)
    
    def add_trade(self, 
                  symbol: str,
                  direction: str,  # "buy" or "sell"
                  entry_price: float,
                  size: int,
                  strategy: str,
                  stop_loss: float = None,
                  take_profit: float = None,
                  notes: str = ""
                  ) -> Dict:
        """
        添加新交易
        
        Args:
            symbol: 股票代码 (e.g., "MSTR", "QQQ", "600519.SH")
            direction: "buy" or "sell"
            entry_price: 买入价格
            size: 数量
            strategy: 策略名称
            stop_loss: 止损价
            take_profit: 止盈价
            notes: 备注
        """
        trade = {
            "id": f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{symbol}",
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "size": size,
            "strategy": strategy,
            "entry_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "notes": notes,
            "status": PositionStatus.OPEN.value,
            "exit_price": None,
            "exit_time": None,
            "pnl": None,
            "pnl_percent": None
        }
        
        self.trades.append(trade)
        self.save_trades()
        
        return trade
    
    def close_trade(self, 
                    symbol: str, 
                    exit_price: float,
                    reason: str = "manual"
                    ) -> Optional[Dict]:
        """
        平仓
        
        Args:
            symbol: 股票代码
            exit_price: 平仓价格
            reason: 平仓原因
        """
        for trade in self.trades:
            if trade['symbol'] == symbol and trade['status'] == PositionStatus.OPEN.value:
                trade['exit_price'] = exit_price
                trade['exit_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                trade['exit_reason'] = reason
                trade['status'] = PositionStatus.CLOSED.value
                
                # 计算盈亏
                if trade['direction'] == 'buy':
                    trade['pnl'] = (exit_price - trade['entry_price']) * trade['size']
                    trade['pnl_percent'] = (exit_price - trade['entry_price']) / trade['entry_price'] * 100
                else:
                    trade['pnl'] = (trade['entry_price'] - exit_price) * trade['size']
                    trade['pnl_percent'] = (trade['entry_price'] - exit_price) / trade['entry_price'] * 100
                
                self.save_trades()
                return trade
        
        return None
    
    def get_open_positions(self) -> List[Dict]:
        """获取未平仓仓位"""
        return [t for t in self.trades if t['status'] == PositionStatus.OPEN.value]
    
    def get_closed_trades(self) -> List[Dict]:
        """获取已平仓交易"""
        return [t for t in self.trades if t['status'] == PositionStatus.CLOSED.value]
    
    def get_pnl_summary(self) -> Dict:
        """获取盈亏汇总"""
        closed = self.get_closed_trades()
        
        total_pnl = sum(t['pnl'] for t in closed) if closed else 0
        win_trades = [t for t in closed if t['pnl'] > 0]
        loss_trades = [t for t in closed if t['pnl'] <= 0]
        
        win_rate = len(win_trades) / len(closed) * 100 if closed else 0
        
        return {
            "total_trades": len(closed),
            "open_positions": len(self.get_open_positions()),
            "total_pnl": total_pnl,
            "win_trades": len(win_trades),
            "loss_trades": len(loss_trades),
            "win_rate": win_rate
        }
    
    def print_status(self):
        """打印当前状态"""
        print("\n" + "=" * 80)
        print("📊 交易状态")
        print("=" * 80)
        
        # 未平仓
        open_positions = self.get_open_positions()
        if open_positions:
            print(f"\n🟢 未平仓 ({len(open_positions)} 只)")
            print("-" * 80)
            print(f"{'代码':<12} {'方向':<6} {'买入价':<10} {'数量':<8} {'止损':<10} {'止盈':<10}")
            print("-" * 80)
            for t in open_positions:
                print(f"{t['symbol']:<12} {t['direction']:<6} ${t['entry_price']:<9.2f} {t['size']:<8} ${t['stop_loss']:<9.2f} ${t['take_profit']:<9.2f}")
        
        # 汇总
        summary = self.get_pnl_summary()
        print("\n📈 汇总统计")
        print("-" * 80)
        print(f"  总交易: {summary['total_trades']}")
        print(f"  未平仓: {summary['open_positions']}")
        print(f"  盈利: {summary['win_trades']}")
        print(f"  亏损: {summary['loss_trades']}")
        print(f"  胜率: {summary['win_rate']:.1f}%")
        print(f"  总盈亏: ${summary['total_pnl']:.2f}")
        
        print("\n" + "=" * 80)


class PositionMonitor:
    """仓位监控器"""
    
    def __init__(self, logger: TradeLogger):
        self.logger = logger
    
    def check_alerts(self, prices: Dict[str, float]) -> List[str]:
        """
        检查是否触发警报
        
        Args:
            prices: {股票代码: 当前价格}
        
        Returns:
            警报列表
        """
        alerts = []
        
        for position in self.logger.get_open_positions():
            symbol = position['symbol']
            
            if symbol not in prices:
                continue
            
            current_price = prices[symbol]
            
            # 止损警报
            if position['stop_loss'] and current_price <= position['stop_loss']:
                if position['direction'] == 'buy':
                    alerts.append(f"🚨 {symbol} 触发止损! 当前价: ${current_price:.2f}, 止损价: ${position['stop_loss']:.2f}")
            
            # 止盈警报
            if position['take_profit'] and current_price >= position['take_profit']:
                if position['direction'] == 'buy':
                    alerts.append(f"🎯 {symbol} 触及止盈! 当前价: ${current_price:.2f}, 止盈价: ${position['take_profit']:.2f}")
        
        return alerts
    
    def print_alerts(self, prices: Dict[str, float]):
        """打印警报"""
        alerts = self.check_alerts(prices)
        
        if alerts:
            print("\n" + "=" * 80)
            print("🚨 警报!")
            print("=" * 80)
            for alert in alerts:
                print(f"  {alert}")
            print("=" * 80)
        else:
            print("\n✅ 无警报")


def main():
    """测试"""
    logger = TradeLogger("trades.json")
    
    # 模拟添加交易
    print("\n📝 添加测试交易...")
    
    # 示例：用户下单 MSTR
    trade = logger.add_trade(
        symbol="MSTR",
        direction="buy",
        entry_price=120.50,
        size=100,
        strategy="MSTR趋势",
        stop_loss=108.45,  # -10%
        take_profit=132.55,  # +10%
        notes="用户确认下单"
    )
    print(f"✅ 已添加: {trade['symbol']} @ ${trade['entry_price']}")
    
    # 示例：用户下单 QQQ
    trade = logger.add_trade(
        symbol="QQQ",
        direction="buy",
        entry_price=600.64,
        size=68,
        strategy="EOF核心",
        stop_loss=540.58,  # -10%
        take_profit=660.70,  # +10%
        notes="用户确认下单"
    )
    print(f"✅ 已添加: {trade['symbol']} @ ${trade['entry_price']}")
    
    # 打印状态
    logger.print_status()
    
    # 模拟监控
    print("\n🔍 模拟价格检查...")
    monitor = PositionMonitor(logger)
    
    # 假设价格
    prices = {
        "MSTR": 115.00,  # 接近止损
        "QQQ": 605.00     # 盈利中
    }
    
    monitor.print_alerts(prices)


if __name__ == "__main__":
    main()
