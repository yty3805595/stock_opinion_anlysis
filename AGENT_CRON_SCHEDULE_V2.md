# 📅 Agent 定时汇报任务配置（更新版）

## 📊 数据来源配置

### A股数据
- **接口**: Tushare（skill: tushare-base）
- **优势**: 专为A股设计，数据全面、更新及时
- **安装**: `npx clawhub install tushare-base`

### 港股/美股数据
- **接口**: Longbridge API
- **支持**: 实时行情、订单交易、期权策略

---

## ⏰ 定时任务清单（GMT+8）

### 🌅 A股时段（09:30 - 15:00）

| 时间 | Agent | 任务 | 数据来源 |
|------|-------|------|---------|
| 09:30 | Astra | 开盘汇报 | Tushare (daily realtime) |
| 09:45 | Trader | 交易监控 | Tushare (realtime + moneyflow) |
| 10:00 | Analyst | 早盘分析 | Tushare (daily moneyflow) |
| 11:30 | Analyst | 午盘总结 | Tushare (daily) |
| 15:00 | Analyst | 收盘总结 | Tushare (daily) |

### 🌏 港股时段（09:30 - 16:00）

| 时间 | Agent | 任务 | 数据来源 |
|------|-------|------|---------|
| 09:30 | Astra | 开盘汇报 | Longbridge |
| 09:45 | Trader | 交易监控 | Longbridge |
| 16:00 | Analyst | 收盘总结 | Longbridge |

### 🌙 美股时段（21:30 - 04:00）

| 时间 | Agent | 任务 | 数据来源 |
|------|-------|------|---------|
| 21:00 | Astra | 盘前汇报 | Longbridge |
| 21:30 | Trader | 交易监控 | Longbridge |
| 22:30 | Analyst | 开盘分析 | Longbridge |
| 04:00 | Analyst | 收盘总结 | Longbridge |

### 📋 每周任务

| 时间 | Agent | 任务 | 数据来源 |
|------|-------|------|---------|
| 周一 10:00 | Researcher | 周度回顾 | Tushare + Longbridge |
| 周五 22:00 | Researcher | 周度总结 | Tushare + Longbridge |

---

## 🔧 Tushare 配置

### 1. 注册并获取 Token
```bash
# 访问 https://tushare.pro/register
# 注册账号并获取 API Token
```

### 2. 配置环境变量
```bash
# 编辑 ~/.zshrc
export TUSHARE_TOKEN="your-api-token"

# 生效配置
source ~/.zshrc
```

### 3. 安装依赖
```bash
pip3 install tushare pandas --user
```

### 4. 验证安装
```bash
python3 skills/tushare-base/scripts/market.py realtime 000001
```

---

## 📝 命令速查

### A股实时行情
```bash
python3 skills/tushare-base/scripts/market.py realtime 000001   # 平安银行
python3 skills/tushare-base/scripts/market.py realtime 600519   # 贵州茅台
python3 skills/tushare-base/scripts/market.py realtime 000001.SZ # 深交所
python3 skills/tushare-base/scripts/market.py realtime 600519.SH # 上交所
```

### A股日线数据
```bash
python3 skills/tushare-base/scripts/market.py daily --ts_code 000001.SZ
python3 skills/tushare-base/scripts/market.py daily --ts_code 600519.SH --start_date 20260201
```

### 资金流向
```bash
python3 skills/tushare-base/scripts/market.py moneyflow --ts_code 000001.SZ
python3 skills/tushare-base/scripts/market.py moneyflow --trade_date 20260213
```

---

## 📈 重点关注标的

### A股
- **上证指数**: 000001.SH
- **深证成指**: 399001.SZ
- **创业板指**: 399006.SZ
- **沪深300**: 000300.SH
- **中证500**: 000905.SH

### 港股
- **恒生指数**: HSI (Longbridge)
- **腾讯**: 0700.HK
- **阿里**: 9988.HK

### 美股
- **QQQ**: Invesco QQQ Trust
- **NVDA**: NVIDIA
- **TSLA**: Tesla
- **GOOGL**: Alphabet
- **MSFT**: Microsoft

---

## 🎯 Agent 协作流程

```
A股/港股数据 → Tushare API
          ↓
     Analyst Agent
          ↓
   初步分析 + 报告生成
          ↓
Astra/Trader Agent (制定策略)
Researcher Agent (深度调研)

美股数据 → Longbridge API
          ↓
   全员协作 (同A股流程)
```

---

## ⚠️ 注意事项

1. **Tushare 积分**: 部分接口需要积分才能使用
2. **数据延迟**: 实时行情可能有 1-3 秒延迟
3. **API 限制**: 注意请求频率限制
4. **交易时段**: A股仅在 09:30-15:00 提供数据
