#!/usr/bin/env python3
"""
全自动交易系统 - 选股 + 执行 + 监控

功能：
1. 自动扫描市场寻找信号
2. 自动计算分数和风险
3. 符合条件自动执行
4. 自动设置止损止盈
5. 自动监控和调仓
6. 只在关键操作时通知
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import requests
import statistics

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trader_auto.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 风险配置
RISK_CONFIG = {
    'max_position_pct': 0.10,      # 单只最大仓位 10%
    'max_sector_pct': 0.30,        # 单板块最大仓位 30%
    'max_daily_loss': -0.03,       # 日最大亏损 -3%
    'max_portfolio_risk': 0.20,    # 组合最大风险 20%
    'min_score': 70,               # 最小执行分数
    'min_risk_reward': 2.0,         # 最小盈亏比
    'stop_loss': -0.05,             # 止损 -5%
    'take_profit': 0.10,           # 止盈 +10%
}


@dataclass
class TradeSignal:
    """交易信号"""
    symbol: str
    name: str
    score: int
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    risk_reward: float
    strategy: str
    timestamp: str


class AutoTrader:
    """全自动交易系统"""
    
    def __init__(self):
        self.positions = {}  # 当前持仓
        self.daily_pnl = 0.0  # 今日盈亏
        self.trading_paused = False  # 交易暂停标志
        self.last_scan_time = None
        
    def scan_market(self) -> List[TradeSignal]:
        """扫描市场，寻找信号"""
        signals = []
        
        logger.info("🔍 开始扫描市场...")
        
        # 1. A股三维选股
        a_signals = self.scan_a_stock()
        signals.extend(a_signals)
        
        # 2. BTC 信号
        btc_signal = self.scan_btc()
        if btc_signal:
            signals.append(btc_signal)
        
        # 3. 排序（分数高的在前）
        signals.sort(key=lambda x: x.score, reverse=True)
        
        self.last_scan_time = datetime.now()
        logger.info(f"✅ 扫描完成，发现 {len(signals)} 个信号")
        
        return signals
    
    def scan_a_stock(self) -> List[TradeSignal]:
        """A股三维选股扫描"""
        signals = []
        
        try:
            # 获取股票列表
            resp = requests.get(
                "https://push2.eastmoney.com/api/qt/clist/get",
                params={
                    'pn': 1, 'pz': 100, 'po': 1, 'np': 1,
                    'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                    'fid': 'f12', 'fs': 'm:0+t:6',
                    'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152'
                },
                timeout=10
            )
            
            if resp.status_code == 200:
                data = resp.json()
                stocks = data['data']['list']
                
                for stock in stocks[:50]:  # 只分析前 50 只
                    try:
                        signal = self.analyze_stock(stock)
                        if signal and signal.score >= RISK_CONFIG['min_score']:
                            signals.append(signal)
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"❌ A股扫描失败: {e}")
        
        return signals
    
    def analyze_stock(self, stock: Dict) -> Optional[TradeSignal]:
        """分析单只股票"""
        try:
            code = stock.get('f12', '')
            name = stock.get('f14', '')
            price = float(stock.get('f2', 0))
            change = float(stock.get('f3', 0))
            volume = float(stock.get('f6', 0))
            turnover = float(stock.get('f8', 0))
            
            if price <= 0:
                return None
            
            # 计算分数
            score = 0
            reasons = []
            
            # 条件 1：基本面（资金关注）
            if change > 3:
                score += 20
                reasons.append("涨幅>3%")
            elif change > 0:
                score += 10
                reasons.append("上涨")
            
            if turnover > 3:
                score += 15
                reasons.append("换手率>3%")
            
            # 条件 2：技术面（简化版）
            # 假设价格在均线附近
            if change > 0 and change < 5:
                score += 20
                reasons.append("温和上涨")
            
            # 条件 3：结构（简化版）
            if change > 3 and change < 9:
                score += 25
                reasons.append("强势但未涨停")
            
            # 止损止盈
            stop_loss = price * (1 + RISK_CONFIG['stop_loss'])
            take_profit = price * (1 + RISK_CONFIG['take_profit'])
            
            # 仓位计算（基于分数）
            if score >= 90:
                position_pct = 0.15
            elif score >= 80:
                position_pct = 0.10
            elif score >= 70:
                position_pct = 0.05
            else:
                position_pct = 0
            
            # 盈亏比（简化）
            risk_reward = 2.0
            
            return TradeSignal(
                symbol=code,
                name=name,
                score=score,
                entry_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size=position_pct,
                risk_reward=risk_reward,
                strategy="A股三维",
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            
        except Exception as e:
            logger.error(f"❌ 股票分析失败: {e}")
            return None
    
    def scan_btc(self) -> Optional[TradeSignal]:
        """BTC 信号扫描"""
        try:
            # 获取价格
            resp = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={'ids': 'bitcoin', 'vs_currencies': 'usd'},
                timeout=10
            )
            price = resp.json()['bitcoin']['usd']
            
            # 简化的分数计算
            score = 50  # 基础分
            
            if price > 70000:
                score += 20
            if price > 75000:
                score += 20
            
            if score >= RISK_CONFIG['min_score']:
                return TradeSignal(
                    symbol='BTC',
                    name='比特币',
                    score=score,
                    entry_price=price,
                    stop_loss=price * 0.95,
                    take_profit=price * 1.10,
                    position_size=0.10,
                    risk_reward=2.0,
                    strategy='BTC趋势',
                    timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                
        except Exception as e:
            logger.error(f"❌ BTC 扫描失败: {e}")
        
        return None
    
    def check_risk(self, signal: TradeSignal) -> bool:
        """风险检查"""
        # 检查是否暂停交易
        if self.trading_paused:
            logger.warning("⚠️ 交易已暂停")
            return False
        
        # 检查分数
        if signal.score < RISK_CONFIG['min_score']:
            logger.info(f"❌ 分数不足: {signal.score} < {RISK_CONFIG['min_score']}")
            return False
        
        # 检查盈亏比
        if signal.risk_reward < RISK_CONFIG['min_risk_reward']:
            logger.info(f"❌ 盈亏比不足: {signal.risk_reward}")
            return False
        
        # 检查仓位
        if signal.position_size > RISK_CONFIG['max_position_pct']:
            logger.info(f"❌ 仓位超限: {signal.position_size}")
            return False
        
        return True
    
    def execute_trade(self, signal: TradeSignal):
        """执行交易"""
        # 风险检查
        if not self.check_risk(signal):
            logger.info(f"❌ 交易被拒绝: {signal.symbol}")
            return
        
        # 执行交易（记录到日志）
        logger.info(f"""
🤖 自动执行交易
====================
股票: {signal.symbol} {signal.name}
价格: {signal.entry_price}
分数: {signal.score}/100
仓位: {signal.position_size*100:.1f}%
止损: {signal.stop_loss}
止盈: {signal.take_profit}
策略: {signal.strategy}
时间: {signal.timestamp}
====================
""")
        
        # 记录到持仓
        self.positions[signal.symbol] = {
            'name': signal.name,
            'entry_price': signal.entry_price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'size': signal.position_size,
            'strategy': signal.strategy,
            'entry_time': signal.timestamp
        }
        
        # 保存到文件
        self.save_positions()
        
        # 通知用户
        self.notify(f"""
🟢 新建仓: {signal.symbol} {signal.name}
💰 价格: ${signal.entry_price}
📊 分数: {signal.score}
📦 仓位: {signal.position_size*100:.1f}%
🛡️ 止损: ${signal.stop_loss}
🎯 止盈: ${signal.take_profit}
""")
    
    def monitor_positions(self):
        """监控持仓"""
        logger.info("🔔 监控持仓...")
        
        for symbol, pos in list(self.positions.items()):
            try:
                # 获取最新价格
                price = self.get_price(symbol)
                if not price:
                    continue
                
                entry_price = pos['entry_price']
                pnl_pct = (price - entry_price) / entry_price
                
                # 检查止损
                if price <= pos['stop_loss']:
                    logger.info(f"🔴 止损触发: {symbol}")
                    self.close_position(symbol, 'stop_loss')
                
                # 检查止盈
                elif price >= pos['take_profit']:
                    logger.info(f"🟢 止盈触发: {symbol}")
                    self.close_position(symbol, 'take_profit')
                
                # 更新盈亏
                self.daily_pnl += pnl_pct * pos['size']
                
            except Exception as e:
                logger.error(f"❌ 监控失败: {symbol}, {e}")
        
        # 检查日亏损
        if self.daily_pnl <= RISK_CONFIG['max_daily_loss']:
            logger.warning("⚠️ 日亏损达到限制，暂停交易")
            self.trading_paused = True
            self.notify("🔴 日亏损达到 -3%，暂停交易")
    
    def close_position(self, symbol: str, reason: str):
        """平仓"""
        if symbol not in self.positions:
            return
        
        pos = self.positions.pop(symbol)
        self.save_positions()
        
        logger.info(f"""
🔄 平仓: {symbol}
原因: {reason}
收益: {self.daily_pnl:.2%}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
        
        self.notify(f"""
🔴 平仓: {symbol}
原因: {reason}
收益: {self.daily_pnl:.2%}
""")
    
    def get_price(self, symbol: str) -> Optional[float]:
        """获取价格"""
        try:
            if symbol == 'BTC':
                resp = requests.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={'ids': 'bitcoin', 'vs_currencies': 'usd'},
                    timeout=5
                )
                return resp.json()['bitcoin']['usd']
            else:
                # A股
                resp = requests.get(
                    f"https://push2.eastmoney.com/api/qt/stock/get",
                    params={
                        'secid': f"{'1' if symbol.startswith('6') else '0'}.{symbol}",
                        'fields': 'f2'
                    },
                    timeout=5
                )
                return resp.json()['data']['f2']
        except:
            return None
    
    def save_positions(self):
        """保存持仓"""
        with open('positions.json', 'w') as f:
            json.dump({
                'positions': self.positions,
                'daily_pnl': self.daily_pnl,
                'paused': self.trading_paused,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, f, indent=2)
    
    def notify(self, message: str):
        """通知用户（仅关键信息）"""
        # 发送通知（这里可以接入邮件、微信等）
        logger.info(f"📢 通知: {message}")
        
        # 写入通知文件
        with open('notifications.txt', 'a') as f:
            f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")
    
    def run(self):
        """运行自动交易系统"""
        logger.info("🚀 启动自动交易系统")
        
        while True:
            try:
                # 扫描市场
                signals = self.scan_market()
                
                # 执行符合条件的信号
                for signal in signals:
                    if signal.symbol not in self.positions:  # 避免重复买入
                        self.execute_trade(signal)
                
                # 监控持仓
                self.monitor_positions()
                
                # 等待下一轮（5分钟）
                logger.info("💤 等待 5 分钟...")
                time.sleep(300)
                
            except KeyboardInterrupt:
                logger.info("👋 停止自动交易系统")
                break
            except Exception as e:
                logger.error(f"❌ 系统错误: {e}")
                time.sleep(60)  # 错误后等待 1 分钟


def main():
    """主函数"""
    trader = AutoTrader()
    
    # 检查是否只运行一次
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # 单次扫描
        signals = trader.scan_market()
        for signal in signals:
            print(f"""
{signal.symbol} {signal.name}
分数: {signal.score}
价格: {signal.entry_price}
仓位: {signal.position_size*100:.1f}%
止损: {signal.stop_loss}
止盈: {signal.take_profit}
""")
    else:
        # 持续运行
        trader.run()


if __name__ == "__main__":
    main()
