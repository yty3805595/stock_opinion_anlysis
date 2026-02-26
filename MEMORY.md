# MEMORY.md

## Important Notes

### US Stock Market Hours (GMT+8)

| Session | Time (GMT+8) | Notes |
|---------|--------------|-------|
| Pre-market | 21:30 - 22:30 | 21:30 starts |
| **Regular hours** | **22:30 - 04:00** | **Official open: 22:30** |
| After-hours | 04:00 - 05:00 | Limited liquidity |

**Trading days:** Monday to Friday (excluding holidays)

**Key times:**
- Open: 22:30 GMT+8
- Close: 04:00 GMT+8 (next day)
- Pre-market starts: 21:30 GMT+8

---

### GOOGL Price Alert (Set on 2026-02-12)

- **Baseline price:** $310.96
- **Alert threshold:** $279.86 (10% drop)
- **Current status:** Monitoring paused until market open

---

### Trading Journal & Backtesting System (Started on 2026-02-13)

**File:** `trading_journal.md`

**Purpose:** Track all trading decisions and recommendations for performance analysis.

**Records so far:**
| Date | Stock | Action | Price | Status |
|------|-------|--------|-------|--------|
| 2026-02-13 16:54 | TSLA.US | Buy 10 shares | $417.07 | Pending |
| 2026-02-13 12:05 | QQQ.US | Buy 68 shares | $600.64 | Pending |
| 2026-02-13 12:05 | NVDA.US | Buy 54 shares | $186.94 | Pending |
| 2026-02-13 12:05 | MSFT.US | Buy 25 shares | $401.84 | Pending |
| 2026-02-13 12:05 | GOOGL.US | Buy 33 shares | $309.00 | Pending |

**Backtesting Metrics (to be tracked):**
- Win rate
- Average return
- Maximum drawdown
- EOF strategy performance vs S&P 500

---

### Longbridge API 正确用法 (Updated on 2026-02-26)

**❌ 旧方法（错误）:**
- 从环境变量加载凭证
- `await ctx.positions()` 异步调用
- `quote.last` 获取价格
- `len(positions)` 直接迭代

**✅ 正确方法:**

```python
import json
from longbridge.openapi import Config, TradeContext, QuoteContext

# 1. 从文件加载凭证
with open("/Users/yintaoye/.openclaw/workspace/skills/longbridge-trading/config/credentials.json") as f:
    creds = json.load(f)["credentials"]

# 2. 初始化 Config (需要 access_token!)
config = Config(
    app_key=creds["app_key"], 
    app_secret=creds["app_secret"],
    access_token=creds["access_token"]
)

# 3. 获取持仓 (同步调用!)
trade_ctx = TradeContext(config)
positions_resp = trade_ctx.stock_positions()

# 4. 遍历持仓
for channel in positions_resp.channels:
    if 'lb_papertrading' in channel.account_channel:
        for p in channel.positions:
            print(f"{p.symbol}: {p.quantity} @ ${p.cost_price}")

# 5. 获取实时行情
quote_ctx = QuoteContext(config)
quotes = quote_ctx.quote(["TSLA.US", "NVDA.US"])
for q in quotes:
    print(f"{q.symbol}: ${q.last_done}")  # 注意是 last_done 不是 last!

# 6. 获取账户余额 (返回 list)
balance = trade_ctx.account_balance()
for bal in balance:
    print(f"总资产: ${bal.net_assets}")
```

**关键点:**
- Config 初始化需要三个参数: `app_key`, `app_secret`, `access_token`
- 所有 API 调用都是**同步**的，不需要 await
- 行情价格属性是 `.last_done` 不是 `.last`
- 持仓在 `positions_resp.channels[0].positions` 里
- 余额返回是 list 不是单个对象
- 账户类型: `lb_papertrading` = 模拟盘

---

### 当前持仓 (2026-02-26)

| 代码 | 数量 | 成本价 | 当前价 | 盈亏 |
|------|------|--------|--------|------|
| TSLA.US | 10 | $416.67 | $417.40 | +0.18% |
| NVDA.US | 100 | $189.69 | $195.56 | +3.10% |
| MSFT.US | 25 | $401.78 | $400.60 | -0.29% |
| GOOGL.US | 33 | $309.00 | $312.90 | +1.26% |
| QQQ.US | 68 | $600.64 | $616.68 | +2.67% |
| NVDA260306C195000.US | -1 | $6.78 | -- | (期权空头) |

**总盈亏: +$1,784.62 (+2.12%)**
**账户总资产: $811,300.60 HKD**
**USD可用: $19,082.78**

---

### RD-Agent Skill (2026-02-26)

**位置:** `~/.openclaw/workspace/skills/rd-agent/`

**功能:**
- 因子挖掘 (77+ 因子)
- 每日回测
- 交易信号
- 期权监控

**使用:**
```bash
# 因子挖掘
python3 ~/.openclaw/workspace/skills/rd-agent/scripts/rd_agent_factor_mining_v2.py

# 每日回测
python3 ~/.openclaw/workspace/skills/rd-agent/scripts/rd_agent_backtest_scheduler.py
```

**Cron 任务:**
- 09:00 - 因子挖掘
- 10:00 - 每日回测

---

### 统一监控系统 (2026-02-26)

**脚本**: `monitor_all.py`

**功能**:
1. 自动同步持仓数据 (`sync_portfolio.py`)
2. 生成每日交易报告 (`rd_agent_daily.py`)
3. 监控期权持仓 (`rd_options_tool.py --monitor`)
4. 风控检查 (止损/止盈)

**运行方式**:
```bash
python3 monitor_all.py
```

**已修复问题**:
- 期权监控数据格式兼容
- Decimal 类型 JSON 序列化
- 所有脚本统一使用 Longbridge API 正确方法
