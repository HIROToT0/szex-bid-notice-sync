# 深圳交易集团招标公告抓取系统

从深圳交易集团官网抓取招标公告，同步到飞书多维表格，并支持邮件通知。

## 功能特性

- 自动抓取深圳交易集团招标公告
- 过滤检测/监测/鉴定等关键词相关公告
- 同步到飞书多维表格（含公告名称、链接、类型、投标截止时间等字段）
- 匹配关键词的新增公告发送邮件通知

## 目录结构

```
szex-bid-notice-sync/
├── config/
│   ├── config.json       # 主配置（飞书多维表格、关键词等）
│   └── email.json        # 邮件发送配置
├── scripts/
│   ├── fetch_and_sync.py # 抓取 + 同步到飞书
│   └── send_email.py    # 邮件通知脚本
```

## 配置说明

### config.json

```json
{
    "app_token": "飞书多维表格AppToken",
    "table_id": "数据表ID",
    "days": 3,
    "notice_types": ["招标公告"],
    "project_types": ["其他"],
    "keywords": ["检测", "监测", "鉴定", "排查", "巡查"],
    "email_enabled": true
}
```

### email.json

```json
{
    "smtp_host": "smtp.example.com",
    "smtp_port": 465,
    "smtp_user": "your@email.com",
    "smtp_password": "your_password",
    "use_ssl": true,
    "from_name": "OpenClaw招标公告系统",
    "to_addresses": ["recipient@example.com"],
    "subject": "【招标公告】每日更新提醒"
}
```

## 使用方式

```bash
# 抓取并同步到飞书
python3 scripts/fetch_and_sync.py

# 发送邮件通知
python3 scripts/send_email.py
```

## 定时任务

建议使用 cron 每日定时执行：

```cron
0 9 * * * cd /path/to/szex-bid-notice-sync && python3 scripts/fetch_and_sync.py && python3 scripts/send_email.py
```
