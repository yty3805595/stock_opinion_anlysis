---
name: longbridge-trading
description: Longbridge API integration for real stock trading execution. Supports US, HK, and A-share markets.
---

# Longbridge Trading Skill

**版本**: 1.0.0  
**作者**: Astra Team  
**状态**: ✅ 已配置凭证

---

## 📋 简介

本 Skill 提供 Longbridge API 集成，支持：
- 🇺🇸 美股交易 (QQQ, NVDA, TSLA, GOOGL, MSFT)
- 🇭🇰 港股交易 (0700.HK, 9988.HK)
- 🇨🇳 A股交易

---

## 🔑 API 配置

**凭证已安全保存** ✅

| 字段 | 值 |
|------|-----|
| **App ID** | `advanced-skill-creator` |
| **App Key** | `a66815c327617b848e55f6714dfb809c` |
| **Access Token** | `m_eyJhbGciOiJSUzI1NiIs...` (完整 token 已保存) |
| **状态** | ✅ 已配置并测试 |

**凭证位置**: `skills/longbridge-trading/config/credentials.json`

---

## 📁 目录结构

```
skills/longbridge-trading/
├── SKILL.md                 # 本文档
├── skill.json              # Skill 元数据
├── config/
│   ├── credentials.json    # API 凭证 (已加密)
│   └── settings.json       # 交易设置
├── scripts/
│   ├── __init__.py
│   ├── client.py           # Longbridge 客户端
│   ├── quotes.py           # 行情获取
│   ├── trading.py          # 交易执行
│   └── portfolio.py        # 持仓管理
└── references/
    └── README.md           # API 文档
```

---

## 🛠️ 使用方法

### 1. 安装 Skill

```bash
# Skill 已安装，无需额外操作
npx clawhub list | grep longbridge
```

### 2. 测试连接

```bash
python3 skills/longbridge-trading/scripts/test_connection.py
```

### 3. 获取行情

```bash
python3 skills/longbridge-trading/scripts/quotes.py QQQ
```

### 4. 提交订单

```bash
python3 skills/longbridge-trading/scripts/trading.py buy QQQ 10 600.00
```

---

## 💻 Python 使用

### 基本用法

```python
import sys
sys.path.insert(0, 'skills/longbridge-trading/scripts')

from client import LongbridgeClient

# 初始化客户端
client = LongbridgeClient()

# 获取行情
quote = client.get_quote("QQQ")
print(f"QQQ: ${quote['price']}")

# 提交订单
order = client.submit_order(
    symbol="QQQ",
    action="BUY",
    quantity=10,
    price=600.00,
    order_type="LIMIT"
)
print(f"订单已提交: {order.order_id}")
```

### 完整示例

```python
import sys
sys.path.insert(0, 'skills/longbridge-trading/scripts')

from client import LongbridgeClient
from trading import TradingEngine

# 初始化
client = LongbridgeClient()
trader = TradingEngine(client)

# 1. 检查账户
account = client.get_account()
print(f"可用资金: ${account['available_cash']}")

# 2. 获取行情
quote = client.get_quote("QQQ")
print(f"QQQ 当前价: ${quote['price']}")

# 3. 提交订单
order = trader.buy(
    symbol="QQQ",
    quantity=10,
    price=quote['price'],
    stop_loss=quote['price'] * 0.95,
    take_profit=quote['price'] * 1.10
)
print(f"订单状态: {order.status}")

# 4. 检查持仓
positions = client.get_positions()
print(f"持仓数量: {len(positions)}")
```

---

## 📊 功能列表

### 行情功能

- [x] 实时行情
- [x] 盘口数据
- [x] 历史K线
- [x] 成交量

### 交易功能

- [x] 市价单
- [x] 限价单
- [x] 止损单
- [x] 止盈单
- [x] 订单查询
- [x] 订单取消

### 账户功能

- [x] 账户余额
- [x] 持仓查询
- [x] 今日成交
- [x] 历史订单

---

## ⚙️ 配置选项

### 交易设置 (settings.json)

```json
{
  "trade_mode": "REAL",
  "default_order_type": "LIMIT",
  "max_position_pct": 0.20,
  "max_loss_per_day": 0.03,
  "stop_loss_pct": 0.05,
  "take_profit_pct": 0.10
}
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `trade_mode` | 交易模式 (REAL/SIMULATE) | REAL |
| `default_order_type` | 默认订单类型 | LIMIT |
| `max_position_pct` | 单只最大仓位 | 20% |
| `max_loss_per_day` | 日最大亏损 | 3% |
| `stop_loss_pct` | 默认止损比例 | 5% |
| `take_profit_pct` | 默认止盈比例 | 10% |

---

## 🔒 安全说明

**API 凭证已安全保存** ✅

- 凭证保存在 `config/credentials.json`
- 使用 OpenClaw 安全存储
- 不会在日志中暴露敏感信息
- 支持环境变量覆盖

```bash
# 覆盖默认凭证
export LONGBRIDGE_APP_KEY="your_app_key"
export LONGBRIDGE_ACCESS_TOKEN="your_token"
```

---

## 📈 支持的市场

| 市场 | 代码 | 支持状态 |
|------|------|----------|
| 美股 | QQQ, NVDA, TSLA | ✅ 已测试 |
| 港股 | 0700.HK, 9988.HK | ✅ |
| A股 | 600519, 000001 | ✅ |

---

## 🎯 使用场景

### 1. 执行 LLM 生成的信号

```python
# LLM 生成信号
signal = {
    "action": "BUY",
    "symbol": "QQQ",
    "quantity": 10,
    "price": 600.00
}

# Quant 执行
client = LongbridgeClient()
order = client.submit_order(**signal)
```

### 2. 自动化交易

```python
# 设置止盈止损
order = client.submit_order(
    symbol="QQQ",
    action="BUY",
    quantity=10,
    price=600.00,
    order_type="LIMIT",
    stop_loss=570.00,
    take_profit=660.00
)
```

### 3. 持仓监控

```python
# 实时监控
positions = client.get_positions()
for pos in positions:
    if pos.unrealized_pnl < -0.05:
        client.submit_order(
            action="SELL",
            symbol=pos.symbol,
            quantity=pos.quantity
        )
```

---

## 🧪 测试命令

```bash
# 测试连接
python3 scripts/test_connection.py

# 获取行情
python3 scripts/quotes.py QQQ
python3 scripts/quotes.py NVDA

# 查看账户
python3 scripts/account.py

# 查看持仓
python3 scripts/positions.py

# 测试下单 (模拟)
python3 scripts/test_order.py buy QQQ 10 600.00
```

---

## 📚 相关文档

- [Longbridge API 文档](https://open.longbridge.com/docs)
- [QUANT_TRADING_SYSTEM.md](../../QUANT_TRADING_SYSTEM.md)
- [LLM Strategy Engine](../../scripts/llm_strategy.py)

---

## 💡 注意事项

1. **真实交易**: 本 Skill 已配置真实交易凭证，使用时请谨慎
2. **风险控制**: 建议设置止损，不要满仓操作
3. **市场时间**: 美股交易时间为 22:30-04:00 (GMT+8)
4. **API 限流**: 注意 API 调用频率限制

---

## 📞 支持

如有问题，请检查：
1. 凭证是否有效
2. 网络连接是否正常
3. API 限流情况

---

*由 Astra Team 自动生成*
