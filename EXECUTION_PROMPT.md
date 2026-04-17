# 深圳交易集团招标公告抓取与飞书同步 — 执行提示词

## 任务概述

从**深圳公共资源交易集团**官网抓取招标公告，过滤后写入**飞书多维表格**。
每天凌晨 3:00 自动运行（可通过 cron 手动触发测试）。

---

## 一、信息资产

### 目标网站
- 网页入口：https://www.szexgrp.com/jyfw/jsgc-view.html?id=jsgc
- 列表 API：`POST https://www.szexgrp.com/cms/api/v1/trade/content/page`
- 详情 API：`GET https://www.szexgrp.com/cms/api/v1/trade/content/detail?contentId={contentId}&channelId=2851`

### 飞书应用凭证
| 字段 | 值 |
|------|-----|
| App ID | `cli_a920358585225bd1` |
| App Secret | `Fteb38eMhHsdA1EhxMmfah86bjGa8Nmj` |
| Token API | `https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal` |

### 目标多维表格
| 字段 | 值 |
|------|-----|
| App Token | `RG7lbqlijaY5WZs78QpcM6NjnZj` |
| Table ID | `tblkYHpGG8V6IO2h` |
| 表格 URL | https://ccnlg9zq6b6x.feishu.cn/base/RG7lbqlijaY5WZs78QpcM6NjnZj |

---

## 二、API 调用规范

### 列表 API
```
POST https://www.szexgrp.com/cms/api/v1/trade/content/page
Content-Type: application/json
User-Agent: Mozilla/5.0

{
  "modelId": 1378,
  "channelId": 2851,
  "fields": [{"fieldName": "jygg_gglx", "fieldValue": "招标公告"}],
  "releaseTimeBegin": "<YYYY-MM-DD>",
  "releaseTimeEnd": "<YYYY-MM-DD>",
  "page": <N>,
  "size": 50
}
```

**响应关键字段：**
- `data.content[]`：公告列表，每条含 `id`（contentId）、`title`、`noticeTypeName`、`projectType`、`rank1NoticeTypeName`
- `data.totalElements`：总数

### 详情 API
```
GET https://www.szexgrp.com/cms/api/v1/trade/content/detail?contentId={contentId}&channelId=2851
User-Agent: Mozilla/5.0
```

**响应结构：**
- `data.attrs[]`：键值对数组，`attrName` + `attrValue`
- `data.txt`：HTML 正文（用于正则提取补充字段）

---

## 三、抓取规则（每次执行时使用）

| 条件 | 值 |
|------|-----|
| 发布时间范围 | **近 3 天**（含当天）|
| 公告类型过滤 | `jygg_gglx = 招标公告` |
| 标题关键词过滤 | **必须包含** `检测` 或 `监测` 或 `鉴定`（三选一）|
| 去重依据 | 按「公告名称」去重，已存在的不重复写入 |

**API 请求逻辑：**
1. 分页抓取所有招标公告（每页 50 条，不断翻页直到取完）
2. 用标题关键词过滤
3. 比对飞书表格中已有「公告名称」，排除重复
4. 剩余为新增记录，逐条调用详情 API 补全字段后再写入

---

## 四、飞书多维表格字段（共 14 个）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| 公告名称 | 文本 | 主字段，API `title` |
| 公告链接 | 链接 | `https://www.szexgrp.com/jyfw/details.html?contentId={id}&channelId=2851&crumb=jsgc` |
| 公告类型 | 单选 | 固定「招标公告」 |
| 子类型 | 单选 | API `rank1NoticeTypeName` 或 `noticeTypeName` |
| 工程类型 | 单选 | API `projectType` |
| 发布时间 | 日期 | API `jygg_ggfbsj`（毫秒时间戳） |
| 投标截止时间 | 日期 | 优先从 HTML 正则提取，其次用 `jygg_ggjssj` |
| 招标概况 | 文本 | 从 HTML 正则提取「本次招标内容」 |
| 抓取时间 | 日期 | 当前时间毫秒时间戳 |
| 状态 | 单选 | 空 |
| 招标估算 | 数字 | 从 HTML 正则 `本次发包工程估价.*?(\d+\.?\d*)\s*万元` |
| 招标方式 | 单选 | HTML 含「公开招标」→ 公开招标；含「邀请招标」→ 邀请招标 |
| 资格审查方式 | 单选 | HTML 含「资格后审」→ 资格后审；含「资格预审」→ 资格预审 |
| 递交方式 | 单选 | HTML 含「线上递交」→ 线上递交；含「线下递交」→ 线下递交 |

**时间戳解析规则：**
- 优先用 `attrs["jygg_ggfbsj"]`（数字，毫秒级时间戳，如 `1776242400000`）
- 次选 `attrs["jygg_ggjssj"]`
- 再次从 HTML 正则提取，格式 `YYYY-MM-DD HH:MM`

**HTML 正则提取投标截止时间（按顺序尝试）：**
```
投标文件递交截止时间.*?(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})
递交投标文件截止时间.*?(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})
截标时间.*?(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})
投标截止时间.*?(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})
```

---

## 五、Python 脚本

**路径：** `/vol2/@apphome/trim.openclaw/data/workspace/skills/szex-bid-notice-sync/scripts/fetch_and_sync.py`

**调用方式：**
```bash
python3 /vol2/@apphome/trim.openclaw/data/workspace/skills/szex-bid-notice-sync/scripts/fetch_and_sync.py
```

**配置（config/config.json）：**
```json
{
  "app_token": "RG7lbqlijaY5WZs78QpcM6NjnZj",
  "table_id": "tblkYHpGG8V6IO2h",
  "days": 3,
  "keywords": ["检测", "监测", "鉴定"]
}
```

**脚本核心逻辑：**
1. 读取飞书应用凭证（从 `~/.openclaw/openclaw.json` 的 `channels.feishu.accounts.main.appId/appSecret`）
2. 获取 tenant_access_token
3. 计算时间范围（今天 − 3 天 ~ 今天）
4. 分页抓取招标公告列表
5. 标题含关键词则进入候选
6. 读取表格已有记录，按「公告名称」去重
7. 剩余记录逐条调用详情 API 补全字段
8. 批量写入飞书表格
9. 输出：新增记录数 + 每条摘要（ID、名称、发布时间、投标截止、招标估算）

---

## 六、定时任务（Cron）

| 字段 | 值 |
|------|-----|
| Job ID | `szex-bid-notice-daily` |
| Schedule | `0 3 * * *`（每天凌晨 3:00） |
| Timezone | `Asia/Shanghai` |
| Session 模式 | `isolated` |
| 触发方式 | cron 触发 isolated session，session 收到 message 后执行脚本并回复结果 |

**Cron Jobs 文件：** `~/.openclaw/cron/jobs.json`

---

## 七、输出规范（每次执行后）

脚本执行完毕后，**必须**在飞书发送一条消息，格式如下：

- **无新增时：**「✅ 抓取完成，近 3 天无新增招标公告。」
- **有新增时：**「✅ 抓取完成，新增 {N} 条招标公告：\n- {公告名称1}（发布时间 | 投标截止）\n- {公告名称2}（发布时间 | 投标截止）\n...」

---

## 八、权限要求

- 飞书应用需开通权限：`drive:drive`（云文档读写）
- 应用需被授予目标多维表格的**编辑权限**
- 开通后需在飞书开放平台**重新发布**应用使权限生效

---

## 九、常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 飞书 API 返回 99991672 | 缺少 `drive:drive` 权限 | 在开放平台开通并重新发布应用 |
| API 返回为空 | `fields` 参数未传或格式错误 | 必须传 `fields: [{"fieldName": "jygg_gglx", "fieldValue": "招标公告"}]` |
| 详情页字段为空 | `jygg_ggjssj` 为 null | 改用 HTML 正则提取投标截止时间 |
| 投标估算为 0 | 正则未匹配到 | 检查 HTML 中「本次发包工程估价」格式 |
| 写入失败 | 表格字段类型不匹配 | 确认字段类型：日期→时间戳，数字→float，链接→`{link, text}` 对象 |
| 重复写入 | 去重逻辑失效 | 检查表格「公告名称」字段是否完整，去重按 title 而非 id |

---

## 十、交付检查清单

- [ ] API 能正常返回招标公告列表
- [ ] 标题关键词过滤正确（只保留含检测/监测/鉴定的）
- [ ] 去重逻辑有效（已有名单不会重复写入）
- [ ] 详情字段完整（发布时间、投标截止、招标估算、招标方式、资格审查方式、递交方式）
- [ ] 写入飞书后表格显示正常
- [ ] cron 任务能正常触发并发送飞书消息
