#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书多维表格新增记录邮件通知脚本
功能：读取飞书多维表格最新N条记录，生成 HTML 邮件并发送
依赖：Python 3.8+, smtplib（内置）
"""

import json, subprocess, sys, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime, timezone, timedelta
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "email.json"

def get_feishu_creds():
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    with open(config_path) as f:
        config = json.load(f)
    feishu_cfg = config.get("channels", {}).get("feishu", {})
    accounts = feishu_cfg.get("accounts", {})
    main_acc = accounts.get("main", accounts.get("default", {}))
    return main_acc.get("appId"), main_acc.get("appSecret")

def get_tenant_token(app_id, app_secret):
    r = subprocess.run([
        "curl", "-s", "-X", "POST",
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"app_id": app_id, "app_secret": app_secret})
    ], capture_output=True, text=True)
    return json.loads(r.stdout)["tenant_access_token"]

def ms_to_date(ms):
    """毫秒时间戳 -> 'yyyy/MM/dd' 格式"""
    if not ms:
        return "—"
    from datetime import datetime, timezone, timedelta
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone(timedelta(hours=8)))
    return dt.strftime("%Y/%m/%d")

def bitable_api(method, path, token, data=None):
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

def fetch_recent_records(app_token, table_id, token, limit=10):
    """获取最近N条记录"""
    result = bitable_api("GET",
        f"/bitable/v1/apps/{app_token}/tables/{table_id}/records?page_size={limit}&sort=-创建时间",
        token)
    return result.get("data", {}).get("items", [])

def build_html_email(records):
    """构建 HTML 邮件内容"""
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y年%m月%d日 %H:%M")

    rows = ""
    for i, rec in enumerate(records, 1):
        f = rec.get("fields", {})
        name = f.get("公告名称", "—")
        ntype = f.get("公告类型", "—")
        ptype = f.get("工程类型", "—")
        pub_time = ms_to_date(f.get("发布时间"))
        deadline = ms_to_date(f.get("投标截止时间"))
        region = f.get("项目区域", f.get("公告地区", "—"))
        link_data = f.get("公告链接", {})
        link_url = link_data.get("link", "#") if isinstance(link_data, dict) else "#"

        rows += f"""
        <tr style="background: {'#f9f9f9' if i % 2 == 0 else '#ffffff'}">
            <td style="padding:8px 12px;border:1px solid #ddd;text-align:center">{i}</td>
            <td style="padding:8px 12px;border:1px solid #ddd">
                <a href="{link_url}" style="color:#2161dc;text-decoration:none" target="_blank">{name[:40]}{'...' if len(name)>40 else ''}</a>
            </td>
            <td style="padding:8px 12px;border:1px solid #ddd;text-align:center">{ntype}</td>
            <td style="padding:8px 12px;border:1px solid #ddd;text-align:center">{ptype}</td>
            <td style="padding:8px 12px;border:1px solid #ddd;text-align:center">{region}</td>
            <td style="padding:8px 12px;border:1px solid #ddd;text-align:center">{pub_time}</td>
            <td style="padding:8px 12px;border:1px solid #ddd;text-align:center;color:{'#e55' if deadline and deadline!='—' else '#333'}">{deadline}</td>
        </tr>"""

    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
body{{ font-family: Arial, "Microsoft YaHei", sans-serif; margin: 20px; color: #333; }}
h2{{ color: #2161dc; border-bottom: 2px solid #2161dc; padding-bottom: 8px; }}
table{{ border-collapse: collapse; width: 100%; margin-top: 16px; font-size: 14px; }}
th{{ background: #2161dc; color: #fff; padding: 10px 12px; border: 1px solid #1a4db8; text-align: center; }}
td{{ vertical-align: top; }}
.footer{{ margin-top: 20px; font-size: 12px; color: #888; }}
.highlight{{ color: #e55; font-weight: bold; }}
</style>
</head>
<body>
<h2>📢 深圳交易集团招标公告更新通知</h2>
<p>抓取时间：{now} &nbsp;|&nbsp; 共 <strong>{len(records)}</strong> 条记录</p>

<table>
<tr>
    <th style="width:5%">#</th>
    <th style="width:35%">公告名称</th>
    <th style="width:10%">公告类型</th>
    <th style="width:8%">工程类型</th>
    <th style="width:8%">区域</th>
    <th style="width:12%">发布时间</th>
    <th style="width:12%">投标截止</th>
</tr>
{rows}
</table>

<div class="footer">
<p>本邮件由 <strong>OpenClaw + 深圳交易集团招标公告抓取系统</strong> 自动发送</p>
<p>⚠️ 投标截止时间标红表示距今不足7天，请及时关注！</p>
</div>
</body>
</html>"""
    return html

def load_email_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    # 默认配置
    return {
        "smtp_host": "smtp.example.com",
        "smtp_port": 465,
        "smtp_user": "your@email.com",
        "smtp_password": "your_password",
        "use_ssl": True,
        "from_name": "OpenClaw招标公告系统",
        "to_addresses": ["recipient@example.com"],
        "subject": "【招标公告】每日更新提醒"
    }

def send_email(html_content, cfg):
    """发送邮件"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(cfg.get("subject", "【招标公告】每日更新提醒"), "utf-8")
    msg["From"] = f"{cfg.get('from_name', 'OpenClaw')} <{cfg.get('smtp_user')}>"
    msg["To"] = ", ".join(cfg.get("to_addresses", []))

    msg.attach(MIMEText(html_content, "html", "utf-8"))

    smtp_cfg = cfg
    try:
        if smtp_cfg.get("use_ssl", True):
            server = smtplib.SMTP_SSL(smtp_cfg["smtp_host"], smtp_cfg["smtp_port"])
        else:
            server = smtplib.SMTP(smtp_cfg["smtp_host"], smtp_cfg["smtp_port"])

        if not smtp_cfg.get("use_ssl"):
            server.starttls()

        server.login(smtp_cfg["smtp_user"], smtp_cfg["smtp_password"])
        server.sendmail(smtp_cfg["smtp_user"], smtp_cfg["to_addresses"], msg.as_string())
        server.quit()
        print("✅ 邮件发送成功")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

def main():
    app_id, app_secret = get_feishu_creds()
    if not app_id or not app_secret:
        print("❌ 未找到飞书凭证")
        return

    # 读取配置
    cfg = load_email_config()
    app_token = cfg.get("app_token") or exit_config_error("app_token")
    table_id = cfg.get("table_id") or exit_config_error("table_id")
    limit = cfg.get("email_record_limit", 10)

    token = get_tenant_token(app_id, app_secret)
    records = fetch_recent_records(app_token, table_id, token, limit)

    if not records:
        print("⚠️ 没有记录，跳过邮件发送")
        return

    html = build_html_email(records)
    send_email(html, cfg)

if __name__ == "__main__":
    main()
