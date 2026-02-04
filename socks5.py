# test_proxy_chrome.py
import os
import undetected_chromedriver as uc
import time

# 设置代理
proxy_server = "socks5://127.0.0.1:8080"

options = uc.ChromeOptions()
options.add_argument(f"--proxy-server={proxy_server}")
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

print(f"使用代理: {proxy_server}")
driver = uc.Chrome(options=options, version_main=144, headless=True)

try:
    # 访问 IP 检查网站
    print("访问 https://api.ipify.org 检查 IP...")
    driver.get("https://api.ipify.org")
    time.sleep(3)
    
    # 获取页面内容
    ip = driver.find_element("tag name", "body").text.strip()
    print(f"检测到的 IP: {ip}")
    
    if ip == "136.56.72.172":
        print("✅ 代理工作正常！")
    else:
        print(f"❌ 代理可能未生效，检测到的 IP: {ip}")
        print("   预期 IP: 136.56.72.172")
        
except Exception as e:
    print(f"❌ 错误: {e}")
finally:
    driver.quit()