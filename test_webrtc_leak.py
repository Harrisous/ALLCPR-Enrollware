#!/usr/bin/env python3
"""
详细测试 WebRTC IP 泄露
使用 JavaScript 直接检测 WebRTC 是否泄露真实 IP
"""
import os
import undetected_chromedriver as uc
import time
import re

# 设置代理
proxy_server = os.getenv("PROXY_SERVER", "socks5://127.0.0.1:8080")

print("=" * 60)
print("WebRTC IP 泄露检测")
print("=" * 60)
print(f"使用代理: {proxy_server}")
print()

options = uc.ChromeOptions()
options.add_argument(f"--proxy-server={proxy_server}")

# WebRTC 防护参数（与 login_humanlike.py 相同）
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
    
    print("1. 检查代理 IP...")
    driver.get("https://api.ipify.org")
    time.sleep(2)
    proxy_ip = driver.find_element("tag name", "body").text.strip()
    print(f"   代理 IP: {proxy_ip}")
    print()
    
    print("2. 测试 WebRTC IP 泄露...")
    print("   使用 JavaScript 直接检测 WebRTC...")
    
    # 使用 JavaScript 检测 WebRTC IP
    webrtc_test_script = """
    return new Promise((resolve) => {
        const ips = [];
        const pc = new RTCPeerConnection({
            iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
        });
        
        pc.onicecandidate = (event) => {
            if (event.candidate) {
                const candidate = event.candidate.candidate;
                // 提取 IP 地址
                const ipMatch = candidate.match(/([0-9]{1,3}\.){3}[0-9]{1,3}/);
                if (ipMatch) {
                    ips.push(ipMatch[0]);
                }
            } else {
                // 所有候选者已收集完成
                setTimeout(() => {
                    pc.close();
                    resolve(ips);
                }, 2000);
            }
        };
        
        pc.createDataChannel('');
        pc.createOffer().then(offer => {
            pc.setLocalDescription(offer);
        }).catch(err => {
            resolve(['ERROR: ' + err.message]);
        });
        
        // 超时保护
        setTimeout(() => {
            pc.close();
            resolve(ips.length > 0 ? ips : ['TIMEOUT']);
        }, 5000);
    });
    """
    
    try:
        webrtc_ips = driver.execute_async_script(webrtc_test_script)
        print(f"   检测到的 WebRTC IP: {webrtc_ips}")
        
        if not webrtc_ips or webrtc_ips == ['TIMEOUT'] or webrtc_ips == []:
            print("   ✅ WebRTC 未泄露 IP（可能被成功拦截）")
        elif any('ERROR' in str(ip) for ip in webrtc_ips):
            print("   ✅ WebRTC 被禁用或拦截")
        else:
            # 检查是否有私有 IP（通常是本地网络 IP，不是真实公网 IP）
            private_ip_pattern = re.compile(r'^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)')
            public_ips = [ip for ip in webrtc_ips if not private_ip_pattern.match(ip)]
            
            if public_ips:
                print(f"   ⚠️  检测到公网 IP: {public_ips}")
                if proxy_ip in public_ips:
                    print("   ✅ WebRTC IP 与代理 IP 一致（正常）")
                else:
                    print("   ❌ WebRTC 泄露了不同的 IP（可能泄露了真实 IP）")
            else:
                print("   ✅ 只检测到私有 IP（正常，未泄露公网 IP）")
                
    except Exception as e:
        print(f"   WebRTC 测试出错: {e}")
        print("   这可能意味着 WebRTC 已被成功禁用")
    
    print()
    print("3. 访问 WebRTC 检测网站...")
    driver.get("https://browserleaks.com/webrtc")
    time.sleep(5)
    
    # 尝试查找页面中的 IP 信息
    try:
        page_text = driver.find_element("tag name", "body").text
        # 查找 IP 地址模式
        ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
        found_ips = ip_pattern.findall(page_text)
        
        if found_ips:
            unique_ips = list(set(found_ips))
            print(f"   页面中发现的 IP: {unique_ips}")
            
            # 过滤掉常见的本地 IP
            filtered_ips = [ip for ip in unique_ips if not ip.startswith(('127.', '0.', '169.254.'))]
            
            if filtered_ips:
                if proxy_ip in filtered_ips:
                    print("   ✅ 页面显示的 IP 与代理 IP 一致")
                else:
                    print(f"   ⚠️  页面显示了其他 IP: {filtered_ips}")
                    print("   请手动检查这些 IP 是否是真实 IP")
            else:
                print("   ✅ 未发现可疑的公网 IP")
        else:
            print("   ✅ 页面中未发现 IP 地址")
    except Exception as e:
        print(f"   检查页面内容时出错: {e}")
    
    print()
    print("=" * 60)
    print("测试总结:")
    print(f"  代理 IP: {proxy_ip}")
    print("  预期代理 IP: 136.56.72.172")
    
    if proxy_ip == "136.56.72.172":
        print("  ✅ 代理配置正确")
    else:
        print("  ❌ 代理 IP 不匹配")
    
    print("=" * 60)
        
except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()
finally:
    driver.quit()
    print("\n测试完成")
