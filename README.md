# Enrollware 自动登录脚本

使用 Selenium 模拟人类行为自动登录 Enrollware 管理后台，支持绕过 Cloudflare Turnstile 验证。

## 项目简介

本项目实现了一个智能的自动化登录脚本，能够：
- 模拟真实人类的鼠标移动和键盘输入行为
- 自动处理 Cloudflare Turnstile 验证（包括嵌套 Shadow DOM）
- 隐藏自动化特征，避免被反爬虫系统检测
- 提供详细的日志记录，便于调试和排查问题

## 功能特点

### 🤖 人类化行为模拟
- **逐字符输入**：模拟真实打字速度，每个字符随机延迟 50-300ms
- **鼠标轨迹模拟**：使用随机偏移和渐进式移动，模拟人类不精确的鼠标操作
- **操作节奏控制**：在关键步骤之间添加随机延迟，模拟人类思考时间
- **打字错误模拟**：5% 概率模拟打字错误和修正

### 🛡️ 反自动化检测
- **隐藏 `navigator.webdriver`**：完全隐藏自动化标识
- **覆盖浏览器特征**：模拟真实浏览器的 `plugins`、`languages` 等属性
- **Chrome 参数优化**：使用反检测启动参数
- **CDP 脚本注入**：在页面加载前注入反检测脚本

### ☁️ Cloudflare Turnstile 处理
- **自动检测验证框**：智能识别 Cloudflare iframe
- **Shadow DOM 访问**：使用 JavaScript 访问嵌套的 Shadow Root
- **双重 Shadow Root 支持**：处理主页面和 iframe 内的两层 Shadow DOM
- **多种定位策略**：支持通过 checkbox、label 等多种方式点击验证

### 📝 日志记录
- **详细的操作日志**：记录每个步骤的执行情况
- **错误追踪**：完整的异常堆栈信息
- **文件日志**：所有日志同时写入文件和终端

## 技术架构

### 核心技术栈
- **undetected-chromedriver**：专门用于绕过反自动化检测的 ChromeDriver 包装器
- **Selenium WebDriver**：浏览器自动化框架（通过 undetected-chromedriver 使用）
- **Chrome 144**：支持的 Chrome 浏览器版本
- **Python 3.10+**：开发语言

### 关键技术点

#### 1. Shadow DOM 访问
Cloudflare Turnstile 的 checkbox 位于两层 Shadow Root 中：
```
主页面
  └─ div#loginTurnstile (第一个 Shadow Root)
      └─ iframe
          └─ body (第二个 Shadow Root)
              └─ input[type="checkbox"]
```

脚本使用 JavaScript `execute_script` 访问 Shadow DOM：
```javascript
// 查找 Shadow Host
const shadowRoot = element.shadowRoot;
// 在 Shadow Root 中查找元素
const checkbox = shadowRoot.querySelector('input[type="checkbox"]');
```

#### 2. 反检测机制
```python
# 隐藏 navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

# 覆盖其他自动化特征
window.chrome = { runtime: {} };
delete Object.getPrototypeOf(navigator).webdriver;
```

## 安装步骤

### 1. 环境要求
- Python 3.10 或更高版本
- Google Chrome 浏览器（已安装）
- WSL/Linux 环境（推荐）或 Windows

### 2. 创建虚拟环境
```bash
cd /path/to/enrollware_login
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 安装依赖
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

依赖包：
- `selenium`：浏览器自动化框架
- `python-dotenv`：环境变量管理
- `undetected-chromedriver`：反检测 ChromeDriver（支持 Chrome 144）

### 4. 配置环境变量
创建 `.env` 文件：
```env
USERNAME=your_email@example.com
PASSWORD=your_password
```

**注意**：`.env` 文件包含敏感信息，不要提交到版本控制系统。

## 使用方法

### 基本使用
```bash
# 激活虚拟环境
source venv/bin/activate

# 运行脚本
python login_humanlike.py
```

### 运行流程
1. **打开登录页面**：自动访问 `https://www.enrollware.com/admin/login.aspx`
2. **填写凭据**：从 `.env` 读取用户名和密码，模拟人类输入
3. **点击登录**：模拟鼠标移动到 Sign In 按钮并点击
4. **处理验证**：自动检测并处理 Cloudflare Turnstile 验证
5. **验证结果**：检查是否成功登录到 `class-list.aspx` 页面

### 日志输出
脚本运行时会：
- 在终端显示实时日志
- 将日志保存到 `login_humanlike.log` 文件

### 浏览器模式

#### 可见模式（推荐用于调试）
默认使用**可见浏览器**（`headless=False`），便于：
- 观察自动化过程
- 人工排查问题
- 调试 Cloudflare 验证

#### Headless 模式（无头模式）
Headless 模式适合在服务器环境运行，但 Cloudflare 更容易检测 headless 浏览器。

**方法 1：使用 Xvfb（推荐，Linux 系统）**
Xvfb 创建一个虚拟显示，让浏览器以为有真实显示器，从而绕过 Cloudflare 检测：

```bash
# 1. 安装 Xvfb（如果未安装）
sudo apt-get install xvfb

# 2. 设置环境变量启用 Xvfb
export HEADLESS=true
export USE_XVFB=true

# 3. 运行脚本
python login_humanlike.py
```

**方法 2：标准 Headless 模式**
如果无法使用 Xvfb，可以使用标准 headless 模式（已优化反检测参数）：

```bash
export HEADLESS=true
python login_humanlike.py
```

**环境变量说明：**
- `HEADLESS=true`：启用 headless 模式（默认：`true`）
- `USE_XVFB=true`：启用 Xvfb 虚拟显示（仅 Linux，默认：`false`）
- `CHROME_PROFILE_DIR=./chrome_profile`：指定 Chrome profile 目录（用于保存 cookies、缓存等）

#### Chrome Profile 方法（推荐用于 AWS 环境）
如果本地可以成功登录但 AWS 环境不行（IP 被 Cloudflare 标记），可以使用 Chrome Profile 方法：

**步骤 1：在本地保存 Profile**
```bash
# 1. 在本地运行一次成功登录
export HEADLESS=false
export CHROME_PROFILE_DIR=./chrome_profile
python login_humanlike.py

# 2. 登录成功后，chrome_profile 目录会包含 cookies、缓存等信息
```

**步骤 2：将 Profile 复制到 AWS**
```bash
# 将整个 chrome_profile 目录打包
tar -czf chrome_profile.tar.gz chrome_profile/

# 上传到 AWS（使用 scp 或其他方式）
scp chrome_profile.tar.gz user@aws-server:/path/to/enrollware_login/
```

**步骤 3：在 AWS 中使用 Profile**
```bash
# 在 AWS 环境中解压
cd /path/to/enrollware_login
tar -xzf chrome_profile.tar.gz

# 设置环境变量使用 profile
export HEADLESS=true
export USE_XVFB=true
export CHROME_PROFILE_DIR=./chrome_profile
python login_humanlike.py
```

**优势：**
- ✅ Profile 包含 Cloudflare 验证通过的 cookies 和浏览器指纹
- ✅ 可以绕过 AWS IP 被标记的问题
- ✅ 不需要配置代理服务器
- ✅ 一次保存，多次使用

## 配置说明

### 环境变量

#### .env 文件（敏感信息）
| 变量名 | 说明 | 示例 |
|--------|------|------|
| `USERNAME` | Enrollware 登录邮箱 | `user@example.com` |
| `PASSWORD` | Enrollware 登录密码 | `your_password` |

#### 系统环境变量（运行模式）
| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `HEADLESS` | 是否使用 headless 模式 | `true` | `true` / `false` |
| `USE_XVFB` | 是否使用 Xvfb 虚拟显示（仅 Linux） | `false` | `true` / `false` |
| `CHROME_PROFILE_DIR` | Chrome profile 目录路径（保存 cookies、缓存等） | 临时目录 | `./chrome_profile` |
| `PROXY_SERVER` | 代理服务器地址（用于绕过 AWS IP 检测） | 无 | `http://proxy.example.com:8080` 或 `socks5://127.0.0.1:8080` |

**使用示例：**
```bash
# 可见模式（调试用）
export HEADLESS=false
python login_humanlike.py

# Headless + Xvfb（推荐，绕过 Cloudflare）
export HEADLESS=true
export USE_XVFB=true
python login_humanlike.py

# 标准 Headless（已优化，但可能被检测）
export HEADLESS=true
python login_humanlike.py

# 使用 Chrome Profile（推荐用于 AWS 环境）
export HEADLESS=false
export CHROME_PROFILE_DIR=./chrome_profile
python login_humanlike.py  # 本地成功登录后，复制 profile 到 AWS

# 使用代理服务器（推荐用于 AWS IP 被标记的情况）
export PROXY_SERVER=http://your-proxy-server.com:8080
export HEADLESS=true
export USE_XVFB=true
python login_humanlike.py
```

### 可调参数
在 `login_humanlike.py` 中可以调整：
- **输入延迟**：`type_humanlike()` 函数的 `min_delay` 和 `max_delay`
- **鼠标移动延迟**：`human_like_delay()` 函数的延迟范围
- **等待超时**：`WebDriverWait` 的超时时间（默认 20 秒）

## 故障排查

### 常见问题

#### 1. ChromeDriver 版本不匹配
**症状**：`SessionNotCreatedException` 或版本错误

**解决方案**：
- `undetected-chromedriver` 会自动下载匹配的 ChromeDriver
- 脚本已配置为使用 Chrome 144 版本（`version_main=144`）
- 如果指定版本失败，脚本会自动检测系统安装的 Chrome 版本
- 确保 Chrome 浏览器已安装并更新到 144 版本

#### 2. Cloudflare 验证失败
**症状**：日志显示 "未检测到 Cloudflare iframe" 或 "Shadow root not found"，或在 headless 模式下无法通过验证

**可能原因**：
- iframe 加载时间较长
- Shadow DOM 结构变化
- 被 Cloudflare 检测为自动化（headless 模式更容易被检测）

**解决方案**：
- **推荐方案**：使用 Xvfb 虚拟显示（Linux 系统）
  ```bash
  sudo apt-get install xvfb
  export HEADLESS=true
  export USE_XVFB=true
  python login_humanlike.py
  ```
- 检查日志中的详细错误信息
- 增加等待时间（修改 `human_like_delay`）
- 确保反检测脚本正确执行
- 如果使用 headless 模式，脚本已自动注入额外的反检测 CDP 脚本

#### 3. 元素定位失败
**症状**：`TimeoutException` 或 `NoSuchElementException`

**解决方案**：
- 检查页面结构是否变化
- 增加 `WebDriverWait` 的超时时间
- 查看日志中的元素定位信息

#### 4. 登录后仍在登录页
**症状**：URL 仍为 `login.aspx`

**可能原因**：
- Cloudflare 验证未通过
- 凭据错误
- 需要额外的验证步骤

**解决方案**：
- 脚本会保持浏览器打开，便于人工排查
- 检查浏览器控制台的错误信息
- 验证 `.env` 中的凭据是否正确

#### 5. AWS 环境无法通过 Cloudflare 验证（IP 被标记）
**症状**：本地可以成功登录，但在 AWS EC2 上失败，Cloudflare 验证无法通过

**可能原因**：
- AWS IP 地址被 Cloudflare 标记为数据中心 IP
- Cloudflare 对 AWS IP 段有更严格的检测

**解决方案（推荐）：使用 Chrome Profile**
1. **在本地成功登录一次**：
   ```bash
   export HEADLESS=false
   export CHROME_PROFILE_DIR=./chrome_profile
   python login_humanlike.py
   ```

2. **打包 profile 目录**：
   ```bash
   tar -czf chrome_profile.tar.gz chrome_profile/
   ```

3. **上传到 AWS**：
   ```bash
   scp chrome_profile.tar.gz user@aws-server:/path/to/enrollware_login/
   ```

4. **在 AWS 中使用**：
   ```bash
   cd /path/to/enrollware_login
   tar -xzf chrome_profile.tar.gz
   export HEADLESS=true
   export USE_XVFB=true
   export CHROME_PROFILE_DIR=./chrome_profile
   python login_humanlike.py
   ```

**为什么有效**：
- Chrome Profile 包含 Cloudflare 验证通过的 cookies
- 包含浏览器指纹信息，让 Cloudflare 认为这是同一个浏览器
- 即使 IP 不同，也能通过验证

**注意事项**：
- Profile 目录可能较大（几十到几百 MB），需要确保有足够空间
- Profile 中的 cookies 可能会过期，如果失败需要重新生成
- 建议定期更新 profile（每周或每月）

**解决方案 2：使用代理服务器（推荐）**

如果 Chrome Profile 方法无效，可以使用代理服务器绕过 AWS IP 检测：

1. **搭建本地代理服务器**（详见 `proxy_setup.md`）：
   ```bash
   # 在本地 WSL 中启动代理服务器
   python3 local_proxy.py --host 0.0.0.0 --port 8080 --allowed-ips YOUR_AWS_EC2_IP
   ```

2. **配置路由器端口转发**（如果有公网 IP）：
   - 将外部端口 8080 转发到本地代理服务器

3. **在 AWS EC2 上使用代理**：
   ```bash
   export PROXY_SERVER=http://your-public-ip:8080
   export HEADLESS=true
   export USE_XVFB=true
   python login_humanlike.py
   ```

**为什么有效**：
- 代理服务器使用本地网络 IP（通常是住宅 IP），不会被 Cloudflare 标记
- AWS EC2 通过代理访问，目标网站看到的是代理服务器的 IP

**详细步骤**：请参考 `proxy_setup.md` 文件，包含三种代理搭建方案：
- 方案 A：Python 简单代理（有公网 IP）
- 方案 B：SSH Tunnel（无需公网 IP）
- 方案 C：Cloudflare Tunnel（无公网 IP）

**⚠️ SSH Tunnel 连接超时问题？**
如果使用方案 B（SSH Tunnel）时遇到 `Connection timed out` 错误，请参考：
- **快速修复指南**: `QUICK_FIX_SSH.md` - 最常见的解决方案
- **完整故障排查**: `SSH_TROUBLESHOOTING.md` - 详细的诊断步骤

### 调试技巧

1. **查看详细日志**：
   ```bash
   tail -f login_humanlike.log
   ```

2. **使用可见浏览器**：
   - 默认已启用，可以观察自动化过程
   - 脚本失败时会保持浏览器打开

3. **检查 Shadow DOM**：
   - 在浏览器开发者工具中检查 Shadow Root
   - 确认 checkbox 的完整路径

## 项目结构

```
enrollware_login/
├── login_humanlike.py    # 主脚本文件
├── local_proxy.py        # 本地代理服务器（可选）
├── proxy_setup.md        # 代理搭建详细指南
├── requirements.txt      # Python 依赖包
├── .env                  # 环境变量配置（不提交到 Git）
├── login_humanlike.log   # 运行日志
├── README.md            # 项目文档
└── venv/                # 虚拟环境目录
```

## 注意事项

### ⚠️ 重要提醒

1. **合规使用**：
   - 仅用于个人账户的自动化操作
   - 遵守 Enrollware 的服务条款
   - 不要用于大规模自动化或爬虫

2. **安全性**：
   - `.env` 文件包含敏感信息，不要提交到 Git
   - 定期更新密码
   - 不要在公共仓库中暴露凭据

3. **稳定性**：
   - Cloudflare 可能会更新检测机制
   - 页面结构可能发生变化
   - 建议定期测试和更新脚本

4. **性能**：
   - 脚本使用人类化延迟，执行时间较长（约 10-20 秒）
   - 这是为了模拟真实用户行为，避免被检测

## 技术细节

### Cloudflare Turnstile 处理流程

1. **检测 iframe**：
   - 使用多种选择器查找 Cloudflare iframe
   - 等待 iframe 加载完成

2. **切换到 iframe**：
   ```python
   driver.switch_to.frame(cloudflare_iframe)
   ```

3. **访问 Shadow DOM**：
   ```javascript
   // 在 iframe 的 body 中查找 Shadow Host
   const shadowRoot = body.children[0].shadowRoot;
   // 在 Shadow Root 中查找 checkbox
   const checkbox = shadowRoot.querySelector('input[type="checkbox"]');
   ```

4. **点击验证**：
   - 滚动到 checkbox
   - 执行点击操作
   - 等待验证完成

### 反检测措施详解

本项目使用 **undetected-chromedriver**，它内置了全面的反检测功能，并在此基础上进行了额外优化：

| 措施 | 说明 | 实现方式 |
|------|------|----------|
| **隐藏自动化标识** | 完全隐藏 `navigator.webdriver` | undetected-chromedriver 内置 + CDP 脚本 |
| **修改 Chrome 特征** | 移除自动化相关的启动参数 | undetected-chromedriver 自动处理 |
| **CDP 脚本注入** | 在页面加载前注入反检测脚本 | undetected-chromedriver + 自定义 CDP 脚本 |
| **User-Agent 伪装** | 移除 HeadlessChrome 标识 | 自定义 User-Agent（headless 模式） |
| **Chrome 指纹修改** | 修改浏览器指纹特征 | undetected-chromedriver 内置 |
| **Xvfb 虚拟显示** | 绕过 headless 检测（Linux） | Xvfb 虚拟显示服务器 |
| **浏览器参数优化** | 添加反检测启动参数 | `--disable-blink-features=AutomationControlled` 等 |
| **Chrome Profile 复用** | 使用保存的 profile 绕过 IP 标记 | `CHROME_PROFILE_DIR` 环境变量 |

**Headless 模式特殊优化**：
- ✅ 使用 `--headless=new`（Chrome 109+ 的新 headless 模式）
- ✅ 注入额外的 CDP 脚本隐藏 `navigator.webdriver`、`window.chrome` 等
- ✅ 覆盖 `navigator.plugins`、`navigator.languages` 等指纹特征
- ✅ 移除 User-Agent 中的 "HeadlessChrome" 标识
- ✅ **推荐**：使用 Xvfb 虚拟显示，让浏览器以为有真实显示器

**优势**：
- ✅ 无需手动配置复杂的反检测参数
- ✅ 自动处理 ChromeDriver 版本匹配
- ✅ 内置多种反检测技术，比手动配置更可靠
- ✅ 支持指定 Chrome 版本（本项目使用 Chrome 144）
- ✅ Headless 模式下的 Cloudflare 绕过成功率显著提升

## 更新日志

### v1.4.0 (2026-02-04)
- ✅ **代理服务器支持**：添加代理服务器配置支持，可以绕过 AWS IP 被 Cloudflare 检测
- ✅ **本地代理工具**：新增 `local_proxy.py` 简单 HTTP/HTTPS 代理服务器
- ✅ **代理搭建指南**：新增 `proxy_setup.md` 详细指南，包含三种代理搭建方案
- ✅ **代码更新**：`create_chrome_driver` 函数支持 `proxy_server` 参数
- ✅ **环境变量**：新增 `PROXY_SERVER` 环境变量配置

### v1.3.0 (2026-02-03)
- ✅ **Chrome Profile 支持**：添加 Chrome profile 目录支持，可以保存和复用 cookies、缓存
- ✅ **AWS IP 绕过方案**：通过使用本地保存的 profile，绕过 AWS IP 被 Cloudflare 标记的问题
- ✅ **Profile 持久化**：支持通过 `CHROME_PROFILE_DIR` 环境变量指定 profile 目录
- ✅ **文档完善**：添加详细的 Chrome Profile 使用说明和故障排查指南

### v1.2.0 (2026-02-03)
- ✅ **Headless 模式优化**：大幅改进 headless 模式下的 Cloudflare 绕过成功率
- ✅ **Xvfb 支持**：添加 Xvfb 虚拟显示支持（Linux），推荐用于 headless 模式
- ✅ **增强反检测**：添加更多 CDP 脚本和浏览器参数来隐藏自动化特征
- ✅ **User-Agent 优化**：移除 HeadlessChrome 标识，使用真实浏览器 User-Agent
- ✅ **环境变量控制**：通过 `HEADLESS` 和 `USE_XVFB` 环境变量灵活控制运行模式

### v1.1.0 (2026-01-29)
- ✅ 迁移到 `undetected-chromedriver`，简化反检测配置
- ✅ 支持 Chrome 144 版本
- ✅ 自动版本检测和回退机制
- ✅ 改进的浏览器启动稳定性

### v1.0.0 (2026-01-29)
- ✅ 实现基本的人类化登录流程
- ✅ 支持 Cloudflare Turnstile 验证处理
- ✅ 实现 Shadow DOM 访问
- ✅ 添加反自动化检测措施
- ✅ 完整的日志记录系统

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

本项目仅供学习和个人使用。

## 联系方式

如有问题或建议，请通过 Issue 反馈。

---

**免责声明**：本项目仅供学习和技术研究使用。使用者需自行承担使用本脚本的所有风险和责任。请遵守相关网站的服务条款和法律法规。
