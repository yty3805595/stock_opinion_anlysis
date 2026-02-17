# 📈 EOF 全天候交易策略手册 v2.1

**创建时间**: 2026-02-15  
**更新时间**: 2026-02-17  
**版本**: v2.1 (RD-Agent 增强版)

---

## ⚠️ 重要声明

**当前所有交易均为【模拟交易】**

- ❌ 未配置真实券商账号
- ❌ 未连接任何交易 API
- ⚠️ 所有盈亏均为模拟，不涉及真实资金
- 🔑 如需真实交易，请提供 Longbridge API 账号

---

## 🎯 策略概览

### EOF + RD-Agent 策略

| 项目 | 内容 |
|------|------|
| **名称** | 经济产出因子 + RD-Agent + 期权增强 |
| **周期** | 中长线 |
| **核心** | RD-Agent 驱动决策 + 期权保护 |
| **目标** | 年化 15-25%，最大回撤 <10% |
| **状态** | ⚠️ 模拟中 |

---

## 🤖 RD-Agent 架构

### 三阶段流程

```
┌─────────────────────────────────────────────────────────┐
│                    RD-Agent 期权交易系统                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1️⃣ Research     →     2️⃣ Develop     →    3️⃣ Feedback  │
│     研究数据            生成策略            绩效评估      │
│                                                          │
│  ┌─────────────┐      ┌─────────────┐    ┌───────────┐ │
│  │ Polymarket  │      │  策略生成   │    │  绩效归因 │ │
│  │ 情绪 (25%)  │      │  信号计算   │    │  策略优化 │ │
│  └─────────────┘      └─────────────┘    └───────────┘ │
│  ┌─────────────┐      ┌─────────────┐                 │
│  │ Tavily 新闻 │      │ 仓位计算    │                 │
│  │ 情绪 (25%)  │      │ 参数优化    │                 │
│  └─────────────┘      └─────────────┘                 │
│  ┌─────────────┐                                   │
│  │ 技术分析    │                                   │
│  │ (35%)      │                                   │
│  └─────────────┘                                   │
│  ┌─────────────┐                                   │
│  │ 基本面 (15%)│                                   │
│  └─────────────┘                                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### RD 权重配置

| 数据源 | 权重 | 说明 |
|--------|------|------|
| **Polymarket** | 25% | 市场情绪、事件概率 |
| **Tavily 新闻** | 25% | 舆情分析、热点事件 |
| **技术分析** | 35% | 趋势、动量、波动率 |
| **基本面** | 15% | PE、增长率 |

---

## 📊 Research 模块

### 数据收集

#### 1. Polymarket 情绪

```python
# 示例
polymarket_sentiment = {
    "QQQ": 0.99,   # Fed 维持利率
    "NVDA": 0.70,  # AI 热点
    "TSLA": 0.45,  # 争议较大
}
```

**数据来源**: Polymarket API  
**更新频率**: 每4小时  
**权重**: 25%

#### 2. Tavily 新闻情绪

```python
# 示例
news_sentiment = {
    "NVDA": 0.70,  # AI芯片热点
    "MSFT": 0.60,  # OpenAI
    "PLTR": 0.40,  # 波动大
}
```

**数据来源**: Tavily Search API  
**更新频率**: 每日2次  
**权重**: 25%

#### 3. 技术分析

```python
technical_analysis = {
    "trend": "bearish/neutral/bullish",
    "momentum": "oversold/neutral/overbought", 
    "volatility": "low/normal/high",
    "rsi": 25,  # 超卖
    "ma20": 550,
}
```

**指标**: MA, RSI, MACD, Bollinger, 波动率  
**权重**: 35%

#### 4. 基本面

```python
fundamental = {
    "pe_ratio": 35,
    "growth_rate": 0.25,
    "score": 0.70,
}
```

**数据**: PE, EPS, 营收增长  
**权重**: 15%

---

## 🎯 Develop 模块

### 策略映射

| 趋势 | 动量 | 波动率 | 策略 |
|------|------|--------|------|
| Bearish | Oversold | High | 🛡️ Hedge |
| Bearish | Oversold | Normal | 🎣 Bottom Fish |
| Bearish | Neutral | High | 🛡️ Hedge |
| Neutral | Oversold | Normal | 🎣 Bottom Fish |
| Bearish | Neutral | Normal | 🛡️ Hedge |
| Neutral | Neutral | High | 📊 Speculate |

### 期权参数计算

#### 🛡️ Hedge (对冲)

```python
hedge_params = {
    "strike_price": current_price * 0.95,   # 略低于现价
    "expiration": 30,                       # 30天后到期
    "position_size": 0.01,                  # 1% 仓位
    "confidence": 0.7 + polymarket * 0.2,
}
```

#### 🎣 Bottom Fish (抄底)

```python
bottom_fish_params = {
    "strike_price": current_price * 0.90,   # 低于现价10%
    "expiration": 60,                       # 60天后到期
    "position_size": 0.005,                 # 0.5% 仓位
    "confidence": 0.6 + rsi_oversold_bonus,
}
```

#### 📊 Speculate (波动率)

```python
speculate_params = {
    "strike_price": current_price * 0.92,   # ATM
    "expiration": 21,                       # 21天后到期
    "position_size": 0.005,                 # 0.5% 仓位
    "confidence": 0.5 + iv_bonus,
}
```

---

## 📈 执行模块

### 仓位管理

| 参数 | 值 | 说明 |
|------|-----|------|
| **期权最大仓位** | 5% | 占总资产 |
| **单期权最大** | 2% | 单个合约 |
| **默认仓位** | 1% | 建议首次 |
| **最小仓位** | 0.5% | 最小投入 |

### 风控规则

```python
risk_rules = {
    "max_loss_per_option": 0.50,   # 单期权最大亏损 50%
    "min_confidence": 0.60,         # 置信度阈值
    "max_positions": 10,            # 最大持仓数
    "hedge_threshold": 0.02,        # 下跌 2% 触发对冲
}
```

---

## 🎯 策略示例

### 场景1: QQQ 对冲

```
日期: 2026-02-17
市场: QQQ 下跌至 $520 (MA20: $600)

RD Research:
  - Polymarket: 0.99 (Fed 稳定)
  - News: 0.55 (AI 热点)
  - Technical: Bearish + RSI 25
  - Fundamental: 0.70

RD Score: 0.65 | 置信度: 91%

Develop:
  - 策略: Hedge
  - Put @ $520 * 0.95 = $494
  - 到期: 30天
  - 仓位: 1%

Execute:
  ✅ 买入 QQQ Put @ $494
  成本: $1,000
  保护: 股票仓位 $20,000
```

### 场景2: NVDA 抄底

```
日期: 2026-02-17
市场: NVDA 下跌至 $180 (RSI: 28)

RD Research:
  - Polymarket: 0.70 (AI 情绪乐观)
  - News: 0.70 (芯片热点)
  - Technical: Oversold + RSI 28
  - Fundamental: 0.85

RD Score: 0.57 | 置信度: 81%

Develop:
  - 策略: Bottom Fish
  - Put @ $180 * 0.90 = $162
  - 到期: 60天
  - 仓位: 1%

Execute:
  ✅ 买入 NVDA Put @ $162
  成本: $500
  目标: 反弹 10-20%
```

---

## 📁 文件结构

```
scripts/
├── rd_options_trading.py       # RD-Agent 期权系统 (核心!)
├── options_trading.py          # 基础期权系统
├── trading_system_v2.py       # 股票交易系统
└── data/
    ├── rd_agent_signals.json  # RD 信号记录
    └── options_portfolio.json # 期权持仓

rd_options_tool.py             # 命令行工具
TRADING_STRATEGY_V2.md        # 策略文档
```

---

## 🚀 使用方法

### 命令行工具

```bash
# 分析所有标的
python rd_options_tool.py --analyze

# 执行特定信号
python rd_options_tool.py --execute QQQ

# 平仓
python rd_options_tool.py --close QQQ

# 查看持仓
python rd_options_tool.py --portfolio
```

### Python API

```python
from scripts.rd_options_trading import RDOptionsTrader

# 创建系统
trader = RDOptionsTrader(50000)

# 市场数据
market_data = {
    "QQQ": {"price": 580, "ma20": 600, "rsi": 25, "volatility": 0.35},
    "NVDA": {"price": 180, "ma20": 185, "rsi": 45, "volatility": 0.40},
}

# 分析
strategies = trader.analyze_all(market_data)
trader.print_report(strategies)

# 执行
best = max(strategies, key=lambda x: x.rd_score)
if best.rd_score > 0.55:
    trader.execute_strategy(best)
```

---

## 📊 监控任务

| 任务 | 频率 | 内容 |
|------|------|------|
| **RD-Agent 分析** | 每日 3 次 | 多源数据整合 |
| **期权信号** | 9:00, 15:00, 21:00 | 信号生成 |
| **持仓监控** | 每小时 | 损益检查 |

---

## 📈 绩效目标

### RD-Agent 部分

| 指标 | 目标 |
|------|------|
| **信号准确率** | > 60% |
| **平均收益** | > 15%/年 |
| **对冲效率** | 减少回撤 30% |

### 期权部分

| 指标 | 目标 |
|------|------|
| **对冲盈利** | 覆盖股票亏损 20-50% |
| **抄底收益** | 单次 20-50% |
| **期权亏损** | < 1%/月 |

---

## 💡 核心理念

### RD-Agent = 多维决策

```
不是单一信号，而是多源数据融合:

Polymarket (25%) + Tavily (25%) + 技术 (35%) + 基本面 (15%)
     ↓              ↓              ↓             ↓
   情绪           舆情          趋势          价值
     ↓              ↓              ↓             ↓
              综合判断 → 最佳策略 → 执行
```

### 期权 = 风险对冲 + 收益增强

```
对冲: 下跌保护 → 减少回撤
抄底: 低位买入 → 反弹收益
      ↓
  两者结合 = 全天候
```

---

## ⚠️ 风险提示

1. **RD-Agent 局限**: 历史数据不代表未来
2. **期权风险**: 可能损失 100% 权利金
3. **时间价值**: Theta 损耗
4. **流动性**: 部分期权可能流动性差
5. **模拟风险**: 历史表现不代表未来收益

---

## 🔗 相关文件

| 文件 | 说明 |
|------|------|
| `scripts/rd_options_trading.py` | RD-Agent 期权系统 |
| `rd_options_tool.py` | 命令行工具 |
| `TRADING_STRATEGY.md` | 基础策略文档 |

---

*EOF + RD-Agent + Options - 全天候交易策略* 🌐

**"用 RD-Agent 做决策，用期权保护收益"**
