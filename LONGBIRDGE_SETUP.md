# 📝 长桥 API 配置指南

**创建时间**: 2026-02-17

---

## 🎯 快速配置 (3步)

### Step 1: 注册长桥账户

1. 访问: https://longbridge.global/
2. 完成注册 (需要手机号)
3. 完成实名认证 (上传身份证)

### Step 2: 创建 API Key

1. 登录长桥账户
2. 进入「账户」→「API 管理」
3. 点击「创建 API Key」
4. 选择权限:
   - ✅ 市场行情 (Quote)
   - ✅ 交易执行 (Trade)
   - ✅ 账户信息 (Account)
5. **复制 App Key 和 App Secret** (注意: Secret 只显示一次!)

### Step 3: 设置环境变量

```bash
# 临时设置 (当前终端)
export LONGBRIDGE_APP_KEY="你的App Key"
export LONGBRIDGE_APP_SECRET="你的App Secret"

# 永久设置 (添加到 ~/.zshrc)
echo 'export LONGBRIDGE_APP_KEY="你的App Key"' >> ~/.zshrc
echo 'export LONGBRIDGE_APP_SECRET="你的App Secret"' >> ~/.zshrc
source ~/.zshrc
```

### Step 4: 测试配置

```bash
cd /Users/yintaoye/.openclaw/workspace
python3 scripts/test_longbridge.py
```

---

## 🔧 高级配置

### 创建配置文件

```bash
# 保存到项目根目录
cat > .env << EOF
LONGBRIDGE_APP_KEY=你的App Key
LONGBRIDGE_APP_SECRET=你的App Secret
EOF
```

### 验证配置

```bash
# 检查环境变量
echo $LONGBRIDGE_APP_KEY
echo $LONGBRIDGE_APP_SECRET

# 运行测试
python scripts/test_longbridge.py
```

---

## 📋 常见问题

### Q1: API Key 在哪里创建?

A: 登录后 → 账户 → API 管理 → 创建 API Key

### Q2: App Secret 丢失怎么办?

A: 重新创建新的 API Key (Secret 只显示一次)

### Q3: 连接失败怎么办?

1. 检查环境变量是否设置: `echo $LONGBRIDGE_APP_KEY`
2. 检查网络连接
3. 检查 API Key 权限是否足够

### Q4: 权限不够怎么办?

A: 删除旧 Key，创建新 Key，选择完整权限

### Q5: 如何获取真实行情?

A: 需要开通账户权限，具体咨询长桥客服

---

## 🚀 配置成功后

修改交易系统配置:

```yaml
# config/trading_config.yaml

execution:
  broker: longbridge
  paper_trading: false  # 设为 false 使用实盘
  auto_trading: false    # 设为 true 自动执行
```

运行交易系统:

```bash
# 仅生成信号
python scripts/main_trading_system.py --mode signal

# 完整流程 (信号 + 执行)
python scripts/main_trading_system.py --mode full
```

---

## ⚠️ 注意事项

1. **安全保存**: App Secret 只显示一次，请立即保存
2. **权限设置**: 需要 "交易" 权限才能执行订单
3. **实盘风险**: 设置 `paper_trading: false` 前请确保已测试
4. **资金安全**: 建议先用小资金测试

---

## 📞 获取帮助

- 长桥官网: https://longbridge.global/
- 客服邮箱: support@longbridge.global
- API 文档: https://longbridge.global/docs

---

*祝配置顺利! 🎉*
