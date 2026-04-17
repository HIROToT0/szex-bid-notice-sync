#!/usr/bin/env python3
"""测试腾讯企业邮 IMAP/SMTP 连接"""

import imaplib
import smtplib
import sys


def test_connection(email, auth_code, imap_host='imap.exmail.qq.com',
                   smtp_host='smtp.exmail.qq.com'):
    results = {}

    # IMAP
    print('=== IMAP 测试 ===')
    try:
        m = imaplib.IMAP4_SSL(imap_host)
        m.login(email, auth_code)
        m.select('INBOX')
        typ, data = m.search(None, 'ALL')
        ids = data[0].split() if data[0] else []
        print(f'✅ IMAP 登录成功，收件箱 {len(ids)} 封邮件')
        m.logout()
        results['imap'] = True
    except Exception as e:
        print(f'❌ IMAP 失败: {e}')
        results['imap'] = False

    # SMTP
    print('\n=== SMTP 测试 ===')
    try:
        s = smtplib.SMTP_SSL(smtp_host, 465)
        s.login(email, auth_code)
        print('✅ SMTP 登录成功')
        s.quit()
        results['smtp'] = True
    except Exception as e:
        print(f'❌ SMTP 失败: {e}')
        results['smtp'] = False

    return results


if __name__ == '__main__':
    email = sys.argv[1] if len(sys.argv) > 1 else input('邮箱地址: ')
    auth_code = sys.argv[2] if len(sys.argv) > 2 else input('授权码: ')
    test_connection(email, auth_code)
