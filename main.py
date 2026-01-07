        print("❌ 错误: 未设置 GLADOS_COOKIE 环境变量")
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
            
            if code == 0:
                print(f"✅ 签到成功: {message}")
            elif code == 1:
                print(f"ℹ️ 状态: {message}")
            else:
                print(f"⚠️ 响应异常: {message} (Code: {code})")
            
            # 只要不是 token error，就显示剩余天数
            if "token error" not in str(message).lower():
                status_url = "https://glados.space/api/user/status"
                status_resp = requests.get(status_url, headers=headers, timeout=10)
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    days = status_data.get("data", {}).get("leftDays")
                    days_str = str(days).split(".")[0] if "." in str(days) else str(days)
                    print(f"📅 剩余会员天数: {days_str} 天")
        else:
            print(f"❌ HTTP 请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 程序异常: {str(e)}")

if __name__ == "__main__":
    checkin()
