# RD-Agent 每日交易系统

自动执行 RD-Agent 因子分析、回测优化和交易决策。

## 功能

1. **因子挖掘**: 使用 RD-Agent 方法论分析股票因子
2. **自动回测**: 基于历史数据回测交易信号
3. **信号优化**: 根据回测结果优化交易信号
4. **交易执行**: 生成交易建议并执行
5. **风控检查**: 设置止损止盈

## 已创建

- `scripts/rd_agent_daily.py` - 每日交易脚本
- `skills/rd-agent-daily-trading/SKILL.md` - Skill 文档
- Cron 任务: "RD-Agent 每日交易分析" (每天 9:00 周一至周五)

## 使用方法

### 1. 手动运行

```bash
cd /Users/yintaoye/.openclaw/workspace
python3 scripts/rd_agent_daily.py
```

### 2. Cron 自动运行

任务已配置:
- **名称**: RD-Agent 每日交易分析
- **时间**: 每天 9:00 (周一至周五)
- **模型**: MiniMax-M2.5

## 工作流程

```
1. 获取当前持仓
2. 获取实时价格
3. 计算技术因子 (MA5/10/20/60/120, RSI, MACD, 波动率)
4. 计算 IC (信息系数)
5. 生成交易信号
6. 输出每日报告
```

## 输出

- 持仓状态
- 因子信号
- 交易建议
- 风控设置
