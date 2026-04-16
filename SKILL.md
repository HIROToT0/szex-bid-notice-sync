---
name: szex-bid-notice-sync
description: 深圳交易集团招标公告抓取并同步到飞书多维表格。支持按工程类型/时间范围过滤、抓取详情字段（投标截止时间、招标估算等）、邮件通知。
metadata:
  platforms: [linux, openclaw]
  dependencies: [python3, curl, feishu-bitable]
  author: Bonbonon
  version: 1.0.0
---

# 深圳交易集团招标公告抓取与飞书同步

自动从深圳交易集团官网抓取招标公告，过滤后写入飞书多维表格，并支持邮件通知。

## 功能特性

- ✅ **列表抓取** — 调用深圳交易集团 API，按时间范围+工程类型过滤
- ✅ **详情补全** — 逐条抓取详情页，提取投标截止时间、招标估算、招标方式等字段
- ✅ **飞书写入** — 自动新增记录，支持去重（按公告名称判断）
- ✅ **字段管理** — 自动检测并创建缺失的表格字段
- ✅ **邮件通知** — 抓取完成后发送 HTML 邮件，标注投标截止时间
- ✅ **定时任务** — 可配置 OpenClaw cron 或系统 cron 每日自动执行

## 目录结构

```
szex-bid-notice-sync/
├── SKILL.md                          # 本文件（技能描述）
├── README.md                          # 详细使用文档
├── scripts/
│   ├── fetch_and_sync.py              # 核心抓取脚本
│   └── send_email.py                  # 邮件通知脚本
├── config/
│   ├── config.json.example             # 主配置模板
│   └── email.json.example             # 邮件配置模板
└── examples/
    └── sample_output.json             # 示例输出
```

## 快速开始

### 1. 复制配置文件

```bash
cd ~/.openclaw/workspace/skills/szex-bid-notice-sync
cp config/config.json.example config/config.json
cp config/email.json.example config/email.json   # 如需邮件通知
```

编辑 `config/config.json`，填写你的飞书多维表格信息：
- `app_token` — 多维表格的 App Token（`basxxx` 格式）
- `table_id` — 数据表的 Table ID（`tblxxx` 格式）

### 2. 修改多维表格

确保多维表格有以下字段（脚本会自动创建缺失字段）：
- `公告名称`（文本，主字段）
- `公告链接`（链接）
- `公告类型`（单选）
- `子类型`（单选）
- `工程类型`（单选）
- `发布时间`（日期）
- `投标截止时间`（日期）
- `招标概况`（文本）
- `抓取时间`（日期）
- `状态`（单选）
- `招标估算`（数字，可选）
- `招标方式`（单选，可选）
- `资格审查方式`（单选，可选）
- `递交方式`（单选，可选）

### 3. 运行脚本

```bash
cd ~/.openclaw/workspace/skills/szex-bid-notice-sync
python3 scripts/fetch_and_sync.py
```

## 配置说明

### 抓取配置 (config/config.json)

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `app_token` | 飞书多维表格 App Token | — |
| `table_id` | 数据表 ID | — |
| `days` | 抓取最近多少天的公告 | 7 |
| `project_types` | 工程类型白名单（空=全部） | `["其他"]` |
| `notice_types` | 公告类型白名单（空=全部） | `["招标公告"]` |
| `email_enabled` | 是否发送邮件通知 | false |

### 邮件配置 (config/email.json)

| 字段 | 说明 |
|------|------|
| `smtp_host` | SMTP 服务器地址 |
| `smtp_port` | SMTP 端口（QQ邮箱用 465） |
| `smtp_user` | 发件人邮箱 |
| `smtp_password` | SMTP 授权码（非登录密码） |
| `use_ssl` | 是否使用 SSL |
| `from_name` | 发件人显示名称 |
| `to_addresses` | 收件人列表 |
| `subject` | 邮件主题 |

## 定时任务设置

### 方案一：OpenClaw Cron（推荐）

在 OpenClaw 的 cron 配置中添加：

```bash
openclaw cron add \
  --name "深圳招标公告每日抓取" \
  --schedule "0 9 * * *" \
  --command "cd ~/.openclaw/workspace/skills/szex-bid-notice-sync && python3 scripts/fetch_and_sync.py && python3 scripts/send_email.py" \
  --channel feishu
```

### 方案二：系统 crontab

```bash
# 每天早上9点执行
0 9 * * * cd /home/bonbonon/.openclaw/workspace/skills/szex-bid-notice-sync && python3 scripts/fetch_and_sync.py >> /var/log/bid_sync.log 2>&1
```

## API 说明

### 深圳交易集团招标 API

**列表 API**：`POST https://www.szexgrp.com/cms/api/v1/trade/content/page`

关键筛选字段：
- `jygg_gglxmc_rank1` — 公告类型（招标公告、资审公示…）
- `jygg_gglx` — 公告子类型
- `jygg_gclx` — 工程类型（施工、监理、设计、勘察、货物、咨询、其他）
- `releaseTimeBegin / releaseTimeEnd` — 发布时间范围
- `modelId: 1378` — 建设工程 modelId
- `channelId: 2851` — 建设工程 channelId

**详情 API**：`GET https://www.szexgrp.com/cms/api/v1/trade/content/detail?contentId={id}&channelId=2851`

详情 HTML 中的字段：
- `投标文件递交截止时间` — 投标截止时间
- `本次发包工程估价` — 招标估算（万元）
- `公开招标 / 邀请招标` — 招标方式
- `资格后审 / 资格预审` — 资格审查方式
- `线上递交 / 线下递交` — 递交方式

### 飞书多维表格 API

凭证：自动从 `~/.openclaw/openclaw.json` 读取 `channels.feishu.accounts.main.appId/appSecret`

Base URL: `https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}`

## 常见问题

**Q: 公告链接点进去显示的不是正确内容？**
A: 部分小型建设工程项目没有 bidSectionNumber，需使用 `details.html?contentId=...&channelId=2851&crumb=jsgc` 格式。详情页为 JS 动态渲染，web_fetch 无法直接读取。

**Q: 邮件发送失败？**
A: 确认 SMTP 授权码是否正确（不是登录密码）。QQ 邮箱需在设置→账户中开启 POP3/SMTP 并获取授权码。

**Q: 如何只抓特定工程类型？**
A: 修改 `config/config.json` 中的 `project_types`，例如 `["施工", "监理"]`

**Q: 已有记录被重复写入？**
A: 脚本按"公告名称"去重，已存在的记录不会重复写入。
