#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深圳交易集团招标公告抓取 + 飞书多维表格同步脚本
功能：从深圳交易集团官网抓取招标公告，写入飞书多维表格
依赖：Python 3.8+, requests, 飞书应用凭证
"""

import json, subprocess, re, time, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.json"
CHANNELS_FEISHU_PATH = Path.home() / ".openclaw" / "openclaw.json"

# ======================== 飞书凭证获取 ========================
def get_feishu_creds():
    """从 openclaw.json 读取飞书应用凭证"""
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    with open(config_path) as f:
        config = json.load(f)
    feishu_cfg = config.get("channels", {}).get("feishu", {})
    accounts = feishu_cfg.get("accounts", {})
    main_acc = accounts.get("main", accounts.get("default", {}))
    return main_acc.get("appId"), main_acc.get("appSecret")

# ======================== 飞书 API 工具 ========================
def get_tenant_token(app_id, app_secret):
    r = subprocess.run([
        "curl", "-s", "-X", "POST",
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"app_id": app_id, "app_secret": app_secret})
    ], capture_output=True, text=True)
    return json.loads(r.stdout)["tenant_access_token"]

def bitable_api(method, path, token, data=None):
    """通用飞书多维表格 API 调用"""
    cmd = [
        "curl", "-s", "-X", method,
        f"https://open.feishu.cn/open-apis{path}",
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json"
    ]
    if data:
        cmd += ["-d", json.dumps(data)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout)

def ensure_fields(token, app_token, table_id, fields_config):
    """确保表格有所需字段，不存在则创建"""
    result = bitable_api("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields", token)
    existing = {f["field_name"]: f["field_id"] for f in result.get("data", {}).get("items", [])}

    for fname, ftype in fields_config.items():
        if fname not in existing:
            payload = {"field_name": fname, "type": ftype}
            # 单选类型需要 options
            if ftype == 3:
                payload["property"] = {"options": []}
            bitable_api("POST", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields", token, payload)
            print(f"  + 新增字段: {fname}")

def batch_create_records(token, app_token, table_id, records):
    """批量新增记录"""
    results = []
    for rec in records:
        r = bitable_api("POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            token, {"fields": rec})
        results.append({"code": r.get("code"), "msg": r.get("msg"), "record_id": r.get("data", {}).get("record_id", "")})
        time.sleep(0.3)
    return results

# ======================== 深圳交易集团 API ========================
def fetch_list(params):
    """调用深圳交易集团列表 API"""
    r = subprocess.run([
        "curl", "-s", "-X", "POST",
        "https://www.szexgrp.com/cms/api/v1/trade/content/page",
        "-H", "Content-Type: application/json",
        "-H", "User-Agent: Mozilla/5.0",
        "-d", json.dumps(params)
    ], capture_output=True, text=True)
    return json.loads(r.stdout)

def fetch_detail(content_id, channel_id=2851):
    """调用深圳交易集团详情 API"""
    r = subprocess.run([
        "curl", "-s",
        f"https://www.szexgrp.com/cms/api/v1/trade/content/detail?contentId={content_id}&channelId={channel_id}",
        "-H", "User-Agent: Mozilla/5.0"
    ], capture_output=True, text=True)
    return json.loads(r.stdout)

# ======================== 数据提取 ========================
def parse_datetime(dt_str):
    """将 '2026-04-20 18:00' 转为毫秒时间戳"""
    if not dt_str:
        return None
    dt_str = dt_str.strip()
    fmt = "%Y-%m-%d %H:%M"
    if len(dt_str) <= 10:
        fmt = "%Y-%m-%d"
    dt = datetime.strptime(dt_str, fmt)
    dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
    return int(dt.timestamp() * 1000)

def extract_fields_from_detail(content_id):
    """从详情 API + HTML 中提取各字段"""
    data = fetch_detail(content_id)
    if data.get("code") != 200:
        return {}

    attrs = {a["attrName"]: a["attrValue"] for a in data["data"].get("attrs", [])}
    html = data["data"].get("txt", "")
    fields = {}

    # 投标截止时间（优先从 HTML 提取，备选 API 字段）
    patterns = [
        r'投标文件递交截止时间.*?(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})',
        r'递交投标文件截止时间.*?(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})',
        r'截标时间.*?(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})',
    ]
    for p in patterns:
        m = re.search(p, html)
        if m:
            fields["投标截止时间"] = parse_datetime(m.group(1))
            break
    if "投标截止时间" not in fields and attrs.get("jygg_ggjssj"):
        fields["投标截止时间"] = attrs["jygg_ggjssj"]

    # 招标估算
    m = re.search(r'本次发包工程估价.*?(\d+\.?\d*)\s*万元', html)
    if m:
        fields["招标估算"] = float(m.group(1))

    # 招标方式
    if '公开招标' in html:
        fields["招标方式"] = '公开招标'
    elif '邀请招标' in html:
        fields["招标方式"] = '邀请招标'

    # 资格审查方式
    if '资格后审' in html:
        fields["资格审查方式"] = '资格后审'
    elif '资格预审' in html:
        fields["资格审查方式"] = '资格预审'

    # 递交方式
    if '线上递交' in html:
        fields["递交方式"] = '线上递交'
    elif '线下递交' in html:
        fields["递交方式"] = '线下递交'

    # 招标概况
    desc_match = re.search(r'本次招标内容.*?<div>(.*?)</div>', html, re.DOTALL)
    if desc_match:
        desc = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()
        fields["招标概况"] = re.sub(r'\s+', ' ', desc)[:500]

    # 发布时间
    if attrs.get("jygg_ggfbsj"):
        fields["发布时间"] = attrs["jygg_ggfbsj"]

    return fields

# ======================== 主流程 ========================
def main():
    app_id, app_secret = get_feishu_creds()
    if not app_id or not app_secret:
        print("❌ 未找到飞书凭证，请检查 ~/.openclaw/openclaw.json 配置")
        sys.exit(1)

    # 加载配置文件
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    else:
        cfg = {
            "app_token": "你的多维表格AppToken",
            "table_id": "你的数据表ID",
            "days": 7,  # 抓取最近N天
            "notice_types": ["招标公告"],  # 要抓取的公告类型
            "project_types": ["其他"],  # 要抓取的工程类型
        }
        print(f"⚠️  未找到配置文件，使用默认配置。请创建 {CONFIG_PATH}")
        print(f"    复制 config/config.json.example 为 config/config.json 并填写实际值")

    app_token = cfg.get("app_token") or "EUv3bCWIMaWUP3sEcEbcgKq8nsg"
    table_id = cfg.get("table_id") or "tbldyqeXNF0py3HN"
    days = cfg.get("days", 7)
    project_types = cfg.get("project_types", ["其他"])

    token = get_tenant_token(app_id, app_secret)

    # 确保表格有所需字段
    ensure_fields(token, app_token, table_id, {
        "公告名称": 1,       # 文本
        "公告链接": 15,      # 链接
        "公告类型": 3,       # 单选
        "子类型": 3,         # 单选
        "工程类型": 3,       # 单选
        "发布时间": 5,       # 日期
        "投标截止时间": 5,   # 日期
        "招标概况": 1,       # 文本
        "抓取时间": 5,       # 日期
        "状态": 3,           # 单选
        "招标估算": 2,       # 数字
        "招标方式": 3,        # 单选
        "资格审查方式": 3,    # 单选
        "递交方式": 3,        # 单选
    })

    # 计算时间范围
    now = datetime.now(timezone(timedelta(hours=8)))
    end_date = now.strftime("%Y-%m-%d")
    begin_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")

    # 获取已有记录（去重）
    existing = bitable_api("GET",
        f"/bitable/v1/apps/{app_token}/tables/{table_id}/records?page_size=500",
        token)
    existing_ids = set()
    for rec in existing.get("data", {}).get("items", []):
        name = rec.get("fields", {}).get("公告名称", "")
        if name:
            existing_ids.add(name)

    # 抓取列表
    print(f"\n📡 开始抓取: {begin_date} ~ {end_date}")
    print(f"   工程类型: {project_types}")

    list_params = {
        "modelId": 1378,
        "channelId": 2851,
        "fields": [
            {"fieldName": "jygg_gglx", "fieldValue": "招标公告"},
            {"fieldName": "jygg_gclx", "fieldValue": "其他"},
        ],
        "releaseTimeBegin": begin_date,
        "releaseTimeEnd": end_date,
        "page": 0,
        "size": 50
    }

    list_data = fetch_list(list_params)
    all_items = list_data.get("data", {}).get("content", [])
    total = list_data.get("data", {}).get("totalElements", 0)
    print(f"   API返回总数: {total}，本次获取: {len(all_items)}")

    # 按工程类型过滤
    if project_types:
        all_items = [i for i in all_items if i.get("projectType") in project_types]
        print(f"   工程类型过滤后: {len(all_items)} 条")

    # 去重已存在的
    new_items = [i for i in all_items if i.get("title") not in existing_ids]
    print(f"   新增记录: {len(new_items)} 条")

    if not new_items:
        print("\n✅ 没有新增记录，任务结束")
        return

    # 逐条抓详情并写入
    now_ts = int(datetime.now(timezone(timedelta(hours=8))).timestamp() * 1000)
    success_count = 0

    for item in new_items:
        cid = item["id"]
        title = item.get("title", "")
        notice_type = item.get("noticeTypeName", "招标公告")
        project_region = item.get("projectRegion", "")
        trade_type = item.get("tradeType", "")
        print(f"\n  [{cid}] {title[:50]}")

        # 提取详情字段
        detail_fields = extract_fields_from_detail(cid)
        detail_fields["公告名称"] = title
        detail_fields["公告类型"] = notice_type
        detail_fields["子类型"] = item.get("rank1NoticeTypeName", notice_type)
        detail_fields["工程类型"] = item.get("projectType", "")
        detail_fields["抓取时间"] = now_ts
        detail_fields["状态"] = ""

        # 公告链接（统一用 details.html 格式）
        detail_url = f"https://www.szexgrp.com/jyfw/details.html?contentId={cid}&channelId=2851&crumb=jsgc"
        detail_fields["公告链接"] = {"link": detail_url, "text": "查看公告"}

        # 写入飞书
        r = bitable_api("POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            token, {"fields": detail_fields})

        if r.get("code") == 0:
            print(f"    ✅ 写入成功")
            success_count += 1
        else:
            print(f"    ❌ 失败: {r.get('msg')}")

        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"✅ 完成！新增 {success_count}/{len(new_items)} 条记录")
    return success_count

if __name__ == "__main__":
    main()
