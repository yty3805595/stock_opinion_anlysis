# 🤖 QLib + RD-Agent + Longbridge 整合交易系统

**创建时间**: 2026-02-17  
**版本**: v1.0

---

## 🎯 系统概述

端到端 AI 量化交易系统，整合：
- **QLib**: 微软开源量化投资平台
- **RD-Agent**: AI Agent 自动因子挖掘和模型优化
- **Longbridge**: 专业美股交易 API

---

## 📁 文件结构

```
scripts/
├── main_trading_system.py      # 主程序入口
├── qlib_integration/
│   ├── __init__.py
│   ├── data_handler.py         # 数据管理器
│   └── alpha_mining.py         # RD-Agent 因子挖掘
├── models/
│   ├── __init__.py
│   └── model_trainer.py       # 模型训练器
├── signals/
│   ├── __init__.py
│   ├── signal_generator.py     # 信号生成器
│   └── risk_manager.py         # 风险管理器
└── execution/
    ├── __init__.py
    └── longbridge_trader.py    # 长桥交易执行
```

---

## 🚀 快速开始

### 1. 运行完整流程

```bash
python scripts/main_trading_system.py --mode full
```

### 2. 仅生成信号

```bash
python scripts/main_trading_system.py --mode signal
```

### 3. 运行回测

```bash
python scripts/main_trading_system.py --mode backtest
```

---

## 📊 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                  Data Layer (数据层)                    │
├─────────────────────────────────────────────────────────┤
│  Longbridge API → 数据获取 → 特征工程 → QLib Format    │
│  ├── 实时行情                                          │
│  ├── 历史K线                                          │
│  └── 基本面数据                                       │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                Strategy Layer (策略层)                   │
├─────────────────────────────────────────────────────────┤
│  RD-Agent                    QLib Models              │
│  ├── 因子自动挖掘             ├── LightGBM             │
│  ├── 假设验证               ├── XGBoost               │
│  └── 模型优化               └── 组合优化               │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                 Signal Layer (信号层)                    │
├─────────────────────────────────────────────────────────┤
│  信号生成器              风险管理器                      │
│  ├── 模型预测分数         ├── 仓位控制                 │
│  ├── 因子打分            ├── 止损机制                 │
│  └── 情绪分析           └── 回撤控制                 │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│               Execution Layer (执行层)                  │
├─────────────────────────────────────────────────────────┤
│  Longbridge Trader                                    │
│  ├── 订单执行              成交确认                   │
│  ├── 资金管理              持仓同步                   │
│  └── 错误处理              日志记录                   │
└─────────────────────────────────────────────────────────┘
```

---

## 📈 核心模块

### 1. 数据管理器 (DataManager)

```python
from qlib_integration.data_handler import DataManager

manager = DataManager({
    "symbols": ["QQQ", "NVDA", "TSLA"]
})

# 获取K线数据
df = manager.get_klines("QQQ", period="365d")

# 创建特征
features = manager.create_features(df)
```

**功能**:
- 获取长桥实时行情
- 获取历史K线数据
- 特征工程 (MA, RSI, MACD, Bollinger等)

### 2. 因子挖掘器 (FactorMiner)

```python
from qlib_integration.alpha_mining import FactorMiner

miner = FactorMiner()
factors = miner.mine_factors(df)

# 获取最佳因子
top_factors = miner.get_top_factors(20)
```

**功能**:
- 技术因子挖掘
- 基本面因子挖掘
- 因子有效性评估 (IC, IR)
- 自动生成 Alpha 表达式

### 3. 模型训练器 (ModelTrainer)

```python
from models.model_trainer import ModelTrainer

trainer = ModelTrainer()
X, y, cols = trainer.prepare_data(df)
models = trainer.train_all(df)
```

**支持的模型**:
- LightGBM
- XGBoost
- LSTM (待实现)
- 集成预测

### 4. 信号生成器 (SignalGenerator)

```python
from signals.signal_generator import SignalGenerator

generator = SignalGenerator()
signal = generator.generate_signal("QQQ", df, models, factors)
```

**信号评分公式**:
```
综合分数 = 模型预测(50%) + 因子打分(30%) + 情绪分析(20%)
```

### 5. 风险管理器 (RiskManager)

```python
from signals.risk_manager import RiskManager

risk_manager = RiskManager()
result = risk_manager.check_signal(signal, portfolio)
```

**风控规则**:
- 单只最大仓位: 30%
- 单板块最大: 50%
- 止损线: 5%
- 最大回撤: 10%
- 最小流动性: 100万日成交

### 6. 长桥交易执行器 (LongbridgeTrader)

```python
from execution.longbridge_trader import LongbridgeTrader

trader = LongbridgeTrader()
result = trader.execute_signal(signal)
```

**功能**:
- 模拟交易模式
- 实盘交易 (需要 API Key)
- 订单管理
- 持仓同步

---

## ⚙️ 配置

编辑 `scripts/main_trading_system.py`:

```python
DEFAULT_CONFIG = {
    "symbols": [
        "QQQ", "NVDA", "TSLA", "GOOGL", "MSFT",
        "AAPL", "AMD", "META", "AMZN", "PLTR"
    ],
    
    "data": {
        "lookback_days": 365,
        "train_ratio": 0.8
    },
    
    "models": {
        "lightgbm": {"enabled": True, "weight": 0.6},
        "xgboost": {"enabled": True, "weight": 0.3}
    },
    
    "risk": {
        "max_single": 0.30,
        "stop_loss": 0.05,
        "max_drawdown": 0.10
    },
    
    "execution": {
        "broker": "longbridge",
        "paper_trading": True  # 设为 False 则实盘交易
    }
}
```

---

## 📊 信号等级

| 分数 | 等级 | 操作 |
|------|------|------|
| > 0.65 | 🟢 强烈买入 | 建仓/加仓 |
| 0.55-0.65 | 🟡 买入 | 小仓位买入 |
| 0.45-0.55 | ⚪ 观望 | 持有不动 |
| 0.35-0.45 | 🟠 卖出 | 减仓 |
| < 0.35 | 🔴 强烈卖出 | 清仓 |

---

## 🎯 下一步计划

### Phase 1: 基础功能 ✅ 已完成
- [x] 系统架构设计
- [x] 核心模块代码
- [x] 模拟数据支持
- [x] 完整交易流程

### Phase 2: 数据接入 (进行中)
- [ ] 长桥 API 对接
- [ ] Polymarket API 接入
- [ ] Tavily 新闻搜索
- [ ] 真实数据测试

### Phase 3: 模型升级
- [ ] 训练 LSTM/Transformer 模型
- [ ] 集成 RD-Agent 因子挖掘
- [ ] 模型自动优化
- [ ] 回测框架

### Phase 4: 实盘交易
- [ ] 长桥 API 实盘对接
- [ ] 资金管理
- [ ] 订单管理系统
- [ ] 绩效归因

---

## 💡 使用建议

1. **先用模拟模式测试**
   ```python
   "paper_trading": True
   ```

2. **观察信号质量**
   - 记录每次信号
   - 验证信号准确性
   - 优化因子和模型

3. **逐步实盘**
   - 先用小资金
   - 验证执行效率
   - 再加大资金

4. **持续优化**
   - 定期重新训练模型
   - 更新因子库
   - 调整风控参数

---

## ⚠️ 风险提示

1. **模拟 vs 实盘**
   - 模拟结果不代表实盘表现
   - 真实市场有滑点和成交限制

2. **模型局限**
   - 历史数据不代表未来
   - 市场结构可能变化

3. **风控第一**
   - 严格遵守止损纪律
   - 控制单只仓位

---

## 📚 参考资料

- **QLib**: https://github.com/microsoft/qlib
- **RD-Agent**: https://github.com/microsoft/RD-Agent
- **长桥**: https://longbridge.global/

---

*由 ProActive Agent 自动生成*
*基于 QLib + RD-Agent + Longbridge 整合架构*
