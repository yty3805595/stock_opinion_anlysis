# 🤖 QLib + RD-Agent + Longbridge 整合交易系统

**创建时间**: 2026-02-17  
**版本**: v1.0

---

## 🎯 系统愿景

打造一个**端到端的 AI 量化交易系统**，从因子挖掘到模型训练再到实盘执行全自动：

```
数据采集 → 因子挖掘 → 模型训练 → 信号生成 → 风控验证 → 长桥执行
    ↓           ↓           ↓          ↓          ↓         ↓
  Longbridge  RD-Agent   QLib      RD-Agent   风控模块   Longbridge
```

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Trading System Core                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  Data Layer (数据层)                   │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  Longbridge API         QLib DataHandler               │    │
│  │  ├── 实时行情            ├── 特征工程                   │    │
│  │  ├── 历史K线             ├── 因子库                     │    │
│  │  ├── 基本面数据           └── 数据清洗                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           ↓                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                Strategy Layer (策略层)                   │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  RD-Agent                  QLib Models                  │    │
│  │  ├── 因子自动挖掘           ├── LightGBM                │    │
│  │  ├── 假设验证               ├── LSTM/Transformer        │    │
│  │  └── 模型优化               ├── 组合优化                 │    │
│  │                              └── 风险模型               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           ↓                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                 Signal Layer (信号层)                   │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  信号生成器              风险管理器                     │    │
│  │  ├── 多头信号              ├── 仓位控制                 │    │
│  │  ├── 空头信号              ├── 止损机制                 │    │
│  │  └── 仓位建议              └── 回撤控制                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           ↓                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │               Execution Layer (执行层)                   │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  Longbridge Trader                                    │    │
│  │  ├── 订单执行              成交确认                     │    │
│  │  ├── 资金管理              持仓同步                     │    │
│  │  └── 错误处理              日志记录                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 文件结构

```
scripts/
├── qlib_integration/
│   ├── __init__.py
│   ├── data_handler.py         # QLib 数据处理
│   ├── feature_engineering.py   # 特征工程
│   └── alpha_mining.py         # RD-Agent 因子挖掘
│
├── models/
│   ├── __init__.py
│   ├── lightgbm_model.py       # LightGBM 选股模型
│   ├── lstm_predictor.py       # LSTM 价格预测
│   └── ensemble.py             # 模型集成
│
├── signals/
│   ├── __init__.py
│   ├── signal_generator.py     # 信号生成器
│   └── risk_manager.py         # 风险管理器
│
├── execution/
│   ├── __init__.py
│   ├── longbridge_trader.py    # 长桥交易执行
│   └── order_manager.py        # 订单管理
│
└── main_trading_system.py      # 主程序入口
```

---

## 🔧 核心模块设计

### 1. 数据层：Longbridge + QLib

```python
class DataManager:
    """
    数据管理器
    整合长桥行情和 QLib 特征工程
    """
    
    def __init__(self, config):
        self.config = config
        self.longbridge = LongbridgeClient()
        self.qlib_handler = QLibDataHandler()
        
    def fetch_realtime_data(self, symbol: str) -> Dict:
        """获取实时行情"""
        return self.longbridge.get_quote(symbol)
    
    def fetch_history_data(self, symbol: str, days: int = 365) -> pd.DataFrame:
        """获取历史数据"""
        return self.longbridge.get_klines(symbol, period=f"{days}d")
    
    def process_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """特征工程"""
        # 使用 QLib 的特征处理
        return self.qlib_handler.create_alpha_features(df)
```

### 2. 策略层：RD-Agent 因子挖掘

```python
class FactorMiner:
    """
    因子挖掘器
    基于 RD-Agent 理念自动发现有效因子
    """
    
    def __init__(self):
        self.alpha_library = []  # 因子库
        
    def mine_factors(self, data: pd.DataFrame) -> List[Dict]:
        """
        自动挖掘因子
        """
        # 1. 技术因子
        tech_factors = self._mine_technical_factors(data)
        
        # 2. 基本面因子
        fund_factors = self._mine_fundamental_factors(data)
        
        # 3. 情绪因子 (Polymarket)
        sentiment_factors = self._mine_sentiment_factors()
        
        return tech_factors + fund_factors + sentiment_factors
    
    def evaluate_factor(self, factor: Dict) -> Dict:
        """评估因子有效性"""
        return {
            "ic": self._calculate_ic(factor),
            "ir": self._calculate_ir(factor),
            "turnover": self._calculate_turnover(factor),
            "score": self._calculate_score()
        }
```

### 3. 模型层：QLib 模型训练

```python
class ModelTrainer:
    """
    模型训练器
    使用 QLib 的模型训练框架
    """
    
    def __init__(self):
        self.models = {}
        
    def train_lightgbm(self, data: pd.DataFrame, label: pd.Series) -> object:
        """训练 LightGBM 模型"""
        from qlib.contrib.estimator import LightGBM
        
        model = LightGBM()
        model.fit(data, label)
        self.models["lightgbm"] = model
        
        return model
    
    def train_lstm(self, data: np.ndarray) -> object:
        """训练 LSTM 模型"""
        from qlib.contrib.model import LSTM
        
        model = LSTM(seq_len=20, n_layers=2)
        model.fit(data)
        self.models["lstm"] = model
        
        return model
    
    def ensemble_predict(self, data: pd.DataFrame) -> np.ndarray:
        """集成预测"""
        pred_lightgbm = self.models["lightgbm"].predict(data)
        pred_lstm = self.models["lstm"].predict(data)
        
        # 加权平均
        return pred_lightgbm * 0.6 + pred_lstm * 0.4
```

### 4. 信号层：多因子信号生成

```python
class SignalGenerator:
    """
    信号生成器
    整合多模型信号
    """
    
    def __init__(self, models: Dict, factors: List[Dict]):
        self.models = models
        self.factors = factors
        self.weights = self._calculate_factor_weights()
        
    def generate_signal(self, data: pd.DataFrame) -> Dict[str, float]:
        """生成交易信号"""
        # 1. 模型预测
        model_pred = self.models.ensemble_predict(data)
        
        # 2. 因子打分
        factor_scores = [self._score_factor(f, data) for f in self.factors]
        
        # 3. 综合评分
        final_score = (
            model_pred * 0.5 +
            np.mean(factor_scores) * 0.3 +
            self._sentiment_score() * 0.2
        )
        
        return {
            "score": final_score,
            "confidence": abs(final_score - 0.5) * 2,
            "direction": "long" if final_score > 0.5 else "short",
            "position_size": self._calculate_position_size(final_score)
        }
```

### 5. 风控层：风险管理

```python
class RiskManager:
    """
    风险管理器
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.max_position = config.get("max_single", 0.30)
        self.max_drawdown = config.get("max_drawdown", 0.10)
        self.stop_loss = config.get("stop_loss", 0.05)
        
    def check_risk(self, signal: Dict, portfolio: Dict) -> Dict:
        """检查风险"""
        # 1. 仓位检查
        if signal["position_size"] > self.max_position:
            signal["position_size"] = self.max_position
            
        # 2. 止损检查
        if self._is_stop_loss_triggered(portfolio):
            signal["action"] = "sell"
            
        # 3. 回撤检查
        if self._check_drawdown():
            signal["action"] = "reduce"
            
        return signal
```

### 6. 执行层：长桥交易

```python
class LongbridgeTrader:
    """
    长桥交易执行器
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.client = self._init_client()
        
    def execute_order(self, signal: Dict, account: Dict) -> Dict:
        """执行订单"""
        # 1. 检查账户余额
        if not self._check_balance(signal, account):
            return {"status": "failed", "reason": "insufficient_funds"}
            
        # 2. 下单
        order = {
            "symbol": signal["symbol"],
            "side": OrderSide.Buy if signal["direction"] == "long" else OrderSide.Sell,
            "quantity": signal["position_size"],
            "order_type": OrderType.Market,
            "time_in_force": TimeInForce.Day,
        }
        
        # 3. 执行
        result = self.client.place_order(**order)
        
        # 4. 记录
        self._log_order(result)
        
        return result
```

---

## 🚀 使用流程

### 1. 安装依赖

```bash
# 安装 QLib
pip install pyqlib

# 安装长桥
pip install longbridge

# 其他依赖
pip install pandas numpy lightgbm pytorch
```

### 2. 配置长桥

```bash
export LONGBRIDGE_APP_KEY="your_app_key"
export LONGBRIDGE_APP_SECRET="your_app_secret"
```

### 3. 运行系统

```bash
# 方式1: 完整流程 (数据 -> 训练 -> 交易)
python scripts/main_trading_system.py --mode full

# 方式2: 仅信号生成
python scripts/main_trading_system.py --mode signal

# 方式3: 仅交易执行
python scripts/main_trading_system.py --mode trade
```

---

## 📊 策略配置

```python
# config/trading_config.yaml

symbols:
  - QQQ
  - NVDA
  - TSLA
  - GOOGL
  - MSFT
  - AAPL
  - AMD
  - META
  - AMZN
  - PLTR

data:
  lookback_days: 365
  train_ratio: 0.8
  rebalance_freq: "weekly"

models:
  lightgbm:
    enabled: true
    weight: 0.6
    params:
      n_estimators: 100
      max_depth: 5
      learning_rate: 0.05
      
  lstm:
    enabled: true
    weight: 0.4
    params:
      seq_len: 20
      n_layers: 2

risk:
  max_single: 0.30
  max_sector: 0.50
  stop_loss: 0.05
  take_profit: 0.10
  max_drawdown: 0.10

execution:
  broker: longbridge
  paper_trading: true  # 模拟交易
```

---

## 🎯 核心功能

### 数据获取
- [ ] 长桥实时行情
- [ ] 历史K线数据
- [ ] 基本面数据
- [ ] Polymarket 情绪

### 因子挖掘
- [ ] 技术因子 (MA, RSI, MACD, Bollinger)
- [ ] 基本面因子 (PE, EPS, ROE)
- [ ] 情绪因子 (Polymarket, 新闻)
- [ ] RD-Agent 自动因子发现

### 模型训练
- [ ] LightGBM 选股模型
- [ ] LSTM 价格预测
- [ ] 模型集成

### 信号生成
- [ ] 多信号融合
- [ ] 仓位计算
- [ ] 置信度评估

### 风控管理
- [ ] 仓位控制
- [ ] 止损机制
- [ ] 回撤控制

### 交易执行
- [ ] 长桥 API
- [ ] 订单管理
- [ ] 成交确认

---

## 📈 绩效目标

| 指标 | 目标 |
|------|------|
| 年化收益 | > 15% |
| 夏普比率 | > 1.0 |
| 最大回撤 | < 10% |
| 胜率 | > 55% |

---

## 🔜 下一步计划

### Phase 1: 基础架构 (本周)
- [ ] 创建目录结构
- [ ] 实现 DataManager
- [ ] 连接长桥 API

### Phase 2: 因子模型 (第2周)
- [ ] 实现因子挖掘
- [ ] 训练 LightGBM 模型
- [ ] 训练 LSTM 模型

### Phase 3: 信号执行 (第3周)
- [ ] 信号生成器
- [ ] 风控模块
- [ ] 长桥交易对接

### Phase 4: 优化迭代 (持续)
- [ ] RD-Agent 因子发现
- [ ] 模型自动优化
- [ ] 策略迭代

---

## 💡 关键优势

| 优势 | 说明 |
|------|------|
| **QLib 基础设施** | 微软开源，稳定可靠 |
| **RD-Agent 自动化** | AI 自动因子挖掘和模型优化 |
| **长桥实时交易** | 低延迟，可靠的执行 |
| **模块化设计** | 易于扩展和维护 |

---

## 🤝 与现有系统集成

```
现有系统                          新系统
    ↓                                ↓
Portfolio Monitor (EOF)    ←→    Risk Manager
Polymarket Monitor        ←→    Sentiment Factor
WeChat Monitor           ←→    News Factor
BTC Monitor               ←→    Crypto Signal
```

---

*由 ProActive Agent 自动设计*
*基于 QLib + RD-Agent + Longbridge 整合*
