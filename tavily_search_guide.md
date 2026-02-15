# 📚 Tavily Search 使用指南

**创建时间**: 2026-02-15  
**API Key**: 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

---

## 🎯 简介

**Tavily** 是一个专为 AI 优化的搜索引擎，可以快速获取相关且简洁的搜索结果。

---

## 🔧 安装和使用

### 1. 安装 Skill

```bash
npx clawhub install tavily-search
```

### 2. 设置 API Key

```bash
export TAVILY_API_KEY="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"
```

### 3. 基本搜索

```bash
# 基础搜索（返回5条结果）
node scripts/search.mjs "查询内容"

# 指定结果数量
node scripts/search.mjs "查询内容" -n 10

# 深度搜索（更全面但更慢）
node scripts/search.mjs "查询内容" --deep

# 新闻搜索
node scripts/search.mjs "查询内容" --topic news

# 搜索最近7天的新闻
node scripts/search.mjs "查询内容" --topic news --days 7
```

### 4. 提取网页内容

```bash
# 提取 URL 内容
node scripts/extract.mjs "https://example.com/article"
```

---

## 📊 使用示例

### 搜索 Polymarket 教程

```bash
node scripts/search.mjs "Polymarket 教程"
```

**结果**:
- Polymarket 预测市场项目解读
- YouTube 视频教程
- 官方文档
- 空投教程

---

### 搜索 A股选股策略

```bash
node scripts/search.mjs "A股三维选股策略" --deep
```

**结果**:
- 华安事件驱动量化策略（三维一体框架）
- BigQuant 量化交易选股模板
- 海龟策略
- 上证50量化选股和择时

---

### 搜索最新新闻

```bash
node scripts/search.mjs "Polymarket 入金 USDC" --topic news --days 30
```

**结果**:
- Polymarket 与 Circle 合作，使用 USDC 结算
- Polymarket 重返美国市场
- 预测市场相关新闻

---

## 🎯 应用场景

### 1. 市场研究

```bash
# 搜索投资策略
node scripts/search.mjs "价值投资 选股策略"

# 搜索行业分析
node scripts/search.mjs "新能源 板块分析 2026"

# 搜索宏观经济
node scripts/search.mjs "美联储 利率决议 影响"
```

### 2. 交易工具

```bash
# 搜索交易平台
node scripts/search.mjs "Polymarket 教程 入金"

# 搜索套利机会
node scripts/search.mjs "加密货币 套利 策略"

# 搜索风险管理
node scripts/search.mjs "投资组合 风险控制 策略"
```

### 3. 学习资源

```bash
# 搜索量化交易
node scripts/search.mjs "量化交易 Python 教程"

# 搜索数据分析
node scripts/search.mjs "数据分析 可视化 工具"

# 搜索机器学习
node scripts/search.mjs "机器学习 股票预测"
```

---

## 📝 最佳实践

### 1. 搜索技巧

- **使用具体关键词**: "Polymarket 入金教程" 比 "Polymarket" 更好
- **使用引号精确匹配**: "三维选股策略"
- **组合关键词**: "A股 选股 量化 策略"

### 2. 选择搜索模式

| 场景 | 推荐命令 |
|------|----------|
| 快速查找 | 基础搜索 |
| 深度研究 | `--deep` |
| 时事新闻 | `--topic news` |
| 最新动态 | `--topic news --days 7` |

### 3. 结果处理

1. **快速浏览**: 查看标题和摘要
2. **深度阅读**: 使用 `extract.mjs` 获取详细内容
3. **保存记录**: 将重要信息保存到文档

---

## 💡 实际应用案例

### 案例 1: 研究 Polymarket 入金

```bash
# 搜索
node scripts/search.mjs "Polymarket 入金 USDC 教程"

# 提取详细内容
node scripts/extract.mjs "https://docs.polymarket.com/"
```

### 案例 2: 学习 A股选股

```bash
# 搜索选股策略
node scripts/search.mjs "A股选股 三维 量化策略" --deep

# 获取PDF报告
node scripts/extract.mjs "https://pdf.dfcfw.com/pdf/H301_AP202502141643079868_1.pdf"
```

### 案例 3: 追踪市场动态

```bash
# 搜索最新新闻
node scripts/search.mjs "美联储 利率 决议" --topic news --days 7

# 搜索加密货币
node scripts/search.mjs "BTC 价格预测 2026" --topic news --days 14
```

---

## 🔗 相关链接

- **官网**: https://tavily.com
- **文档**: https://docs.tavily.com
- **API Key**: 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

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `scripts/travily_search.py` | Python 封装脚本 |
| `skills/tavily-search/` | Tavily Search Skill |
| `github_reports/*.md` | 分析报告 |

---

## 🎯 后续应用

1. **自动监控**: 定时搜索市场动态
2. **研究助手**: 快速获取投资相关信息
3. **学习工具**: 搜索教程和学习资源
4. **新闻追踪**: 追踪特定主题的最新消息

---

*由 Agent Team 自动生成*
