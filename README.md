# 深圳交易集团招标公告抓取与结果推送

## 一、问题背景

需要每天监控深圳交易集团官网的招标公告，尤其是"工程类型=其他，关键词为检测、监测、鉴定"的检测类项目。

**痛点：**
- 官网每天更新几十条公告，人工筛选费时费力
- 公告分散，点击每个详情页查看费时
- 无法及时获知新增公告

## 二、解决方案

用 OpenClaw + 飞书多维表格 + 定时任务，实现：

```
深圳交易集团官网
       ↓（API抓取）
  Python 脚本处理
       ↓（飞书API）
  飞书多维表格
       ↓（可选-邮件通知）
  指定人员邮箱
```

## 三、完整配置步骤

### 步骤 1：确认飞书应用权限

1. 打开 [飞书开放平台](https://open.feishu.cn/app/cli_a94cf77bd73bdccf/auth)
2. 权限管理 → 开通以下权限：
   - `bitable:app` 或 `bitable:app:readonly`
   - `bitable:record:write`（写入需要）
   - `drive:drive`
3. 发布应用

### 步骤 2：配置多维表格协作者

1. 打开目标多维表格
2. 右上角「···」→「分享」
3. 搜索并添加你的应用名（`飞书bot名字`），给予**编辑**权限

### 步骤 3：确认多维表格字段

表格字段应包含（或脚本自动创建）：
- `公告名称`（文本，主字段）
- `公告链接`（链接）
- `公告类型`（单选：招标公告、答疑、补遗、截标信息…）
- `子类型`（单选）
- `工程类型`（单选：施工、监理、勘察…）
- `发布时间`（日期）
- `投标截止时间`（日期）
- `招标概况`（文本）
- `抓取时间`（日期）
- `状态`（单选）
- `招标估算`（数字，可选）
- `招标方式`（单选，可选）
- `资格审查方式`（单选，可选）
- `递交方式`（单选，可选）

### 步骤 4：配置脚本

```bash
cd ~/.openclaw/workspace/skills/szex-bid-notice-sync
cp config/config.json.example config/config.json
# 编辑 config/config.json 填写 app_token 和 table_id

cp config/email.json.example config/email.json
# 如需邮件通知，编辑 config/email.json 填写 SMTP 信息
```

### 步骤 5：测试运行

```bash
python3 scripts/fetch_and_sync.py
```

正常输出：
```
📡 开始抓取: 2026-04-09 ~ 2026-04-16
   工程类型: ['其他']
   API返回总数: 9
   新增记录: 3 条
  [20302651] xxx
    ✅ 写入成功
==================================================
✅ 完成！新增 3/3 条记录
```

发送邮件（如启用）：
```
✅ 邮件发送成功
```

## 四、定时任务设置

### 方式一：OpenClaw 内置 Cron（推荐）

注册每日定时任务：

```bash
openclaw cron add \
  --name "深圳招标公告每日抓取" \
  --schedule "0 9 * * *" \
  --command "python3 /home/bonbonon/.openclaw/workspace/skills/szex-bid-notice-sync/scripts/fetch_and_sync.py && python3 /home/bonbonon/.openclaw/workspace/skills/szex-bid-notice-sync/scripts/send_email.py"
```

`--schedule "0 9 * * *"` = 每天 09:00 执行，可修改为其他时间。

### 方式二：系统 Crontab

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天早上9点执行）
0 9 * * * cd /home/bonbonon/.openclaw/workspace/skills/szex-bid-notice-sync && python3 scripts/fetch_and_sync.py >> /tmp/bid_sync.log 2>&1
```

### 方式三：手动触发

随时对主公说："执行招标公告抓取"，我可以立即运行脚本。

## 五、飞书表格自动化邮件

飞书多维表格有内置自动化能力，可以实现"有新记录时自动发邮件"：

1. 打开飞书多维表格
2. 点击右上角「···」→「自动化」→「添加自动化」
3. 选择触发条件：「当有记录满足条件时」
4. 条件：`创建时间` `是今天`
5. 添加操作：「发送邮件」→ 填写收件人、主题、邮件内容
6. 保存

这种方式**不需要写代码**，且完全在飞书内完成。

## 六、字段说明

| 字段 | 类型 | 说明 | 备注 |
|------|------|------|------|
| 公告名称 | 文本 | 公告标题 | 来自列表API |
| 公告链接 | 链接 | 详情页URL | `details.html`格式 |
| 公告类型 | 单选 | 招标公告/答疑补遗/截标信息等 | |
| 子类型 | 单选 | rank1分类 | |
| 工程类型 | 单选 | 施工/监理/勘察/其他等 | 来自API `projectType` |
| 发布时间 | 日期 | 公告发布时间 | 毫秒时间戳 |
| 投标截止时间 | 日期 | 投标文件递交截止时间 | 详情页HTML解析 |
| 招标概况 | 文本 | 本次招标内容摘要 | 详情页HTML解析 |
| 抓取时间 | 日期 | 数据抓取时间 | |
| 状态 | 单选 | 留空或手动标记 | |
| 招标估算 | 数字 | 发包工程估价（万元） | 详情页解析 |
| 招标方式 | 单选 | 公开招标/邀请招标 | |
| 资格审查方式 | 单选 | 资格后审/资格预审 | |
| 递交方式 | 单选 | 线上递交/线下递交 | |

## 七、API 参数参考

深圳交易集团 API 调用参数：

```
POST https://www.szexgrp.com/cms/api/v1/trade/content/page
{
    "modelId": 1378,              # 建设工程 modelId
    "channelId": 2851,             # 建设工程 channelId
    "fields": [
        {"fieldName": "jygg_gglxmc_rank1", "fieldValue": "招标公告"}
    ],
    "releaseTimeBegin": "2026-04-09",
    "releaseTimeEnd": "2026-04-16",
    "page": 0,
    "size": 50
}
```

筛选条件（jygg_gclx）可选值：`施工`、`监理`、`勘察`、`设计`、`可研`、`货物`、`物业`、`其他`
