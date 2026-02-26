---
name: rd-agent
description: 增强版 RD-Agent 量化交易系统 - 因子挖掘、回测、信号生成
version: 2.0.0
author: Astra Team
---

# 🤖 RD-Agent 量化交易系统

基于微软 RD-Agent 论文理念的 AI 驱动美股交易系统，支持因子挖掘、自动回测、信号生成。

---

## 功能概览

| 功能 | 脚本 | 说明 |
|------|------|------|
| **实盘交易** | `rd_agent_trading_v2.py` | 因子+信号+期权+实盘执行 |
| **图表可视化** | `rd_agent_chart.py` | TradingView Lightweight Charts 可视化 |
| **自动挖掘回测** | `rd_agent_auto_mining.py` | 自动化因子挖掘 + 回测 + 复盘 |
| 因子挖掘 | `rd_agent_factor_mining_v2.py` | 77+ 技术因子挖掘与评估 |
| 每日回测 (真实) | `rd_agent_backtest_v2.py` | yfinance 真实数据回测 |
| 期权监控 | `rd_options_tool.py` | 期权持仓监控 |

---

## 快速使用

### 1. 图表可视化 (TradingView Lightweight Charts)

```bash
python3 skills/rd-agent/scripts/rd_agent_chart.py --symbol NVDA
# 然后打开 /tmp/rd_agent_NVDA.html 查看
```

**生成交互式图表:**
- K线 + 均线 (MA5, MA20)
- 成交量
- RSI
- MACD

### 2. 实盘交易系统

```bash
python3 skills/rd-agent/scripts/rd_agent_trading_v2.py
```

**功能:**
- 自动获取持仓 (Longbridge)
- 实时行情
- 因子分析 & 信号生成
- 期权分析
- 执行建议

### 2. 自动挖掘回测

```bash
python3 skills/rd-agent/scripts/rd_agent_auto_mining.py
```

### 2. 每日回测 (真实数据)

```bash
python3 skills/rd-agent/scripts/rd_agent_backtest_v2.py
```

**使用 yfinance 获取真实数据，回测标的:** QQQ, NVDA, TSLA, GOOGL, MSFT, SPY, AAPL, META

### 3. 每日回测 (模拟数据)

```bash
python3 skills/rd-agent/scripts/rd_agent_backtest_scheduler.py
```

### 4. 交易信号

```bash
python3 skills/rd-agent/scripts/rd_agent_trading.py
```

### 5. 期权监控

```bash
python3 skills/rd-agent/scripts/rd_options_tool.py --monitor
```

---

## 定时任务 (Cron)

| 任务 | 时间 | 说明 |
|------|------|------|
| 因子挖掘 | 09:00 | 每日挖掘新因子 |
| 每日回测 | 10:00 | 多标的回测 (真实数据) |
| 信号分析 | 09:15:21 | 盘前/盘中/盘后 |

---

## Python 使用

```python
import sys
sys.path.insert(0, 'skills/rd-agent/scripts')

from rd_agent_factor_mining_v2 import EnhancedFactorMiner

miner = EnhancedFactorMiner()
factors = miner.run("NVDA.US", 500)

for f in factors[:10]:
    print(f"{f.name}: IC={f.ic:.4f}")
```

---

## 数据源

- **yfinance** - 真实历史数据 (主要)
- **Longbridge API** - 实时行情

---

## 注意事项

1. 首次运行需安装 yfinance (`pip install yfinance`)
2. 回测结果仅供参考，不构成投资建议
3. 建议结合风控系统使用
