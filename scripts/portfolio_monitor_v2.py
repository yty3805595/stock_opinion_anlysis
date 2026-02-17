#!/usr/bin/env python3
"""
持仓管理系统
- 定时监控持仓
- 自动止盈止损
- 推送通知
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))


class PortfolioManager:
    """持仓管理器"""
    
    def __init__(self):
        self.stock_portfolio_file = "data/portfolio.json"
        self.options_portfolio_file = "data/options_portfolio.json"
        
        # 止盈止损规则
        self.rules = {
            "stock": {
                "stop_loss": -0.05,   # 止损 5%
                "take_profit": 0.10,   # 止盈 10%
                "trailing_stop": 0.03   # 追踪止损 3%
            },
            "options": {
                "stop_loss": 0.50,     # 期权止损 50%
                "take_profit": 0.30,    # 期权止盈 30%
            }
        }
    
    def load_portfolios(self) -> Dict:
        """加载所有持仓"""
        portfolios = {
            "stocks": {},
            "options": {}
        }
        
        # 加载股票
        if Path(self.stock_portfolio_file).exists():
            with open(self.stock_portfolio_file) as f:
                data = json.load(f)
                portfolios["stocks"] = data.get("positions", {})
        
        # 加载期权
        if Path(self.options_portfolio_file).exists():
            with open(self.options_portfolio_file) as f:
                data = json.load(f)
                portfolios["options"] = data.get("positions", {})
        
        return portfolios
    
    def save_portfolios(self, portfolios: Dict):
        """保存所有持仓"""
        # 保存股票
        with open(self.stock_portfolio_file, "w") as f:
            json.dump({
                "positions": portfolios["stocks"],
                "last_update": datetime.now().isoformat()
            }, f, indent=2)
        
        # 保存期权
        with open(self.options_portfolio_file, "w") as f:
            json.dump({
                "positions": portfolios["options"],
                "last_update": datetime.now().isoformat()
            }, f, indent=2)
    
    def check_stock_alerts(self, portfolios: Dict) -> List[str]:
        """检查股票止盈止损"""
        alerts = []
        
        for symbol, pos in portfolios["stocks"].items():
            pnl_pct = pos.get("pnl_pct", 0)
            
            # 检查止损
            if pnl_pct <= self.rules["stock"]["stop_loss"]:
                alerts.append(f"🔴 {symbol} 触发止损: {pnl_pct:.1f}%")
            
            # 检查止盈
            elif pnl_pct >= self.rules["stock"]["take_profit"]:
                alerts.append(f"🟢 {symbol} 触发止盈: {pnl_pct:.1f}%")
            
            # 检查追踪止损
            elif "highest_price" in pos and pos["highest_price"] > 0:
                current_price = pos.get("current_price", pos.get("avg_price", 0))
                high = pos["highest_price"]
                drawdown = (high - current_price) / high
                if drawdown >= self.rules["stock"]["trailing_stop"]:
                    alerts.append(f"🔴 {symbol} 触发追踪止损: 回落 {drawdown:.1f}%")
        
        return alerts
    
    def check_options_alerts(self, portfolios: Dict) -> List[str]:
        """检查期权止盈止损"""
        alerts = []
        
        for code, pos in portfolios["options"].items():
            return_pct = pos.get("return_pct", 0)
            stop_loss = pos.get("stop_loss", 0)
            take_profit = pos.get("take_profit", 0)
            
            # 止损: 损失达到 50%
            if return_pct <= -self.rules["options"]["stop_loss"]:
                alerts.append(f"🔴 {code} 期权止损: {return_pct:.1f}%")
            
            # 止盈: 盈利达到 30%
            elif return_pct >= self.rules["options"]["take_profit"]:
                alerts.append(f"🟢 {code} 期权止盈: {return_pct:.1f}%")
            
            # 即将到期检查
            expiry = datetime.strptime(pos.get("expiration", ""), "%Y-%m-%d")
            days_left = (expiry - datetime.now()).days
            if days_left <= 7:
                alerts.append(f"⚠️ {code} 即将到期: 剩{days_left}天")
            
            # 损失接近止损线
            if return_pct < 0 and abs(return_pct) >= stop_loss * 0.8:
                alerts.append(f"⚠️ {code} 接近止损: {return_pct:.1f}% / -{stop_loss*100:.0f}%")
        
        return alerts
    
    def generate_report(self) -> str:
        """生成持仓报告"""
        portfolios = self.load_portfolios()
        
        report = []
        report.append("="*70)
        report.append("📊 持仓管理报告")
        report.append("="*70)
        report.append(f"\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # 股票
        report.append("\n💼 股票持仓:")
        report.append("-"*70)
        
        total_stock_value = 0
        total_stock_pnl = 0
        
        for symbol, pos in portfolios["stocks"].items():
            value = pos.get("market_value", 0)
            pnl = pos.get("pnl", 0)
            pnl_pct = pos.get("pnl_pct", 0)
            
            emoji = "🟢" if pnl >= 0 else "🔴"
            
            report.append(f"\n  {symbol}: {pos.get('quantity', 0):.1f}股")
            report.append(f"     市值: ${value:,.2f}")
            report.append(f"     盈亏: {emoji} ${pnl:,.2f} ({pnl_pct:+.1f}%)")
            
            total_stock_value += value
            total_stock_pnl += pnl
        
        # 期权
        report.append("\n\n📈 期权持仓:")
        report.append("-"*70)
        
        total_option_value = 0
        total_option_pnl = 0
        
        for code, pos in portfolios["options"].items():
            value = pos.get("market_value", 0)
            pnl = pos.get("unrealized_pnl", 0)
            return_pct = pos.get("return_pct", 0)
            
            emoji = "🟢" if pnl >= 0 else "🔴"
            
            report.append(f"\n  {code}")
            report.append(f"     标的: {pos.get('symbol', '')}")
            report.append(f"     行权价: ${pos.get('strike_price', 0)}")
            report.append(f"     到期: {pos.get('expiration', '')}")
            report.append(f"     市值: ${value:,.2f}")
            report.append(f"     盈亏: {emoji} ${pnl:,.2f} ({return_pct:+.1f}%)")
            report.append(f"     止损: ${pos.get('stop_loss', 0):.2f}")
            report.append(f"     止盈: ${pos.get('take_profit', 0):.2f}")
            
            total_option_value += value
            total_option_pnl += pnl
        
        # 汇总
        report.append("\n\n📈 汇总:")
        report.append("="*70)
        report.append(f"\n  股票: ${total_stock_value:,.2f} | 盈亏: ${total_stock_pnl:,.2f}")
        report.append(f"  期权: ${total_option_value:,.2f} | 盈亏: ${total_option_pnl:,.2f}")
        report.append(f"\n  总计: ${total_stock_value + total_option_value:,.2f}")
        report.append(f"        ${total_stock_pnl + total_option_pnl:,.2f}")
        
        # 检查警报
        stock_alerts = self.check_stock_alerts(portfolios)
        option_alerts = self.check_options_alerts(portfolios)
        all_alerts = stock_alerts + option_alerts
        
        if all_alerts:
            report.append("\n\n⚠️ 警报:")
            report.append("-"*70)
            for alert in all_alerts:
                report.append(f"\n  {alert}")
        
        report.append("\n" + "="*70)
        
        return "\n".join(report)
    
    def run(self):
        """运行检查"""
        print(self.generate_report())


def main():
    """主函数"""
    manager = PortfolioManager()
    manager.run()


if __name__ == "__main__":
    main()
