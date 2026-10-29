import os
import re
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import formataddr

import requests

# Default timeout for HTTP requests (seconds).
REQUESTS_TIMEOUT = int(os.environ.get("REQUESTS_TIMEOUT", "10"))
SESSION_KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+):sess(\.sig)?$")
AUTH_FAILURE_TERMS = (
    "没有权限", "权限不足", "未登录", "登录已失效", "unauthorized",
    "forbidden", "invalid token", "token error",
)
COOKIE_FORMAT_HINT = (
    "请登录 https://glados.cloud，重新复制完整 Cookie 并更新对应的 GitHub Secret。"
    "需要同一前缀的 sess 和 sess.sig 成对出现，例如 "
    "gld:sess=...; gld:sess.sig=...（旧版为 koa:sess / koa:sess.sig）。"
    "不要手动修改 Cookie 的前缀。"
)


def send_mail(subject, content):
    sender = os.environ.get("MAIL_USERNAME")
    password = os.environ.get("MAIL_PASSWORD")

    receiver = os.environ.get("MAIL_TO")
    if not receiver:
        receiver = sender
        print(f"ℹ️ 未设置 MAIL_TO，默认发送给发件人: {receiver}")

    smtp_server = os.environ.get("MAIL_SMTP_SERVER", "smtp.qq.com")
    smtp_port = int(os.environ.get("MAIL_SMTP_PORT", 465))

    if not sender or not password:
        print("⚠️ 邮件通知未配置 (MAIL_USERNAME/MAIL_PASSWORD)，跳过发送。")
        return

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        unique_subject = f"{subject} [{timestamp}]"
        message = MIMEText(content, "plain", "utf-8")
        message["From"] = formataddr(("GLaDOS Bot", sender))
        message["To"] = formataddr(("User", receiver))
        message["Subject"] = unique_subject

        print(f"📧 正在发送邮件通知至 {receiver} ...")
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        server.login(sender, password)
        server.sendmail(sender, [receiver], message.as_string())
        server.quit()
        print("✅ 邮件已发送成功")
    except smtplib.SMTPRecipientsRefused:
        print(f"❌ 邮件发送失败: 收件人地址 {receiver} 不存在或被拒绝")
    except Exception as e:
        print(f"❌ 邮件发送异常: {str(e)}")


def normalize_cookie(raw_cookie):
    """Remove copy/paste artifacts without changing any cookie key or value."""
    cookie = (raw_cookie or "").strip()
    # Strip wrapping quotes and the Cookie header label in either order.
    for _ in range(3):
        if len(cookie) >= 2 and cookie[0] == cookie[-1] and cookie[0] in ('"', "'"):
            cookie = cookie[1:-1].strip()
        elif cookie[:7].lower() == "cookie:":
            cookie = cookie[7:].strip()
        else:
            break
    return cookie


def validate_cookie(cookie):
    """Check for a nonempty matching <prefix>:sess and <prefix>:sess.sig pair.

    This is only a structural check, not proof that the session is still valid.
    Returns (valid, prefix_or_error); never includes cookie values in errors.
    """
    found = {}
    for part in cookie.split(";"):
        key, separator, value = part.strip().partition("=")
        if not separator or not value.strip():
            continue
        match = SESSION_KEY_RE.fullmatch(key.strip())
        if not match:
            continue
        prefix, suffix = match.groups()
        found.setdefault(prefix, set()).add("sig" if suffix else "sess")

    for prefix, fields in found.items():
        if {"sess", "sig"} <= fields:
            return True, prefix

    if found:
        prefixes = ", ".join(sorted(found))
        return False, f"Cookie 会话字段不成对（检测到前缀: {prefixes}）。{COOKIE_FORMAT_HINT}"
    return False, f"Cookie 缺少有效的 sess / sess.sig 会话字段。{COOKIE_FORMAT_HINT}"


def is_auth_failure(message):
    return any(term in str(message).lower() for term in AUTH_FAILURE_TERMS)


def checkin():
    raw_cookie = os.environ.get("GLADOS_COOKIE")
    token = os.environ.get("GLADOS_TOKEN", "glados.cloud")

    if not raw_cookie:
        msg = "❌ 错误: 未设置 GLADOS_COOKIE 环境变量"
        print(msg)
        send_mail("GLaDOS 配置错误", msg)
        return 1

    cookie = normalize_cookie(raw_cookie)
    valid, info = validate_cookie(cookie)
    if not valid:
        msg = f"❌ Cookie 格式错误: {info}"
        print(msg)
        send_mail("GLaDOS Cookie 配置错误", msg)
        return 1

    print(f"ℹ️ 已识别 Cookie 会话前缀: {info}:（不会修改原始前缀）")
    url = "https://glados.cloud/api/user/checkin"
    headers = {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://glados.cloud",
        "Referer": "https://glados.cloud/console/checkin",
    }

    try:
        print("🚀 正在尝试签到...")
        response = requests.post(url, headers=headers, json={"token": token}, timeout=REQUESTS_TIMEOUT)
        if response.status_code != 200:
            hint = f" {COOKIE_FORMAT_HINT}" if response.status_code in (401, 403) else ""
            err_msg = f"HTTP 请求失败: {response.status_code}.{hint}"
            print(f"❌ {err_msg}")
            send_mail("GLaDOS 网络或鉴权错误", err_msg)
            return 1

        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("签到接口返回的 JSON 格式不正确")
        code = data.get("code")
        message = data.get("message", "")

        if code in (0, 1):
            status_msg = "签到成功" if code == 0 else "重复签到"
            days_str = "未知"
            try:
                status_resp = requests.get(
                    "https://glados.cloud/api/user/status",
                    headers=headers, timeout=REQUESTS_TIMEOUT,
                )
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    details = status_data.get("data") if isinstance(status_data, dict) else None
                    if isinstance(details, dict) and details.get("leftDays") is not None:
                        days_str = str(details["leftDays"]).split(".")[0]
            except (requests.RequestException, ValueError, TypeError):
                print("⚠️ 查询剩余天数失败，但签到结果不受影响")
            log_msg = f"{status_msg}: {message}\n📅 剩余天数: {days_str}"
            print(f"✅ {log_msg}")
            send_mail(f"GLaDOS {status_msg}", log_msg)
            return 0

        hint = f" {COOKIE_FORMAT_HINT}" if is_auth_failure(message) else ""
        err_msg = f"签到失败: {message} (Code: {code}).{hint}"
        print(f"❌ {err_msg}")
        send_mail("GLaDOS 签到失败", err_msg)
        return 1
    except (requests.RequestException, ValueError, TypeError) as e:
        err_msg = f"签到请求异常: {e}"
        print(f"❌ {err_msg}")
        send_mail("GLaDOS 脚本错误", err_msg)
        return 1


if __name__ == "__main__":
    sys.exit(checkin())
