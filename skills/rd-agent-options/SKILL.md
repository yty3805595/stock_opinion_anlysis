# RD-Agent Options Trading Skill

## 功能

集成 RD-Agent 三阶段架构的期权交易系统：
- **Research**: Polymarket 情绪 + Tavily 新闻 + 技术分析
- **Develop**: 股票信号 + 期权策略生成
- **Feedback**: 绩效评估 + 策略优化

## 命令

```bash
# 分析期权信号
python3 scripts/rd_options_tool.py --analyze

# 执行期权交易
python3 scripts/rd_options_tool.py --execute NVDA

# 监控期权持仓
python3 scripts/rd_options_tool.py --monitor

# 实时获取期权价格
python3 scripts/rd_options_trading.py --fetch-price NVDA
```

## 核心文件

| 文件 | 功能 |
|------|------|
| `scripts/rd_options_trading.py` | 期权交易核心逻辑 |
| `scripts/rd_options_tool.py` | CLI 工具 |
| `data/options_portfolio.json` | 期权持仓记录 |

## 期权参数

| 参数 | 值 |
|------|------|
| 行权价 | 价内 5% (strike_price × 0.95) |
| 到期日 | 30 天后 |
| 合约大小 | 100 股/张 |
| 最小权利金 | 标的参数决定 |

## 定时任务

| 时间 | 任务 | 触发 |
|------|------|------|
| 10:00 | 期权信号分析 | `RD-Agent 期权信号分析` |
| 16:00 | 期权信号分析 | `RD-Agent 期权信号分析` |
| 22:00 | 期权信号分析 | `RD-Agent 期权信号分析` |

## RD Score 排名

当前 Top 3 期权：
1. **NVDA Put** - RD Score 0.672 (置信度 85%)
2. **MSFT Put** - RD Score 0.595 (置信度 80%)
3. **QQQ Put** - RD Score 0.583 (置信度 78%)

## 使用示例

```bash
# 1. 分析所有标的
python3 scripts/rd_options_tool.py --analyze

# 2. 执行最佳期权
python3 scripts/rd_options_tool.py --execute NVDA

# 3. 监控持仓状态
python3 scripts/rd_options_tool.py --monitor
```
