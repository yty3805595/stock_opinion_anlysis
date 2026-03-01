# 🤖 OpenClaw Agent 团队协作指南

## 团队成员

| Agent | 角色 | Workspace | 专长 |
|-------|------|-----------|------|
| **main** | 首席助手 | ~/.openclaw/workspace | 综合协调 |
| **astra** | 财富管理大师 | ~/.openclaw/agents/astra | 投资策略 |
| **analyst** | 数据分析师 | ~/.openclaw/agents/analyst | 市场分析 |
| **trader** | 量化交易员 | ~/.openclaw/agents/trader | 策略执行 |
| **researcher** | 研究员 | ~/.openclaw/agents/researcher | 深度调研 |

---

## 使用方法

### 方法 1：直接切换 Agent
```bash
# 在聊天中指定 agent
@astra 分析特斯拉股票
@analyst 做一份港股研究报告
@trader 执行QQQ期权策略
@researcher 研究AI行业趋势
```

### 方法 2：通过命令行
```bash
openclaw agents list          # 查看所有 agent
openclaw sessions_spawn --agent astra  # 启动 astra session
```

### 方法 3：路由配置（进阶）
可以配置消息自动路由到特定 agent。

---

## 协作流程

### 示例：完整的投资决策流程

```
1. 📊 analyst
   - 分析市场数据
   - 识别机会/风险
   
2. 🔍 researcher  
   - 深度调研目标公司
   - 评估基本面
   
3. 💼 astra
   - 制定投资策略
   - 配置资产组合
   
4. 🤖 trader
   - 执行交易
   - 风险管理
```

---

## Agent 技能

### astra（财富管理）
- ✅ Longbridge API 交易
- ✅ 全球市场分析
- ✅ EOF 投资策略
- ✅ 期权策略
- ✅ 投资组合管理

### analyst（数据分析）
- ✅ 股票分析 (stock-analysis skill)
- ✅ 财报分析
- ✅ 技术指标
- ✅ 实时行情

### trader（量化交易）
- ✅ Longbridge 订单执行
- ✅ 风险管理
- ✅ 策略回测
- ✅ 自动交易

### researcher（深度调研）
- ✅ 行业研究
- ✅ 公司尽调
- ✅ 竞争分析
- ✅ 趋势预测

---

## 记忆管理

每个 agent 有独立的记忆文件：
- `~/.openclaw/agents/{agent}/memory/YYYY-MM-DD.md`
- `~/.openclaw/agents/{agent}/MEMORY.md`

---

## 注意事项

1. **Agent 共享 skills** - 所有 agent 可以使用相同的 skill
2. **独立记忆** - 每个 agent 的记忆是独立的
3. **配置可定制** - 每个 agent 可以有不同的 model、技能配置
4. **路由规则** - 可以配置自动路由策略

---

## 下一步

1. **配置技能** - 为每个 agent 安装专门的 skills
2. **绑定渠道** - 配置自动路由
3. **测试协作** - 运行完整的协作流程
