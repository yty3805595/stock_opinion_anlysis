---
name: chromium-browser
description: 网页浏览、解析和自动化控制能力。用于访问和分析网页内容，支持截图、提取文本、表单交互等。触发场景：用户要求查看网页、解析网页内容、自动化网页操作。
---

# Chromium Browser

网页浏览器控制能力，基于 OpenClaw 的 browser 工具实现。

## 快速开始

使用 `browser` 工具前，确保 gateway 正在运行：

```bash
openclaw gateway start
```

### Chrome 扩展连接（必需）

gateway 启动后，需要连接 Chrome 扩展到一个标签页：

1. 在 Chrome 浏览器中打开任意标签页
2. 点击 OpenClaw Chrome 扩展图标（工具栏）
3. 确保状态显示 "ON" 或 "Connected"

## 常用操作

### 访问网页
```json
{
  "action": "navigate",
  "targetUrl": "https://example.com"
}
```

### 获取页面快照
```json
{
  "action": "snapshot",
  "compact": true
}
```

### 页面交互
```json
{
  "action": "act",
  "request": {
    "kind": "click",
    "ref": "element-ref"
  }
}
```

### 截图
```json
{
  "action": "screenshot"
}
```

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| gateway 未运行 | 运行 `openclaw gateway start` |
| 扩展未连接 | 点击 Chrome 扩展图标，确保连接 |
| 无法访问网站 | 检查网络连接，尝试使用 HTTPS |

## Profiles

- `profile: "chrome"` — 使用已安装的 Chrome 浏览器（推荐）
- `profile: "openclaw"` — 使用 OpenClaw 管理的隔离浏览器

## 注意事项

- 页面加载需要时间，使用 `timeoutMs` 调整等待时间
- 复杂的交互可能需要多次操作
- 部分动态网站可能需要 JavaScript 执行支持
