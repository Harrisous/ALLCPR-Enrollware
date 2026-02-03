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
默认使用**可见浏览器**（`headless=False`），便于：
- 观察自动化过程
- 人工排查问题
- 调试 Cloudflare 验证

如需使用 headless 模式，修改 `login_humanlike.py`：
```python
driver = create_chrome_driver(headless=True)
```

## 配置说明

### 环境变量（.env）
| 变量名 | 说明 | 示例 |
|--------|------|------|
| `USERNAME` | Enrollware 登录邮箱 | `user@example.com` |
| `PASSWORD` | Enrollware 登录密码 | `your_password` |

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
**症状**：日志显示 "未检测到 Cloudflare iframe" 或 "Shadow root not found"

**可能原因**：
- iframe 加载时间较长
- Shadow DOM 结构变化
- 被 Cloudflare 检测为自动化

**解决方案**：
- 检查日志中的详细错误信息
- 增加等待时间（修改 `human_like_delay`）
- 确保反检测脚本正确执行

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

本项目使用 **undetected-chromedriver**，它内置了全面的反检测功能：

| 措施 | 说明 | 实现方式 |
|------|------|----------|
| **隐藏自动化标识** | 完全隐藏 `navigator.webdriver` | undetected-chromedriver 内置 |
| **修改 Chrome 特征** | 移除自动化相关的启动参数 | undetected-chromedriver 自动处理 |
| **CDP 脚本注入** | 在页面加载前注入反检测脚本 | undetected-chromedriver 自动处理 |
| **User-Agent 伪装** | 使用真实的浏览器 User-Agent | undetected-chromedriver 自动处理 |
| **Chrome 指纹修改** | 修改浏览器指纹特征 | undetected-chromedriver 内置 |

**优势**：
- ✅ 无需手动配置复杂的反检测参数
- ✅ 自动处理 ChromeDriver 版本匹配
- ✅ 内置多种反检测技术，比手动配置更可靠
- ✅ 支持指定 Chrome 版本（本项目使用 Chrome 144）

## 更新日志

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
