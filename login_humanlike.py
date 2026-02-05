"""
使用 Selenium + undetected-chromedriver 模拟人类行为自动登录 Enrollware。

特点：
- 使用 undetected-chromedriver（内置反检测功能，支持 Chrome 144）
- 模拟人类鼠标移动轨迹
- 逐字符输入，带随机延迟
- 模拟真实人类操作节奏
- 自动处理 Cloudflare Turnstile 验证（包括 Shadow DOM）
- 优化的 headless 模式，支持 Xvfb 虚拟显示（推荐用于绕过 Cloudflare）

运行模式：
- 可见模式：HEADLESS=false（默认，用于调试）
- Headless + Xvfb：HEADLESS=true USE_XVFB=true（推荐，Linux 系统）
- 标准 Headless：HEADLESS=true（已优化，但可能被检测）

Chrome Profile 使用（绕过 AWS IP 被标记）：
- 本地成功登录后，设置 CHROME_PROFILE_DIR=./chrome_profile 保存 profile
- 将 chrome_profile 目录复制到 AWS 环境
- 在 AWS 中设置 CHROME_PROFILE_DIR=./chrome_profile 使用保存的 profile
- Profile 包含 cookies、缓存和浏览器指纹，有助于绕过 Cloudflare 检测
"""
import logging
import os
import random
import subprocess
import sys
import time
from typing import Optional, Tuple

from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

LOGIN_URL = "https://www.enrollware.com/admin/login.aspx"
TARGET_URL_FRAGMENT = "class-list.aspx"


def setup_logging(log_file: str = "login_humanlike.log") -> None:
    """配置日志记录到文件和终端。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def load_credentials() -> Tuple[str, str]:
    """从 .env 加载用户名和密码。"""
    load_dotenv()
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")

    if not username or not password:
        raise RuntimeError("请在 .env 中配置 USERNAME 和 PASSWORD")

    logging.info("成功从 .env 读取到用户名和密码。")
    return username, password


def start_xvfb(display_num: str = ":99") -> Optional[subprocess.Popen]:
    """
    启动 Xvfb 虚拟显示服务器（仅 Linux）。
    
    Args:
        display_num: 显示编号，例如 ":99"
        
    Returns:
        subprocess.Popen 对象，如果启动失败则返回 None
    """
    if sys.platform != "linux":
        logging.warning("Xvfb 仅在 Linux 系统上可用")
        return None
    
    try:
        # 检查 Xvfb 是否已运行
        result = subprocess.run(
            ['pgrep', '-f', f'Xvfb.*{display_num}'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logging.info(f"Xvfb 已在显示 {display_num} 上运行")
            os.environ['DISPLAY'] = display_num
            return None
        
        # 启动 Xvfb
        logging.info(f"启动 Xvfb 虚拟显示服务器 (DISPLAY={display_num})...")
        xvfb_process = subprocess.Popen(
            ['Xvfb', display_num, '-screen', '0', '1920x1080x24', '-ac', '+extension', 'RANDR'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # 等待一下确保 Xvfb 启动完成
        time.sleep(1)
        
        # 检查进程是否还在运行
        if xvfb_process.poll() is None:
            os.environ['DISPLAY'] = display_num
            logging.info(f"Xvfb 已成功启动 (PID: {xvfb_process.pid})")
            return xvfb_process
        else:
            logging.warning("Xvfb 启动失败")
            return None
            
    except FileNotFoundError:
        logging.warning("Xvfb 未安装。安装命令: sudo apt-get install xvfb")
        return None
    except Exception as e:
        logging.exception(f"启动 Xvfb 时出错: {e}")
        return None


def create_chrome_driver(headless: bool = False, use_xvfb: bool = False, user_data_dir: Optional[str] = None, proxy_server: Optional[str] = None) -> uc.Chrome:
    """
    使用 undetected-chromedriver 创建 Chrome WebDriver。
    
    undetected-chromedriver 内置了反自动化检测功能，比手动配置更简单有效。

    Args:
        headless: 是否使用无头模式（默认 False，便于观察和调试）
        use_xvfb: 是否使用 Xvfb 虚拟显示（仅 Linux，推荐用于 headless 模式）
        user_data_dir: Chrome profile 数据目录路径（如果提供，将使用该目录保存 cookies、缓存等）
        proxy_server: 代理服务器地址（格式：http://host:port 或 socks5://host:port，用于绕过 AWS IP 检测）

    Returns:
        uc.Chrome: undetected-chromedriver 实例
    """
    logging.info("正在创建 Chrome WebDriver（使用 undetected-chromedriver，headless=%s，use_xvfb=%s，user_data_dir=%s，proxy=%s）...", 
                 headless, use_xvfb, user_data_dir if user_data_dir else "默认临时目录", proxy_server if proxy_server else "无")
    
    try:
        # 配置 Chrome 选项
        options = uc.ChromeOptions()
        
        # 如果指定了 user_data_dir，使用它来保存 profile 数据
        if user_data_dir:
            # 确保目录存在
            os.makedirs(user_data_dir, exist_ok=True)
            options.user_data_dir = user_data_dir
            logging.info(f"使用 Chrome profile 目录: {user_data_dir}")
            logging.info("这将保存 cookies、缓存和浏览器指纹信息，有助于绕过 Cloudflare 检测")
        
        if headless and not use_xvfb:
            # 使用新的 headless 模式，并添加更多反检测参数
            options.add_argument("--headless=new")
            # 移除 headless 标识的关键参数
            options.add_argument("--disable-blink-features=AutomationControlled")
            # 添加更多反检测参数
            options.add_argument("--disable-features=IsolateOrigins,site-per-process,VizDisplayCompositor")
            # 模拟真实浏览器的窗口大小和行为
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--start-maximized")
            # 禁用一些可能暴露自动化的特征
            options.add_argument("--disable-extensions")
            options.add_argument("--no-first-run")
            options.add_argument("--disable-default-apps")
            # 添加语言和区域设置
            options.add_argument("--lang=en-US,en")
            options.add_argument("--accept-lang=en-US,en")
        
        # 基本参数（所有模式都需要）
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        # 禁用 CSP 相关警告
        options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        # 允许不安全内容（某些 Cloudflare 资源可能需要）
        options.add_argument("--allow-running-insecure-content")
        
        # WebRTC 泄露防护（防止泄露真实 IP，即使使用代理）
        options.add_argument("--disable-webrtc")
        options.add_argument("--disable-webrtc-hw-encoding")
        options.add_argument("--disable-webrtc-hw-decoding")
        options.add_argument("--disable-webrtc-multiple-routes")
        options.add_argument("--disable-webrtc-hw-vp8-encoding")
        options.add_argument("--disable-webrtc-ip-handling-policy")
        
        # 设置 User-Agent（移除 HeadlessChrome 标识）
        # undetected-chromedriver 会自动处理，但我们可以确保它正确
        options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36")
        
        # 配置代理服务器（用于绕过 AWS IP 检测）
        if proxy_server:
            logging.info(f"配置代理服务器: {proxy_server}")
            options.add_argument(f"--proxy-server={proxy_server}")
            logging.info("代理服务器已配置，将使用代理访问网站以绕过 AWS IP 检测")
        
        # 使用 undetected-chromedriver 创建驱动
        # version_main=144 指定 Chrome 144 版本
        driver = uc.Chrome(
            options=options,
            version_main=144,  # 指定 Chrome 144 版本
            headless=headless and not use_xvfb,  # 如果使用 Xvfb，不使用 headless 模式
            use_subprocess=True,  # 使用子进程模式，更稳定
        )
        
        # 如果使用 Xvfb，DISPLAY 环境变量已在 start_xvfb 中设置
        if use_xvfb:
            display_num = os.getenv('DISPLAY', ':99')
            logging.info(f"使用 Xvfb 虚拟显示: {display_num}")
        
        # 最大化窗口（如果不是 headless 模式）
        if not headless or use_xvfb:
            try:
                driver.maximize_window()
            except Exception:
                pass
        
        # 通过 CDP 注入增强的反检测脚本（包括 WebRTC 泄露防护）
        # 无论是否 headless，都注入反检测脚本，确保代理环境下也能正常工作
        try:
            # 执行 CDP 命令来隐藏自动化特征和防止 WebRTC 泄露
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': r'''
                    // 隐藏 webdriver 标识
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // 删除 webdriver 属性
                    delete Object.getPrototypeOf(navigator).webdriver;
                    
                    // 覆盖 chrome 对象
                    window.chrome = {
                        runtime: {},
                        loadTimes: function() {},
                        csi: function() {},
                        app: {}
                    };
                    
                    // 覆盖 permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                    
                    // 覆盖 plugins
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    
                    // 覆盖 languages
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                    
                    // WebRTC 泄露防护 - 拦截 RTCPeerConnection
                    const originalRTCPeerConnection = window.RTCPeerConnection;
                    const originalRTCPeerConnection2 = window.webkitRTCPeerConnection || window.mozRTCPeerConnection;
                    
                    window.RTCPeerConnection = function(...args) {
                        const pc = new originalRTCPeerConnection(...args);
                        const originalCreateOffer = pc.createOffer.bind(pc);
                        const originalCreateAnswer = pc.createAnswer.bind(pc);
                        const originalSetLocalDescription = pc.setLocalDescription.bind(pc);
                        
                        // 拦截 createOffer，移除 IP 地址
                        pc.createOffer = function(...args) {
                            return originalCreateOffer(...args).then(offer => {
                                if (offer && offer.sdp) {
                                    // 移除所有 candidate 行（包含 IP 地址）
                                    // 使用正则表达式匹配并移除包含 IP 的 candidate 行
                                    offer.sdp = offer.sdp.replace(/a=candidate:.*[\r\n]+/g, '');
                                    offer.sdp = offer.sdp.replace(/a=rtcp:.*[\r\n]+/g, '');
                                }
                                return offer;
                            }).catch(err => {
                                console.error('createOffer error:', err);
                                throw err;
                            });
                        };
                        
                        // 拦截 createAnswer，移除 IP 地址
                        pc.createAnswer = function(...args) {
                            return originalCreateAnswer(...args).then(answer => {
                                if (answer && answer.sdp) {
                                    answer.sdp = answer.sdp.replace(/a=candidate:.*[\r\n]+/g, '');
                                    answer.sdp = answer.sdp.replace(/a=rtcp:.*[\r\n]+/g, '');
                                }
                                return answer;
                            }).catch(err => {
                                console.error('createAnswer error:', err);
                                throw err;
                            });
                        };
                        
                        // 拦截 setLocalDescription，移除 IP 地址
                        pc.setLocalDescription = function(...args) {
                            if (args[0] && args[0].sdp) {
                                args[0].sdp = args[0].sdp.replace(/a=candidate:.*[\r\n]+/g, '');
                                args[0].sdp = args[0].sdp.replace(/a=rtcp:.*[\r\n]+/g, '');
                            }
                            return originalSetLocalDescription(...args);
                        };
                        
                        return pc;
                    };
                    
                    // 拦截其他 WebRTC API
                    if (originalRTCPeerConnection2) {
                        window.webkitRTCPeerConnection = window.RTCPeerConnection;
                        window.mozRTCPeerConnection = window.RTCPeerConnection;
                    }
                    
                    // 禁用 getDisplayMedia（防止屏幕共享泄露）
                    if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
                        const originalGetDisplayMedia = navigator.mediaDevices.getDisplayMedia.bind(navigator.mediaDevices);
                        navigator.mediaDevices.getDisplayMedia = function(...args) {
                            return Promise.reject(new Error('getDisplayMedia is not supported'));
                        };
                    }
                    
                    // 覆盖 getUserMedia（可选，进一步防护）
                    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                        const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
                        navigator.mediaDevices.getUserMedia = function(...args) {
                            // 允许但记录，用于调试
                            return originalGetUserMedia(...args);
                        };
                    }
                    
                    // 覆盖 RTCDataChannel（防止数据通道泄露）
                    if (window.RTCDataChannel) {
                        const originalRTCDataChannel = window.RTCDataChannel;
                        window.RTCDataChannel = function(...args) {
                            const channel = new originalRTCDataChannel(...args);
                            // 可以在这里添加额外的拦截逻辑
                            return channel;
                        };
                    }
                '''
            })
            logging.info("已注入增强的反检测脚本（包括 WebRTC 泄露防护）")
        except Exception as e:
            logging.warning(f"注入 CDP 脚本失败（不影响使用）: {e}")
        
        logging.info("Chrome WebDriver 已启动（undetected-chromedriver，Chrome 144）。")
        return driver
    except Exception as e:
        logging.exception("创建 Chrome WebDriver 失败。")
        # 如果指定版本失败，尝试自动检测版本
        logging.info("尝试自动检测 Chrome 版本...")
        try:
            driver = uc.Chrome(
                options=options,
                headless=headless,
                use_subprocess=True,
            )
            if not headless:
                driver.maximize_window()
            logging.info("Chrome WebDriver 已启动（自动检测版本）。")
            return driver
        except Exception as e2:
            logging.exception("自动检测版本也失败。")
            raise e


def human_like_delay(min_ms: float = 50, max_ms: float = 300) -> None:
    """模拟人类操作的随机延迟（毫秒）。"""
    delay = random.uniform(min_ms / 1000, max_ms / 1000)
    time.sleep(delay)


def move_mouse_humanlike(actions: ActionChains, element, offset_x: int = 0, offset_y: int = 0) -> None:
    """
    模拟人类鼠标移动到元素位置，带随机轨迹。

    Args:
        actions: ActionChains 实例
        element: 目标元素
        offset_x: X 轴偏移（相对于元素中心）
        offset_y: Y 轴偏移（相对于元素中心）
    """
    # 使用更安全的方法：直接移动到元素，添加小幅随机偏移模拟人类不精确的移动
    # 先移动到元素附近，再精确移动到目标位置
    random_offset_x = random.randint(-5, 5)
    random_offset_y = random.randint(-5, 5)
    
    # 第一步：移动到元素附近（带小偏移）
    actions.move_to_element_with_offset(
        element, 
        offset_x + random_offset_x, 
        offset_y + random_offset_y
    )
    human_like_delay(50, 150)
    
    # 第二步：精确移动到目标位置
    actions.move_to_element_with_offset(element, offset_x, offset_y)
    human_like_delay(30, 100)


def handle_cloudflare_challenge(driver: uc.Chrome, wait: WebDriverWait, timeout: int = 15) -> bool:
    """
    检测并处理 Cloudflare 验证（Turnstile checkbox）。

    Args:
        driver: WebDriver 实例
        wait: WebDriverWait 实例
        timeout: 等待超时时间（秒）

    Returns:
        True 如果检测到并处理了 Cloudflare 验证，False 否则
    """
    try:
        logging.info("检测 Cloudflare 验证（等待 iframe 加载）...")
        
        # 先等待一段时间，让 Cloudflare iframe 有时间加载
        human_like_delay(2000, 3000)

        # Cloudflare Turnstile 通常在 iframe 中
        # 使用 WebDriverWait 等待 iframe 出现
        cloudflare_iframe = None
        
        # 方法1: 等待特定的 iframe 选择器出现
        iframe_selectors = [
            "iframe[src*='challenges.cloudflare.com']",
            "iframe[src*='cloudflare.com']",
            "iframe[src*='turnstile']",
            "iframe[id*='cf-']",
            "iframe[name*='cf-']",
            "iframe[title*='Cloudflare']",
            "iframe[title*='challenge']",
            "iframe[title*='Widget containing a Cloudflare security challenge']",
            "iframe[title*='Verify you are human']",
        ]

        for selector in iframe_selectors:
            try:
                iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                if iframe and iframe.is_displayed():
                    cloudflare_iframe = iframe
                    logging.info(f"通过 WebDriverWait 找到 Cloudflare iframe: {selector}")
                    break
            except Exception:
                continue

        # 方法2: 如果没找到，尝试查找所有 iframe 并检查 src
        if not cloudflare_iframe:
            logging.info("尝试通过 src 属性查找所有 iframe...")
            try:
                # 等待至少一个 iframe 出现
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
                all_iframes = driver.find_elements(By.TAG_NAME, "iframe")
                logging.info(f"页面上找到 {len(all_iframes)} 个 iframe")
                
                for iframe in all_iframes:
                    try:
                        src = iframe.get_attribute("src") or ""
                        title = iframe.get_attribute("title") or ""
                        iframe_id = iframe.get_attribute("id") or ""
                        
                        # 记录所有 iframe 信息用于调试
                        logging.debug(f"Iframe: src={src[:50]}, title={title}, id={iframe_id}")
                        
                        if any(keyword in src.lower() for keyword in ["cloudflare", "challenges", "turnstile"]):
                            cloudflare_iframe = iframe
                            logging.info(f"通过 src 属性找到 Cloudflare iframe: {src[:100]}")
                            break
                        elif any(keyword in title.lower() for keyword in ["cloudflare", "challenge", "verify"]):
                            cloudflare_iframe = iframe
                            logging.info(f"通过 title 属性找到 Cloudflare iframe: {title}")
                            break
                    except Exception as e:
                        logging.debug(f"检查 iframe 属性时出错: {e}")
                        continue
            except Exception as e:
                logging.warning(f"查找 iframe 时出错: {e}")

        if not cloudflare_iframe:
            logging.warning("未检测到 Cloudflare iframe，可能不需要验证或 iframe 尚未加载。")
            # 再等待一下，可能 iframe 加载较慢
            human_like_delay(2000, 3000)
            # 最后尝试一次快速查找
            try:
                all_iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in all_iframes:
                    if iframe.is_displayed():
                        cloudflare_iframe = iframe
                        logging.info("找到可见的 iframe，尝试使用它")
                        break
            except Exception:
                pass
            
            if not cloudflare_iframe:
                return False

        # 方法1: 在主页面通过第一个 shadow root 找到 iframe，然后切换到 iframe
        # 方法2: 直接切换到 iframe，然后在 iframe 中访问第二个 shadow root
        # 我们使用方法2，因为更简单
        
        logging.info("切换到 Cloudflare iframe...")
        driver.switch_to.frame(cloudflare_iframe)
        human_like_delay(2000, 3000)  # 等待 iframe 内容加载

        # Cloudflare Turnstile checkbox 在 iframe 内的第二个 shadow-root 中
        # 结构: iframe -> body -> shadow-root (第二个) -> div.main-wrapper -> label.cb-lb -> input[type="checkbox"]
        logging.info("检测到 checkbox 在 iframe 内的 shadow-root 中，使用 JavaScript 访问...")
        
        try:
            # JavaScript 代码来访问第二个 shadow DOM 并点击 checkbox
            click_script = """
            // 获取 iframe 的 body 元素
            const body = document.body;
            if (!body) {
                return {success: false, error: 'Body not found in iframe'};
            }
            
            // 查找包含 shadow root 的元素（第二个 shadow root）
            let shadowHost = null;
            let shadowRoot = null;
            
            // 尝试查找 shadow host（通常是 body 的直接子元素）
            const children = body.children;
            for (let i = 0; i < children.length; i++) {
                const child = children[i];
                if (child.shadowRoot) {
                    shadowHost = child;
                    shadowRoot = child.shadowRoot;
                    break;
                }
            }
            
            // 如果没找到，尝试查找所有可能的 shadow host
            if (!shadowRoot) {
                const allElements = body.querySelectorAll('*');
                for (let elem of allElements) {
                    if (elem.shadowRoot) {
                        shadowHost = elem;
                        shadowRoot = elem.shadowRoot;
                        break;
                    }
                }
            }
            
            if (!shadowRoot) {
                return {success: false, error: 'Second shadow root not found in iframe'};
            }
            
            // 在第二个 shadow root 中查找 checkbox
            // 路径: div.main-wrapper -> div#content -> div -> div.cb-c -> label.cb-lb -> input[type="checkbox"]
            let checkbox = shadowRoot.querySelector('input[type="checkbox"]');
            
            // 如果直接找不到，尝试通过 label 查找
            if (!checkbox) {
                const label = shadowRoot.querySelector('label.cb-lb');
                if (label) {
                    checkbox = label.querySelector('input[type="checkbox"]');
                }
            }
            
            if (!checkbox) {
                return {success: false, error: 'Checkbox not found in second shadow root'};
            }
            
            // 检查 checkbox 是否可见
            const style = window.getComputedStyle(checkbox);
            if (style.display === 'none' || style.visibility === 'hidden') {
                return {success: false, error: 'Checkbox is hidden'};
            }
            
            // 滚动到 checkbox 位置
            checkbox.scrollIntoView({behavior: 'smooth', block: 'center'});
            
            // 等待一下让滚动完成
            const startTime = Date.now();
            while (Date.now() - startTime < 500) {
                // 等待 500ms
            }
            
            // 点击 checkbox
            checkbox.click();
            
            // 等待一下让点击生效
            const startTime2 = Date.now();
            while (Date.now() - startTime2 < 500) {
                // 等待 500ms
            }
            
            // 检查是否被选中
            const isChecked = checkbox.checked;
            
            return {
                success: true,
                checked: isChecked,
                shadowHostTag: shadowHost ? shadowHost.tagName : 'unknown',
                checkboxFound: true
            };
            """
            
            logging.info("执行 JavaScript 访问第二个 shadow DOM 并点击 checkbox...")
            result = driver.execute_script(click_script)
            
            if result and result.get('success'):
                logging.info(f"成功点击 Cloudflare checkbox！Checkbox 状态: checked={result.get('checked')}")
                human_like_delay(3000, 5000)  # 等待验证完成
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No result'
                logging.warning(f"JavaScript 点击失败: {error_msg}")
                
                # 尝试备用方法：通过 label 点击
                logging.info("尝试备用方法：通过 label.cb-lb 点击...")
                try:
                    label_script = """
                    const body = document.body;
                    let shadowRoot = null;
                    const children = body.children;
                    for (let i = 0; i < children.length; i++) {
                        if (children[i].shadowRoot) {
                            shadowRoot = children[i].shadowRoot;
                            break;
                        }
                    }
                    if (!shadowRoot) {
                        const allElements = body.querySelectorAll('*');
                        for (let elem of allElements) {
                            if (elem.shadowRoot) {
                                shadowRoot = elem.shadowRoot;
                                break;
                            }
                        }
                    }
                    if (shadowRoot) {
                        const label = shadowRoot.querySelector('label.cb-lb');
                        if (label) {
                            label.scrollIntoView({behavior: 'smooth', block: 'center'});
                            const startTime = Date.now();
                            while (Date.now() - startTime < 500) {}
                            label.click();
                            const startTime2 = Date.now();
                            while (Date.now() - startTime2 < 500) {}
                            return {success: true, method: 'label click'};
                        }
                    }
                    return {success: false, error: 'Label not found'};
                    """
                    result2 = driver.execute_script(label_script)
                    if result2 and result2.get('success'):
                        logging.info("通过点击 label 成功！")
                        human_like_delay(3000, 5000)
                    else:
                        logging.error("所有方法都失败了")
                        driver.switch_to.default_content()
                        return False
                except Exception as e2:
                    logging.exception(f"备用方法也失败: {e2}")
                    driver.switch_to.default_content()
                    return False
                    
        except Exception as e:
            logging.exception(f"使用 JavaScript 访问 shadow DOM 时出错: {e}")
            driver.switch_to.default_content()
            return False

        # 切换回主页面
        driver.switch_to.default_content()
        logging.info("已切换回主页面，等待 Cloudflare 验证完成...")

        # 等待验证完成（通常会有页面变化或元素消失）
        human_like_delay(2000, 4000)

        return True

    except Exception as e:
        logging.exception("处理 Cloudflare 验证时出现异常。")
        # 确保切换回主页面
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
        return False


def type_humanlike(element, text: str, min_delay: float = 0.05, max_delay: float = 0.3) -> None:
    """
    模拟人类逐字符输入，带随机延迟。

    Args:
        element: 输入框元素
        text: 要输入的文本
        min_delay: 最小延迟（秒）
        max_delay: 最大延迟（秒）
    """
    element.clear()
    human_like_delay(100, 200)  # 清空后稍作停顿

    for char in text:
        element.send_keys(char)
        # 随机延迟，模拟人类打字速度
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

        # 偶尔模拟打字错误和修正（小概率）
        if random.random() < 0.05:  # 5% 概率
            element.send_keys(Keys.BACKSPACE)
            human_like_delay(50, 150)
            element.send_keys(char)


def perform_humanlike_login(
    driver: uc.Chrome, username: str, password: str
) -> bool:
    """
    模拟人类行为执行登录流程。

    Returns:
        True 如果登录成功，False 否则
    """
    wait = WebDriverWait(driver, 20)
    actions = ActionChains(driver)

    logging.info("打开登录页面: %s", LOGIN_URL)
    driver.get(LOGIN_URL)

    # 等待页面加载
    human_like_delay(1000, 2000)

    try:
        # 定位用户名输入框
        logging.info("定位用户名输入框...")
        username_input = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//input[@type='text' or @name='username' or contains(@id,'UserName') "
                    "or contains(@name,'UserName')]",
                )
            )
        )

        # 模拟鼠标移动到用户名输入框并点击
        logging.info("模拟鼠标移动到用户名输入框...")
        actions = ActionChains(driver)
        move_mouse_humanlike(actions, username_input)
        actions.click().perform()
        human_like_delay(300, 600)

        # 模拟人类输入用户名
        logging.info("模拟人类输入用户名...")
        type_humanlike(username_input, username)
        human_like_delay(300, 600)

        # 定位密码输入框
        logging.info("定位密码输入框...")
        password_input = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//input[@type='password' or contains(@id,'Password') "
                    "or contains(@name,'Password')]",
                )
            )
        )

        # 模拟鼠标移动到密码输入框并点击
        logging.info("模拟鼠标移动到密码输入框...")
        actions = ActionChains(driver)
        # 先移动到密码框附近（模拟从用户名框移动过来的轨迹）
        move_mouse_humanlike(actions, password_input)
        actions.click().perform()
        human_like_delay(300, 600)

        # 模拟人类输入密码
        logging.info("模拟人类输入密码...")
        type_humanlike(password_input, password)
        human_like_delay(500, 1000)  # 输入密码后稍作停顿

        # 定位 Sign In 按钮
        logging.info("定位 Sign In 按钮...")
        signin_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//input[@type='submit' or @type='button' or contains(@value,'Sign In') "
                    "or contains(@value,'Login') or contains(@id,'Login')] "
                    "| //button[contains(.,'Sign In') or contains(.,'Login')]",
                )
            )
        )

        # 模拟鼠标移动到 Sign In 按钮并点击
        logging.info("模拟鼠标移动到 Sign In 按钮...")
        actions = ActionChains(driver)
        move_mouse_humanlike(actions, signin_button)
        logging.info("点击 Sign In 按钮...")
        actions.click().perform()
        
        # 点击后等待页面跳转（给足够时间让验证和跳转完成）
        logging.info("等待页面跳转和验证完成...")
        human_like_delay(5000, 8000)
        
        # 第一次检查：如果已经跳转到目标页面，直接返回成功
        current_url = driver.current_url
        logging.info("第一次检查 - 当前 URL: %s", current_url)
        
        if TARGET_URL_FRAGMENT in current_url:
            logging.info("检测到成功跳转到 class-list 页面，登录成功！")
            logging.info("✓ LOGIN_SUCCESS - 当前 URL: %s", current_url)
            return True
        
        # 如果还在登录页，可能需要 Cloudflare 验证
        if "login.aspx" in current_url.lower():
            logging.info("仍在登录页，检测是否需要 Cloudflare 验证...")
            
            # 检测并处理 Cloudflare 验证
            if handle_cloudflare_challenge(driver, wait):
                logging.info("Cloudflare 验证已处理，继续等待页面跳转...")
                # 验证后等待更长时间
                human_like_delay(5000, 8000)
            else:
                logging.info("未检测到 Cloudflare 验证，继续等待页面跳转...")
                human_like_delay(3000, 5000)
            
            # 第二次检查：验证后再次检查 URL
            current_url = driver.current_url
            logging.info("第二次检查 - 当前 URL: %s", current_url)
            
            if TARGET_URL_FRAGMENT in current_url:
                logging.info("检测到成功跳转到 class-list 页面，登录成功！")
                logging.info("✓ LOGIN_SUCCESS - 当前 URL: %s", current_url)
                return True
            else:
                logging.warning("仍在登录页，可能登录失败或需要额外验证。")
                logging.error("✗ LOGIN_FAILED - 当前 URL: %s", current_url)
                return False
        else:
            # 既不在登录页，也不在目标页，可能是中间状态
            logging.info("页面处于中间状态，继续等待...")
            human_like_delay(3000, 5000)
            
            # 第三次检查
            current_url = driver.current_url
            logging.info("第三次检查 - 当前 URL: %s", current_url)
            
            if TARGET_URL_FRAGMENT in current_url:
                logging.info("检测到成功跳转到 class-list 页面，登录成功！")
                logging.info("✓ LOGIN_SUCCESS - 当前 URL: %s", current_url)
                return True
            else:
                logging.warning("未知的页面状态，当前 URL: %s", current_url)
                logging.error("✗ LOGIN_FAILED - 当前 URL: %s", current_url)
                return False

    except Exception as e:
        logging.exception("执行登录流程时出现异常。")
        try:
            current_url = driver.current_url
            logging.error("✗ LOGIN_FAILED - 异常发生时的 URL: %s", current_url)
        except:
            logging.error("✗ LOGIN_FAILED - 无法获取当前 URL")
        return False


def main() -> int:
    """
    主函数。
    
    Returns:
        0 如果登录成功，1 如果登录失败
    """
    setup_logging()
    logging.info("===== Enrollware 人类化自动登录脚本开始运行 =====")

    # 检查是否在 EC2 环境（通过环境变量控制 headless 模式）
    # 默认在 EC2 上使用 headless，本地可以通过设置 HEADLESS=false 来禁用
    is_headless = os.getenv("HEADLESS", "true").lower() == "true"
    
    # 检查是否使用 Xvfb（推荐用于 headless 模式，绕过 Cloudflare 检测）
    # 设置 USE_XVFB=true 来启用 Xvfb 虚拟显示
    use_xvfb = os.getenv("USE_XVFB", "false").lower() == "true"
    
    # 读取 Chrome profile 目录（用于保存 cookies、缓存等，有助于绕过 Cloudflare）
    # 如果本地成功登录后，可以将 profile 目录复制到 AWS 使用
    chrome_profile_dir = os.getenv("CHROME_PROFILE_DIR", "").strip()
    if chrome_profile_dir:
        # 检查目录是否存在
        if os.path.exists(chrome_profile_dir):
            logging.info(f"检测到 Chrome profile 目录: {chrome_profile_dir}")
            logging.info("将使用该目录中的 cookies、缓存和浏览器指纹信息")
        else:
            logging.warning(f"Chrome profile 目录不存在，将创建: {chrome_profile_dir}")
            os.makedirs(chrome_profile_dir, exist_ok=True)
    else:
        logging.info("未指定 CHROME_PROFILE_DIR，将使用临时目录（数据不会保存）")
        chrome_profile_dir = None
    
    # 读取代理服务器配置（用于绕过 AWS IP 检测）
    # 格式：http://host:port 或 socks5://host:port
    # 示例：PROXY_SERVER=http://proxy.example.com:8080
    proxy_server = os.getenv("PROXY_SERVER", "").strip()
    if proxy_server:
        logging.info(f"检测到代理服务器配置: {proxy_server}")
        logging.info("将使用代理服务器访问网站，以绕过 AWS IP 被 Cloudflare 检测的问题")
    else:
        logging.info("未配置代理服务器，将直接连接（如果 AWS IP 被标记，建议配置代理）")
        proxy_server = None
    
    # 如果 headless=True 且未指定 USE_XVFB，在 Linux 上自动尝试使用 Xvfb
    if is_headless and not use_xvfb and sys.platform == "linux":
        logging.info("检测到 headless 模式，建议使用 Xvfb 以提高 Cloudflare 绕过成功率")
        logging.info("设置环境变量 USE_XVFB=true 来启用 Xvfb，或手动安装: sudo apt-get install xvfb")
    
    xvfb_process = None
    try:
        username, password = load_credentials()
    except Exception as e:
        logging.exception("加载凭据失败。")
        print("✗ LOGIN_FAILED - 无法加载凭据")
        return 1

    driver = None
    try:
        # 如果使用 Xvfb，先启动虚拟显示服务器
        if use_xvfb and is_headless:
            xvfb_process = start_xvfb()
            if xvfb_process is None and sys.platform == "linux":
                logging.warning("Xvfb 启动失败，将使用标准 headless 模式")
                use_xvfb = False
        
        # 创建 Chrome（根据环境变量决定是否 headless）
        mode_description = "headless (Xvfb)" if (is_headless and use_xvfb) else ("headless" if is_headless else "visible")
        logging.info("运行模式: %s", mode_description)
        driver = create_chrome_driver(headless=is_headless, use_xvfb=use_xvfb, user_data_dir=chrome_profile_dir, proxy_server=proxy_server)

        # 执行人类化登录
        success = perform_humanlike_login(driver, username, password)

        # 输出明确的成功/失败标识
        logging.info("=" * 60)
        if success:
            logging.info("✓ 登录检查结果：成功")
            print("=" * 60)
            print("✓ LOGIN_SUCCESS")
            print("=" * 60)
            return_code = 0
        else:
            logging.error("✗ 登录检查结果：失败")
            print("=" * 60)
            print("✗ LOGIN_FAILED")
            print("=" * 60)
            return_code = 1

    except Exception as e:
        logging.exception("执行过程中出现未处理异常。")
        print("=" * 60)
        print("✗ LOGIN_FAILED - 发生异常")
        print("=" * 60)
        return_code = 1
    finally:
        if driver is not None:
            logging.info("关闭浏览器。")
            driver.quit()
        
        # 清理 Xvfb 进程（如果是由我们启动的）
        if xvfb_process is not None:
            try:
                logging.info(f"关闭 Xvfb 进程 (PID: {xvfb_process.pid})")
                xvfb_process.terminate()
                xvfb_process.wait(timeout=5)
            except Exception as e:
                logging.warning(f"关闭 Xvfb 进程时出错: {e}")
                try:
                    xvfb_process.kill()
                except Exception:
                    pass

        logging.info("===== Enrollware 人类化自动登录脚本结束 =====")
        return return_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
