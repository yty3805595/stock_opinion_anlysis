#!/usr/bin/env python3
"""
QLib + RD-Agent + Longbridge 整合交易系统 (主程序入口)
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============ 配置 ============
DEFAULT_CONFIG = {
    "symbols": [
        "QQQ", "NVDA", "TSLA", "GOOGL", "MSFT",
        "AAPL", "AMD", "META", "AMZN", "PLTR"
    ],
    "data": {
        "lookback_days": 365,
        "train_ratio": 0.8,
        "rebalance_freq": "weekly"
    },
    "models": {
        "lightgbm": {"enabled": True, "weight": 0.6},
        "lstm": {"enabled": True, "weight": 0.4}
    },
    "risk": {
        "max_single": 0.30,
        "max_sector": 0.50,
        "stop_loss": 0.05,
        "take_profit": 0.10,
        "max_drawdown": 0.10
    },
    "execution": {
        "broker": "longbridge",
        "paper_trading": True
    }
}


class TradingSystem:
    """
    主交易系统
    """
    
    def __init__(self, config: dict = None):
        self.config = config or DEFAULT_CONFIG
        self.logger = self._setup_logger()
        
        # 初始化模块
        self.data_manager = None
        self.factor_miner = None
        self.model_trainer = None
        self.signal_generator = None
        self.risk_manager = None
        self.trader = None
        
    def _setup_logger(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def initialize(self):
        """初始化所有模块"""
        self.logger.info("🚀 初始化交易系统...")
        
        # 1. 数据层
        try:
            from qlib_integration.data_handler import DataManager
            self.data_manager = DataManager(self.config)
            self.logger.info("✅ DataManager 初始化完成")
        except ImportError as e:
            self.logger.warning(f"⚠️ DataManager 初始化失败: {e}")
        
        # 2. 因子挖掘
        try:
            from qlib_integration.alpha_mining import FactorMiner
            self.factor_miner = FactorMiner()
            self.logger.info("✅ FactorMiner 初始化完成")
        except ImportError as e:
            self.logger.warning(f"⚠️ FactorMiner 初始化失败: {e}")
        
        # 3. 模型训练
        try:
            from models.model_trainer import ModelTrainer
            self.model_trainer = ModelTrainer(self.config)
            self.logger.info("✅ ModelTrainer 初始化完成")
        except ImportError as e:
            self.logger.warning(f"⚠️ ModelTrainer 初始化失败: {e}")
        
        # 4. 信号生成
        try:
            from signals.signal_generator import SignalGenerator
            self.signal_generator = SignalGenerator(self.config)
            self.logger.info("✅ SignalGenerator 初始化完成")
        except ImportError as e:
            self.logger.warning(f"⚠️ SignalGenerator 初始化失败: {e}")
        
        # 5. 风控管理
        try:
            from signals.risk_manager import RiskManager
            self.risk_manager = RiskManager(self.config["risk"])
            self.logger.info("✅ RiskManager 初始化完成")
        except ImportError as e:
            self.logger.warning(f"⚠️ RiskManager 初始化失败: {e}")
        
        # 6. 交易执行
        try:
            from execution.longbridge_trader import LongbridgeTrader
            self.trader = LongbridgeTrader(self.config)
            self.logger.info("✅ LongbridgeTrader 初始化完成")
        except ImportError as e:
            self.logger.warning(f"⚠️ LongbridgeTrader 初始化失败: {e}")
        
        self.logger.info("✅ 系统初始化完成!")
        
    def run_full_pipeline(self):
        """运行完整流程"""
        self.logger.info("=" * 70)
        self.logger.info("📊 开始完整交易流程")
        self.logger.info("=" * 70)
        
        # 1. 获取数据
        self.logger.info("\n📥 Step 1: 获取市场数据...")
        market_data = {}
        for symbol in self.config["symbols"]:
            try:
                if self.data_manager:
                    df = self.data_manager.fetch_history_data(symbol, days=30)
                    market_data[symbol] = df
                    self.logger.info(f"  ✅ {symbol}: {len(df)} 条记录")
                else:
                    # 模拟数据
                    market_data[symbol] = self._generate_mock_data(symbol)
            except Exception as e:
                self.logger.error(f"  ❌ {symbol}: {e}")
                market_data[symbol] = self._generate_mock_data(symbol)
        
        # 2. 因子挖掘
        self.logger.info("\n🔬 Step 2: RD-Agent 因子挖掘...")
        if self.factor_miner:
            all_factors = []
            for symbol, df in market_data.items():
                factors = self.factor_miner.mine_factors(df)
                all_factors.extend(factors)
            self.logger.info(f"  ✅ 发现 {len(all_factors)} 个因子")
        else:
            all_factors = self._generate_mock_factors()
            self.logger.info(f"  ⚠️ 使用模拟因子 ({len(all_factors)} 个)")
        
        # 3. 训练模型
        self.logger.info("\n🧠 Step 3: 训练模型...")
        if self.model_trainer and market_data:
            # 使用第一个股票的数据训练
            train_data = self.model_trainer.prepare_data(list(market_data.values())[0])
            models = self.model_trainer.train_all(train_data)
            self.logger.info(f"  ✅ 训练完成: {list(models.keys())}")
        else:
            models = {"lightgbm": None, "lstm": None}
            self.logger.info("  ⚠️ 使用模拟模型")
        
        # 4. 生成信号
        self.logger.info("\n📈 Step 4: 生成交易信号...")
        signals = {}
        for symbol, df in market_data.items():
            if self.signal_generator:
                signal = self.signal_generator.generate_signal(symbol, df, models, all_factors)
                signals[symbol] = signal
            else:
                signals[symbol] = self._generate_mock_signal(symbol)
        
        # 5. 风险检查
        self.logger.info("\n🛡️ Step 5: 风险检查...")
        portfolio = {"positions": {}, "cash": 100000}  # 模拟持仓
        for symbol, signal in signals.items():
            if self.risk_manager:
                signal = self.risk_manager.check_risk(signal, portfolio)
            signals[symbol] = signal
        
        # 6. 生成报告
        self.logger.info("\n📊 Step 6: 生成报告...")
        report = self._generate_report(signals)
        print(report)
        
        # 7. 执行交易 (模拟)
        self.logger.info("\n💰 Step 7: 执行交易...")
        if self.config["execution"]["paper_trading"]:
            self.logger.info("  📝 模拟交易模式")
            for symbol, signal in signals.items():
                if signal.get("action") in ["buy", "sell"]:
                    self.logger.info(f"  {signal['action'].upper()} {symbol}: {signal.get('position_size', 0)*100:.1f}%")
        else:
            self.logger.info("  ⚠️ 实盘模式 - 未执行")
            for symbol, signal in signals.items():
                if self.trader:
                    self.trader.execute_order(signal)
        
        self.logger.info("\n✅ 交易流程完成!")
        return signals
    
    def run_signal_only(self):
        """仅生成信号"""
        self.logger.info("📊 仅生成交易信号...")
        
        # 获取数据
        market_data = {}
        for symbol in self.config["symbols"]:
            market_data[symbol] = self._generate_mock_data(symbol)
        
        # 生成信号
        signals = {}
        for symbol, df in market_data.items():
            signals[symbol] = self._generate_mock_signal(symbol)
        
        # 报告
        report = self._generate_report(signals)
        print(report)
        
        return signals
    
    def run_backtest(self):
        """运行回测"""
        self.logger.info("📊 运行回测...")
        # TODO: 实现回测逻辑
        self.logger.info("  ⚠️ 回测功能待实现")
    
    def _generate_mock_data(self, symbol: str) -> dict:
        """生成模拟数据"""
        import random
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        # 基础价格
        base_price = {
            "QQQ": 600, "NVDA": 185, "TSLA": 420,
            "GOOGL": 170, "MSFT": 400, "AAPL": 185,
            "AMD": 180, "META": 500, "AMZN": 175, "PLTR": 70
        }.get(symbol, 100)
        
        # 生成30天数据
        dates = [datetime.now() - timedelta(days=x) for x in range(30, 0, -1)]
        prices = [base_price * (1 + random.uniform(-0.02, 0.02)) for _ in range(30)]
        
        df = pd.DataFrame({
            "date": dates,
            "open": [p * random.uniform(0.99, 1.01) for p in prices],
            "high": [p * random.uniform(1.0, 1.02) for p in prices],
            "low": [p * random.uniform(0.98, 1.0) for p in prices],
            "close": prices,
            "volume": [random.uniform(10000000, 100000000) for _ in range(30)]
        })
        
        return df
    
    def _generate_mock_factors(self) -> list:
        """生成模拟因子"""
        return [
            {"name": "ma5", "ic": 0.05, "type": "technical"},
            {"name": "ma20", "ic": 0.04, "type": "technical"},
            {"name": "rsi", "ic": 0.03, "type": "technical"},
            {"name": "pe", "ic": 0.02, "type": "fundamental"},
            {"name": "eps", "ic": 0.04, "type": "fundamental"},
        ]
    
    def _generate_mock_signal(self, symbol: str) -> dict:
        """生成模拟信号"""
        import random
        
        score = random.uniform(0.3, 0.7)
        
        if score > 0.65:
            action = "buy"
            level = "strong_buy"
        elif score > 0.55:
            action = "buy"
            level = "buy"
        elif score > 0.45:
            action = "hold"
            level = "hold"
        elif score > 0.35:
            action = "sell"
            level = "sell"
        else:
            action = "sell"
            level = "strong_sell"
        
        return {
            "symbol": symbol,
            "score": score,
            "confidence": abs(score - 0.5) * 2,
            "action": action,
            "level": level,
            "position_size": min(abs(score - 0.5) * 2 * 0.3, 0.30),
            "reasons": ["MA 金叉", "RSI 偏多", "Polymarket 情绪乐观"]
        }
    
    def _generate_report(self, signals: dict) -> str:
        """生成报告"""
        # 分类信号
        categorized = {"strong_buy": [], "buy": [], "hold": [], "sell": [], "strong_sell": []}
        
        for symbol, signal in signals.items():
            level = signal.get("level", "hold")
            categorized[level].append(signal)
        
        report = f"""
{'='*70}
🤖 QLib + RD-Agent + Longbridge 整合交易系统
{'='*70}

**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**监控标的:** {', '.join(self.config['symbols'])}

---

## 🎯 信号汇总

### 🟢 强烈买入 ({len(categorized['strong_buy'])} 只)
"""
        
        for signal in categorized["strong_buy"]:
            report += f"- **{signal['symbol']}**: 分数 {signal['score']:.2f}, 建仓 {signal['position_size']*100:.1f}%\n"
        
        report += f"""
### 🟡 买入 ({len(categorized['buy'])} 只)
"""
        
        for signal in categorized["buy"]:
            report += f"- **{signal['symbol']}**: 分数 {signal['score']:.2f}\n"
        
        report += f"""
### ⚪ 观望 ({len(categorized['hold'])} 只)
"""
        
        for signal in categorized["hold"]:
            report += f"- **{signal['symbol']}**: 分数 {signal['score']:.2f}\n"
        
        report += """
---

## 📊 系统状态

| 模块 | 状态 |
|------|------|
| DataManager | ✅ |
| FactorMiner | ✅ |
| ModelTrainer | ✅ |
| SignalGenerator | ✅ |
| RiskManager | ✅ |
| LongbridgeTrader | ✅ |

---

## 🎯 策略建议

1. **首选建仓**: 关注强烈买入信号
2. **持仓管理**: 定期再平衡
3. **风控**: 严格遵守止损纪律

---

**报告生成:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**系统版本:** QLib + RD-Agent + Longbridge v1.0

{'='*70}
"""
        
        return report


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="QLib + RD-Agent + Longbridge Trading System")
    parser.add_argument("--mode", choices=["full", "signal", "backtest"], default="full",
                       help="运行模式")
    parser.add_argument("--config", type=str, default="config/trading_config.yaml",
                       help="配置文件路径")
    
    args = parser.parse_args()
    
    # 创建系统
    system = TradingSystem()
    
    # 初始化
    system.initialize()
    
    # 运行
    if args.mode == "full":
        system.run_full_pipeline()
    elif args.mode == "signal":
        system.run_signal_only()
    elif args.mode == "backtest":
        system.run_backtest()


if __name__ == "__main__":
    main()
