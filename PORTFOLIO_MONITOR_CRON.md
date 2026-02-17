# 📊 持仓监控定时任务

**任务名称**: Portfolio Monitor  
**频率**: 每小时  
**触发**: 自动运行 `scripts/portfolio_check.py`

## 功能

1. **检查持仓状态**
   - 股票盈亏
   - 期权状态
   - 资金状况

2. **止盈止损检查**
   - 股票止损: -5%
   - 股票止盈: +10%
   - 期权止损: -50%
   - 期权止盈: +30%

3. **到期预警**
   - 期权到期前7天提醒

## 输出

报告格式:
```
📊 持仓监控报告
==================

💼 股票持仓:
  NVDA: 54股 @ $186.94
       市值: $9,822.60
       🔴 $-272 (-2.7%)

📈 期权持仓:
  NVDA260320P165
       行权价: $165
       到期: 2026-03-20
       🟢 $0 (0.0%)
       止损: $21.83
       止盈: $7.28

⚠️ 警报:
  (如果有)
```

## 手动运行

```bash
python scripts/portfolio_check.py
```

## 修改频率

- **每小时**: `openclaw cron update --every 1h Portfolio Monitor`
- **每日4次**: `openclaw cron update --cron "0 9,12,15,18 * * *" Portfolio Monitor`
