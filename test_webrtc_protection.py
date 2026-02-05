#!/usr/bin/env python3
"""
测试 WebRTC 泄露防护
验证代理环境下 WebRTC 不会泄露真实 IP
"""
import os
import undetected_chromedriver as uc
import time

# 设置代理
proxy_server = os.getenv("PROXY_SERVER", "socks5://127.0.0.1:8080")

print(f"使用代理: {proxy_server}")
print("=" * 60)

options = uc.ChromeOptions()
options.add_argument(f"--proxy-server={proxy_server}")

# WebRTC 防护参数
options.add_argument("--disable-webrtc")
options.add_argument("--disable-webrtc-hw-encoding")
options.add_argument("--disable-webrtc-hw-decoding")
options.add_argument("--disable-webrtc-multiple-routes")
options.add_argument("--disable-webrtc-hw-vp8-encoding")
options.add_argument("--disable-webrtc-ip-handling-policy")

options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = uc.Chrome(options=options, version_main=144, headless=True)

try:
    # 注入 WebRTC 防护脚本（与 login_humanlike.py 中相同）
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': r'''
            // WebRTC 泄露防护 - 拦截 RTCPeerConnection
            const originalRTCPeerConnection = window.RTCPeerConnection;
            
            window.RTCPeerConnection = function(...args) {
                const pc = new originalRTCPeerConnection(...args);
                const originalCreateOffer = pc.createOffer.bind(pc);
                
                pc.createOffer = function(...args) {
                    return originalCreateOffer(...args).then(offer => {
                        if (offer && offer.sdp) {
                            // 移除所有 candidate 行（包含 IP 地址）
                            offer.sdp = offer.sdp.replace(/a=candidate:.*[\r\n]+/g, '');
                            offer.sdp = offer.sdp.replace(/a=rtcp:.*[\r\n]+/g, '');
                        }
                        return offer;
                    });
                };
                
                return pc;
            };
        '''
    })
    
    print("1. 访问 IP 检查网站...")
    driver.get("https://api.ipify.org")
    time.sleep(3)
    ip = driver.find_element("tag name", "body").text.strip()
    print(f"   检测到的 IP: {ip}")
    
    print("\n2. 测试 WebRTC 泄露（使用 WebRTC IP 检测网站）...")
    driver.get("https://browserleaks.com/webrtc")
    time.sleep(5)
    
    # 尝试查找 WebRTC IP
    try:
        # 查找可能显示 IP 的元素
        page_source = driver.page_source
        if "webrtc" in page_source.lower():
            print("   ⚠️  检测到 WebRTC 相关内容")
            print("   请手动检查页面是否显示真实 IP")
        else:
            print("   ✅ 未检测到明显的 WebRTC IP 泄露")
    except Exception as e:
        print(f"   检查 WebRTC 时出错: {e}")
    
    print("\n3. 测试代理 IP...")
    driver.get("https://api.ipify.org")
    time.sleep(2)
    final_ip = driver.find_element("tag name", "body").text.strip()
    print(f"   最终检测到的 IP: {final_ip}")
    
    if final_ip == "136.56.72.172":
        print("\n✅ 代理工作正常，IP 正确")
    else:
        print(f"\n❌ IP 不匹配，预期: 136.56.72.172，实际: {final_ip}")
        
except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()
finally:
    driver.quit()
    print("\n测试完成")
