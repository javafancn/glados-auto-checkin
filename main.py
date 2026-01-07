import requests
import os
import time
import random

def checkin():
    # 从环境变量获取 Cookie
    cookie = os.environ.get("GLADOS_COOKIE")
    if not cookie:
        print("❌ 未找到 Cookie，请检查 Github Secrets 设置")
        return

    url = "https://glados.space/api/user/checkin"
    payload = {"token": "glados.space"}
    headers = {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        print("🚀 开始执行签到...")
        response = requests.post(url, json=payload, headers=headers)
        result = response.json()
        
        # 输出结果用于日志查看
        print(f"📡 响应状态: {response.status_code}")
        print(f"📝 签到结果: {result.get('message')}")
        
        # 简单的结果判断
        if result.get('code') == 0: # 0 通常代表成功
             print("✅ 签到成功！")
        else:
             print(f"⚠️ 可能已签到或出错: {result}")
             
    except Exception as e:
        print(f"❌ 请求发生错误: {e}")

if __name__ == "__main__":
    # --- 随机等待逻辑 ---
    # GitHub Actions 启动时间通常比较准时
    # 为了模拟“白天随机时间”，我们让脚本随机休眠 0 到 3 小时 (10800秒)
    # 这样签到时间就会分布在启动后的 3 小时内
    
    wait_seconds = random.randint(0, 30) 
    
    # 转换成小时和分钟方便查看日志
    m, s = divmod(wait_seconds, 60)
    h, m = divmod(m, 60)
    
    print(f"⏳ 随机延迟启动: 计划等待 {h}小时 {m}分 {s}秒...")
    time.sleep(wait_seconds)
    
    checkin()
