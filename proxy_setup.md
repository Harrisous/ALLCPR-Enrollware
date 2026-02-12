# 本地代理服务器搭建指南

本指南介绍如何在本地搭建代理服务器，让 AWS EC2 上的脚本通过代理访问 Enrollware，从而绕过 AWS IP 被 Cloudflare 检测的问题。

## 目录

1. [方案 A：Python 简单代理（推荐）](#方案-a-python-简单代理推荐)
2. [方案 B：SSH Tunnel](#方案-b-ssh-tunnel)
3. [方案 C：Cloudflare Tunnel（无公网 IP）](#方案-c-cloudflare-tunnel无公网-ip)
4. [配置脚本使用代理](#配置脚本使用代理)
5. [故障排查](#故障排查)

---

## 方案 A：Python 简单代理（推荐）

### 适用场景
- ✅ 有公网 IP（你的公网 IP: `136.56.72.172`）
- ✅ 可以配置路由器端口转发
- ✅ 最简单的方案

### 步骤 1：启动本地代理服务器

在 WSL 中运行：

```bash
cd /home/harry/github_ALLCPR/ALLCPR-Enrollware

# 方式 1：允许所有 IP 访问（不推荐，仅用于测试）
python3 local_proxy.py

# 方式 2：只允许 AWS EC2 IP 访问（推荐）
# 先获取你的 AWS EC2 公网 IP，然后：
python3 local_proxy.py --host 0.0.0.0 --port 8080 --allowed-ips YOUR_AWS_EC2_IP
```

**示例：**
```bash
# 假设你的 AWS EC2 IP 是 54.123.45.67
python3 local_proxy.py --host 0.0.0.0 --port 8080 --allowed-ips 54.123.45.67
```

代理服务器会监听 `0.0.0.0:8080`，你应该看到：
```
代理服务器已启动
监听地址: 0.0.0.0:8080
允许的 IP: 54.123.45.67
```

### 步骤 2：配置路由器端口转发

1. **登录路由器管理界面**
   - 通常是 `http://192.168.1.1` 或 `http://192.168.0.1`
   - 查看路由器背面标签获取默认地址

2. **找到端口转发/虚拟服务器设置**
   - 不同路由器界面不同，常见名称：
     - "端口转发" / "Port Forwarding"
     - "虚拟服务器" / "Virtual Server"
     - "NAT" / "应用" / "Applications"

3. **添加端口转发规则**
   - **外部端口**：`8080`（或你选择的其他端口）
   - **内部 IP**：你的 WSL 主机 IP（在 Windows 中运行 `ipconfig` 查看，通常是 `192.168.x.x`）
   - **内部端口**：`8080`
   - **协议**：TCP
   - **启用**：是

4. **保存设置**

### 步骤 3：测试代理连接

在 AWS EC2 上测试：

```bash
# 测试代理是否可访问
curl -x http://136.56.72.172:8080 https://www.enrollware.com

# 或使用环境变量
export http_proxy=http://136.56.72.172:8080
export https_proxy=http://136.56.72.172:8080
curl https://www.enrollware.com
```

如果看到网页内容，说明代理工作正常。

### 步骤 4：配置脚本使用代理

在 AWS EC2 上设置环境变量：

```bash
export PROXY_SERVER=http://136.56.72.172:8080
python login_humanlike.py
```

或在 `.env` 文件中添加（不推荐，因为 IP 可能变化）：
```bash
PROXY_SERVER=http://136.56.72.172:8080
```

---

## 方案 B：SSH Tunnel

### 适用场景
- ✅ 不需要公网 IP
- ✅ 不需要配置路由器
- ✅ 更安全（加密连接）
- ⚠️ 需要保持 SSH 连接

### 步骤 1：在 WSL 中安装 SSH 服务器

```bash
# 安装 OpenSSH Server
sudo apt-get update
sudo apt-get install openssh-server -y

# 启动 SSH 服务
sudo systemctl start ssh
sudo systemctl enable ssh

# 检查 SSH 服务状态
sudo systemctl status ssh
```

### 步骤 2：配置 SSH 服务器（可选，提高安全性）

编辑 `/etc/ssh/sshd_config`：

```bash
sudo nano /etc/ssh/sshd_config
```

添加或修改：
```
# 允许端口转发
AllowTcpForwarding yes
GatewayPorts yes

# 只允许特定用户（可选）
AllowUsers your_username
```

重启 SSH 服务：
```bash
sudo systemctl restart ssh
```

### 步骤 3：从 AWS EC2 建立 SSH 隧道

在 AWS EC2 上运行：

```bash
# 建立 SSH 隧道，创建本地 SOCKS5 代理
ssh -D 8080 -N -f user@136.56.72.172

# 参数说明：
# -D 8080: 创建本地 SOCKS5 代理，监听 127.0.0.1:8080
# -N: 不执行远程命令
# -f: 后台运行
```

**注意：** 你需要：
1. 在 WSL 中配置 SSH 密钥认证，或
2. 使用密码认证（需要输入密码）

### 步骤 4：配置脚本使用本地 SOCKS5 代理

在 AWS EC2 上：

```bash
export PROXY_SERVER=socks5://127.0.0.1:8080
python login_humanlike.py
```

---

## 方案 C：Cloudflare Tunnel（无公网 IP）

### 适用场景
- ✅ 没有公网 IP
- ✅ 无法配置路由器
- ✅ 自动处理 NAT 穿透

### 步骤 1：注册 Cloudflare 账户

1. 访问 https://dash.cloudflare.com/sign-up
2. 注册免费账户（不需要域名）

### 步骤 2：安装 cloudflared

在 WSL 中：

```bash
# 下载 cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb

# 安装
sudo dpkg -i cloudflared-linux-amd64.deb

# 验证安装
cloudflared --version
```

### 步骤 3：创建隧道

```bash
# 登录 Cloudflare
cloudflared tunnel login

# 创建隧道
cloudflared tunnel create proxy-tunnel

# 配置隧道（创建配置文件）
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << EOF
tunnel: proxy-tunnel
credentials-file: ~/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  - hostname: proxy-tunnel.your-domain.cf
    service: http://localhost:8080
  - service: http_status:404
EOF
```

### 步骤 4：启动本地代理和 Cloudflare Tunnel

**终端 1：启动本地代理**
```bash
python3 local_proxy.py --host 127.0.0.1 --port 8080
```

**终端 2：启动 Cloudflare Tunnel**
```bash
cloudflared tunnel run proxy-tunnel
```

### 步骤 5：配置脚本使用 Cloudflare Tunnel

在 AWS EC2 上：

```bash
export PROXY_SERVER=http://proxy-tunnel.your-domain.cf:8080
python login_humanlike.py
```

---

## 配置脚本使用代理

### 方法 1：环境变量（推荐）

在 AWS EC2 上：

```bash
# HTTP 代理
export PROXY_SERVER=http://your-proxy-ip:8080

# SOCKS5 代理
export PROXY_SERVER=socks5://127.0.0.1:8080

# 运行脚本
python login_humanlike.py
```

### 方法 2：.env 文件

在 `.env` 文件中添加：

```bash
PROXY_SERVER=http://your-proxy-ip:8080
```

**注意：** 如果 IP 地址会变化，建议使用环境变量而不是 `.env` 文件。

### 验证代理配置

脚本启动时会显示：

```
检测到代理服务器配置: http://your-proxy-ip:8080
将使用代理服务器访问网站，以绕过 AWS IP 被 Cloudflare 检测的问题
配置代理服务器: http://your-proxy-ip:8080
代理服务器已配置，将使用代理访问网站以绕过 AWS IP 检测
```

---

## 故障排查

### 问题 1：无法连接到代理服务器

**症状：** `Connection refused` 或 `Connection timed out`

**解决方案：**
1. 检查代理服务器是否正在运行：
   ```bash
   # 在 WSL 中
   netstat -tlnp | grep 8080
   ```

2. 检查防火墙设置：
   ```bash
   # Ubuntu/Debian
   sudo ufw allow 8080/tcp
   sudo ufw status
   ```

3. 检查路由器端口转发是否正确配置

4. 测试从本地访问：
   ```bash
   # 在 WSL 中测试本地代理
   curl -x http://127.0.0.1:8080 https://www.google.com
   ```

### 问题 2：代理连接成功但脚本仍然失败

**可能原因：**
- 代理服务器 IP 也被标记
- 代理配置格式错误

**解决方案：**
1. 检查代理配置格式：
   - HTTP: `http://host:port`
   - SOCKS5: `socks5://host:port`

2. 测试代理是否真的在工作：
   ```bash
   # 在 AWS EC2 上
   curl -x http://your-proxy:8080 https://www.enrollware.com
   ```

3. 查看脚本日志，确认代理是否被使用

### 问题 3：SSH Tunnel 连接超时（Connection timed out）

**症状：** 在 AWS EC2 上执行 `ssh -D 8080 -N -f user@136.56.72.172` 时出现：
```
ssh: connect to host 136.56.72.172 port 22: Connection timed out
```

**可能原因和解决方案：**

#### 原因 1：路由器端口转发未配置（最常见）

SSH Tunnel 需要从公网访问你的 WSL，必须配置路由器端口转发。

**检查步骤：**
1. 登录路由器管理界面（通常是 `http://192.168.86.1`）
2. 查找"端口转发"或"虚拟服务器"设置
3. 确认是否有以下规则：
   - **外部端口**: `22`
   - **内部 IP**: `192.168.86.100`（你的 Windows 主机 IP）
   - **内部端口**: `22`
   - **协议**: TCP

**如果没有配置，添加规则：**
- TP-Link: 高级功能 → 虚拟服务器 → 添加新条目
- 华硕: 高级设置 → 虚拟服务器 → 添加
- 小米: 高级设置 → 端口转发 → 添加规则
- 华为: 高级功能 → NAT → 虚拟服务器 → 添加

**windows 转wsl**
```bash
# 步骤 1：获取 WSL IP 地址
$wslIP = (wsl hostname -I).Trim()
Write-Host "WSL IP: $wslIP"
# 步骤 2：配置 Windows 端口转发
# 删除旧的端口转发规则（如果存在）
netsh interface portproxy delete v4tov4 listenport=22 listenaddress=0.0.0.0

# 添加新的端口转发规则：Windows 端口 22 → WSL IP:22
netsh interface portproxy add v4tov4 listenport=22 listenaddress=0.0.0.0 connectport=22 connectaddress=$wslIP

# 查看配置
netsh interface portproxy show all


#步骤 3：确保防火墙允许
# 确保防火墙规则存在（如果还没有）
New-NetFirewallRule -DisplayName "SSH" -Direction Inbound -LocalPort 22 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
```

**测试端口转发：**
```bash
# 使用在线工具测试（在浏览器中访问）
https://canyouseeme.org
# 输入端口 22，点击 "Check Port"
# 如果显示 "Success"，说明端口转发配置正确
```

#### 原因 2：Windows 防火墙阻止端口 22

Windows 防火墙可能阻止了 SSH 端口的入站连接。

**解决方案（在 Windows PowerShell 中运行）：**
```powershell
# 方法 1：使用图形界面
# 设置 → 隐私和安全性 → Windows 安全中心 → 防火墙和网络保护 → 高级设置
# 入站规则 → 新建规则 → 端口 → TCP → 22 → 允许连接

# 方法 2：使用命令行（以管理员身份运行 PowerShell）
New-NetFirewallRule -DisplayName "SSH" -Direction Inbound -LocalPort 22 -Protocol TCP -Action Allow
```

**测试 Windows 防火墙：**
```powershell
# 在 Windows PowerShell 中测试
Test-NetConnection -ComputerName 192.168.86.100 -Port 22
# 如果显示 TcpTestSucceeded: True，说明端口可访问
```

#### 原因 3：SSH 服务未在 WSL 中运行

**检查 SSH 服务状态：**
```bash
# 在 WSL 中运行
sudo systemctl status ssh
```

**如果服务未运行，启动服务：**
```bash
sudo systemctl start ssh
sudo systemctl enable ssh
```

**检查 SSH 是否监听端口 22：**
```bash
# 在 WSL 中运行
sudo netstat -tlnp | grep :22
# 或
sudo ss -tlnp | grep :22
# 应该看到类似：0.0.0.0:22 或 :::22
```

#### 原因 4：WSL 防火墙阻止（如果启用了 ufw）

**检查防火墙状态：**
```bash
# 在 WSL 中运行
sudo ufw status
```

**如果防火墙已启用，开放 SSH 端口：**
```bash
sudo ufw allow 22/tcp
sudo ufw reload
```

#### 原因 5：SSH 配置问题

**检查 SSH 配置：**
```bash
# 在 WSL 中运行
sudo nano /etc/ssh/sshd_config
```

**确保以下配置存在：**
```
Port 22
AllowTcpForwarding yes
GatewayPorts yes
```

**重启 SSH 服务：**
```bash
sudo systemctl restart ssh
```

#### 原因 6：AWS EC2 安全组阻止出站连接（罕见）

AWS EC2 默认允许所有出站连接，但请确认安全组规则。

**检查方法：**
1. 登录 AWS 控制台 → EC2 → 安全组
2. 检查出站规则是否允许所有流量（0.0.0.0/0）

#### 快速诊断脚本

**在 WSL 中运行诊断脚本：**
```bash
cd /home/harry/github_ALLCPR/ALLCPR-Enrollware
bash troubleshoot_ssh.sh
```

这个脚本会自动检查：
- SSH 服务状态
- 端口监听情况
- SSH 配置
- 防火墙设置
- 本地连接测试

#### 逐步测试流程

1. **测试本地 SSH 连接（在 WSL 中）：**
   ```bash
   ssh harry@localhost
   # 如果成功，输入 exit 退出
   ```

2. **测试从 Windows 访问 WSL（在 Windows PowerShell 中）：**
   ```powershell
   Test-NetConnection -ComputerName 192.168.86.100 -Port 22
   ```

3. **测试从公网访问（使用在线工具）：**
   - 访问 https://canyouseeme.org
   - 输入端口 22
   - 如果显示 "Success"，说明端口转发正确

4. **测试从 AWS EC2 连接（详细模式）：**
   ```bash
   # 在 AWS EC2 上运行
   ssh -v harry@136.56.72.172
   # -v 参数显示详细连接信息，有助于诊断问题
   ```

5. **如果连接成功，建立 SSH 隧道：**
   ```bash
   ssh -D 8080 -N -f harry@136.56.72.172
   ```

#### 替代方案

如果 SSH Tunnel 配置困难，可以考虑：

1. **方案 A：Python 简单代理**（需要路由器端口转发 8080）
   - 更简单，不需要 SSH
   - 详见本文档"方案 A"部分

2. **方案 C：Cloudflare Tunnel**（完全不需要端口转发）
   - 不需要公网 IP
   - 不需要配置路由器
   - 详见本文档"方案 C"部分

### 问题 4：SSH Tunnel 连接断开

**症状：** SSH 连接中断，代理失效

**解决方案：**
1. 使用 `autossh` 保持连接：
   ```bash
   # 安装 autossh
   sudo apt-get install autossh

   # 使用 autossh 建立隧道
   autossh -M 20000 -D 8080 -N -f user@your-ip
   ```

2. 使用 `screen` 或 `tmux` 保持会话：
   ```bash
   screen -S proxy
   ssh -D 8080 -N user@your-ip
   # 按 Ctrl+A 然后 D 分离会话
   ```

3. 配置 SSH 保持连接参数：
   ```bash
   # 在 AWS EC2 上编辑 ~/.ssh/config
   nano ~/.ssh/config
   
   # 添加：
   Host 136.56.72.172
       ServerAliveInterval 60
       ServerAliveCountMax 3
   ```

### 问题 5：端口被占用

**症状：** `Address already in use`

**解决方案：**
1. 查找占用端口的进程：
   ```bash
   sudo lsof -i :8080
   # 或
   sudo netstat -tlnp | grep 8080
   ```

2. 使用其他端口：
   ```bash
   python3 local_proxy.py --port 8888
   ```

### 问题 6：IP 白名单拒绝连接

**症状：** 代理服务器日志显示 "拒绝来自 XXX 的连接"

**解决方案：**
1. 检查 AWS EC2 的公网 IP：
   ```bash
   # 在 AWS EC2 上
   curl ifconfig.me
   ```

2. 更新代理服务器的 IP 白名单：
   ```bash
   # 停止当前代理服务器（Ctrl+C）
   # 重新启动，添加正确的 IP
   python3 local_proxy.py --allowed-ips CORRECT_IP
   ```

---

## 安全建议

1. **使用 IP 白名单**：只允许 AWS EC2 IP 访问代理服务器
2. **使用防火墙**：限制代理端口的访问
3. **定期更新 IP**：如果 AWS EC2 使用弹性 IP，确保白名单是最新的
4. **监控日志**：定期检查代理服务器日志，发现异常访问

---

## 下一步

配置完成后，在 AWS EC2 上运行脚本：

```bash
export PROXY_SERVER=http://136.56.72.172:8080
export HEADLESS=true
export USE_XVFB=true
python login_humanlike.py
```

如果成功，你应该看到脚本通过代理访问 Enrollware，并且能够绕过 Cloudflare 检测。
