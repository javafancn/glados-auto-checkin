import requests
import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.header import Header

def send_mail(subject, content):
    sender = os.environ.get("MAIL_USERNAME")
    password = os.environ.get("MAIL_PASSWORD")
    receiver = os.environ.get("MAIL_TO", "545443766@qq.com")
    
    # 支持自定义 SMTP 服务器，默认为 QQ 邮箱
    smtp_server = os.environ.get("MAIL_SMTP_SERVER", "smtp.qq.com")
    smtp_port = int(os.environ.get("MAIL_SMTP_PORT", 465))
    
    if not sender or not password:
        print("⚠️ 邮件通知未配置 (MAIL_USERNAME/MAIL_PASSWORD)，跳过发送。")
        return

    try:
        message = MIMEText(content, "plain", "utf-8")
        message["From"] = Header(f"GLaDOS Bot <{sender}>", "utf-8")
        message["To"] = Header(receiver, "utf-8")
        message["Subject"] = Header(subject, "utf-8")

        print("📧 正在发送邮件通知...")
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            # 兼容非 SSL 端口 (如 587 TLS)
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            
        server.login(sender, password)
        server.sendmail(sender, [receiver], message.as_string())
        server.quit()
        print(f"✅ 邮件已发送至 {receiver}")
    except Exception as e:
        print(f"❌ 邮件发送失败: {str(e)}")

def checkin():
    cookie = os.environ.get("GLADOS_COOKIE")
    token = os.environ.get("GLADOS_TOKEN", "glados.one")
    
    if not cookie:
        msg = "❌ 错误: 未设置 GLADOS_COOKIE 环境变量"
        print(msg)
        send_mail("GLaDOS 配置错误", msg)
        sys.exit(1)

    url = "https://glados.space/api/user/checkin"
    headers = {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://glados.space",
        "Referer": "https://glados.space/console/checkin"
    }
    payload = {"token": token}

    try:
        print(f"🚀 正在尝试签到 (Token: {token})...")
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            code = data.get("code")
            message = data.get("message")
            days_str = "未知"

            # 获取天数 (如果不是 token error)
            if "token error" not in str(message).lower():
                try:
                    status_url = "https://glados.space/api/user/status"
                    status_resp = requests.get(status_url, headers=headers, timeout=10)
                    if status_resp.status_code == 200:
                        status_data = status_resp.json()
                        days = status_data.get("data", {}).get("leftDays")
                        days_str = str(days).split(".")[0] if "." in str(days) else str(days)
                except:
                    pass

            # code 0: 成功, code 1: 重复
            if code in [0, 1]:
                status_msg = "签到成功" if code == 0 else "重复签到"
                log_msg = f"{status_msg}: {message}\n📅 剩余天数: {days_str}"
                print(f"✅ {log_msg}")
                # 现在的需求是：重复签到也要发邮件 (成功当然也要发)
                send_mail(f"GLaDOS {status_msg}", log_msg)
            else:
                err_msg = f"签到失败: {message} (Code: {code})"
                print(f"❌ {err_msg}")
                send_mail("GLaDOS 签到失败", err_msg)
        else:
            err_msg = f"HTTP 请求失败: {response.status_code}\n{response.text}"
            print(f"❌ {err_msg}")
            send_mail("GLaDOS 网络错误", err_msg)
            
    except Exception as e:
        err_msg = f"脚本执行异常: {str(e)}"
        print(f"❌ {err_msg}")
        send_mail("GLaDOS 脚本错误", err_msg)

if __name__ == "__main__":
    checkin()
