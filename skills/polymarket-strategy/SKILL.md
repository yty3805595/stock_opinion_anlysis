---
name: polymarket-strategy
description: Polymarket 预测市场交易策略，包含信号分析、风险管理、和自动监控功能。基于群众智慧和概率分析进行交易决策。
metadata:
  {
    "openclaw": {
      "emoji": "🎯",
      "requires": { "bins": ["python3"] },
      "features": [
        "市场信号分析",
        "概率评估",
        "风险管理",
        "定时监控",
        "机会推送"
      ]
    }
  }
---

# Polymarket 交易策略

基于预测市场的群众智慧和概率分析进行交易决策。

## 核心原则

### 1. 只交易高概率事件

| 概率范围 | 策略 | 仓位 |
|----------|------|------|
| >90% | 强烈推荐 | 5-10% |
| 70-90% | 谨慎参与 | 3-5% |
| 50-70% | 观望 | 0% |
| <50% | 不参与 | 0% |

### 2. 风险控制

- **单笔最大仓位**: 10%
- **日最大仓位**: 30%
- **止损线**: -50%（归零风险）
- **止盈目标**: 30-50%

### 3. 期望值为正

```
期望值 = 概率 × 收益 - (1-概率) × 损失
```

只有期望值 > 0 才参与

## 交易信号

### 强烈信号 (>90%)

```python
SIGNALS = {
    "government_shutdown": {
        "event": "政府周六关门",
        "probability": 96.8,
        "action": "NO",
        "min_investment": 10,
        "max_investment": 100,
        "expected_return": 0.03,  # 3%
        "risk": 0.032  # 3.2%
    },
    "btc_above_66000": {
        "event": "BTC 2/14 > $66,000",
        "probability": 97.7,
        "action": "YES",
        "min_investment": 10,
        "max_investment": 100,
        "expected_return": 0.10,  # 10%
        "risk": 0.024  # 2.4%
    }
}
```

### 中等信号 (70-90%)

```python
MEDIUM_SIGNALS = {
    "fed_no_rate_change": {
        "event": "Fed 3月不降息",
        "probability": 93.5,
        "action": "YES",
        "min_investment": 5,
        "max_investment": 50,
        "expected_return": 0.07,
        "risk": 0.065
    }
}
```

## 市场类型

### 1. 政治事件

- 选举结果
- 政府决策
- 国际关系

**风险**: 高，可能有法律风险

### 2. 金融事件

- Fed 利率决策
- 股市预测
- 经济数据

**风险**: 中等，信息来源广

### 3. 加密货币

- BTC 价格预测
- ETH 价格预测

**风险**: 中等，波动大

### 4. 体育/娱乐

- 比赛结果
- 奖项评选

**风险**: 较低

## 交易流程

### 1. 信号识别

```bash
# 获取 Top 市场
python3 skills/polymarket-api/scripts/polymarket.py --top

# 搜索特定市场
python3 skills/polymarket-api/scripts/polymarket.py --search "btc"
```

### 2. 概率分析

```
检查条件:
1. 概率 > 70%？
2. 期望值为正？
3. 流动性充足（> $100k 24h）？
4. 事件可验证？
```

### 3. 仓位计算

```python
def calculate_position(probability, expected_return, risk, total_capital):
    """计算仓位"""
    if probability < 70:
        return 0
    
    if probability > 90:
        max_pct = 0.10  # 10%
    elif probability > 80:
        max_pct = 0.07  # 7%
    else:
        max_pct = 0.05  # 5%
    
    # 期望值计算
    expected_value = (probability/100) * expected_return - ((100-probability)/100) * risk
    
    if expected_value <= 0:
        return 0
    
    return total_capital * max_pct
```

### 4. 执行交易

**注意**: Polymarket 无交易 API，需手动操作

1. 登录 polymarket.com
2. 找到目标市场
3. 点击 YES/NO 按钮
4. 输入金额
5. 确认交易

### 5. 监控和退出

- 定期检查市场价格
- 达到止盈目标可部分获利
- 接近归零时考虑止损

## 定时监控

### 设置 Cron 任务

```bash
# 每天 8, 12, 18, 22 点监控
cron add --name "Polymarket 监控" \
  --schedule "cron 0 8,12,18,22 * * *" \
  --payload '{"kind":"agentTurn","message":"运行 Polymarket 监控"}' \
  --sessionTarget isolated
```

### 推送条件

只有以下情况会推送：

1. 发现 >90% 概率的机会
2. 现有持仓达到止盈/止损
3. 市场重大变化

## 禁止交易

以下情况**不交易**：

1. 概率 < 70%
2. 期望值为负
3. 流动性不足 (< $10k 24h)
4. 法律风险高（选举类）
5. 无法验证结果的事件

## 常见问题

### Q: 如何判断概率是否可靠？

A: 检查 24h 交易量
- > $1M: 高度可靠
- $100k-$1M: 中等可靠
- < $100k: 不够可靠

### Q: 什么时候卖？

A:
- 达到止盈（30-50%）
- 概率下降到 70% 以下
- 事件临近但概率仍高

### Q: 会归零吗？

A: 会，如果预测错误，YES/NO 合约价值归零

## 相关文件

- `skills/polymarket-api/` - API 接口
- `github_reports/polymarket_*.md` - 分析报告

---

*基于 Polymarket 教程学习形成*
