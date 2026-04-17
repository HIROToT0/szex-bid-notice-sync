#!/usr/bin/env python3
"""抓取完成后通过腾讯企业邮发送招标公告通知邮件"""

import json
import os
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.header import Header


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json')
    with open(config_path) as f:
        return json.load(f)


def send_email(subject, html_body, to_addresses):
    """通过腾讯企业邮 SMTP 发送邮件"""
    config = load_config()
    smtp_cfg = config.get('smtp', {})

    email = smtp_cfg.get('user', 'hew@tkjy.com')
    auth_code = smtp_cfg.get('auth_code', '')
    smtp_host = smtp_cfg.get('host', 'smtp.exmail.qq.com')
    smtp_port = smtp_cfg.get('port', 465)

    msg = MIMEText(html_body, 'html', 'utf-8')
    msg['From'] = Header(f'招标公告系统 <{email}>', 'utf-8')
    msg['To'] = ', '.join(to_addresses)
    msg['Subject'] = Header(subject, 'utf-8')

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(email, auth_code)
        server.sendmail(email, to_addresses, msg.as_string())

    print(f'✅ 邮件已发送至: {", ".join(to_addresses)}')


def main():
    config = load_config()
    app_token = config.get('app_token')
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    date_str = now.strftime('%Y-%m-%d')

    bitable_url = f'https://ccnlg9zq6b6x.feishu.cn/base/{app_token}'
    subject = f'招标公告更新通知 - {date_str}'

    html = f"""
    <div style="font-family: Microsoft YaHei, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #333;">📊 深圳招标公告已更新</h2>
        <p>抓取时间：{date_str} {now.strftime('%H:%M')}</p>
        <p>数据已同步至飞书多维表格，点击下方链接查看：</p>
        <p style="text-align: center; margin: 20px 0;">
            <a href="{bitable_url}" target="_blank"
               style="background: #1677ff; color: #fff; padding: 10px 24px;
                      border-radius: 6px; text-decoration: none; display: inline-block;">
                📋 打开飞书多维表格
            </a>
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">
            此邮件由 OpenClaw 深圳交易集团招标公告抓取系统自动发送
        </p>
    </div>
    """

    recipients = config.get('email_recipients', ['hew@tkjy.com'])
    send_email(subject, html, recipients)


if __name__ == '__main__':
    main()
