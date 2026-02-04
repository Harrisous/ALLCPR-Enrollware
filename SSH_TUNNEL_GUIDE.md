# SSH Tunnel 设置指南（方案 B）

本指南将帮助你设置 SSH Tunnel，让 AWS EC2 通过你的本地网络访问 Enrollware。

## 你的网络信息

- **WSL 用户名**: `harry`
- **Windows 主机 IP**: `192.168.86.100`
- **公网 IP**: `136.56.72.172`
- **路由器地址**: `192.168.86.1`

---

## 步骤 1：在 WSL 中安装和配置 SSH 服务器

### 1.1 安装 OpenSSH Server

在 WSL 终端中运行：

```bash
sudo apt-get update
sudo apt-get install openssh-server -y
```

### 1.2 启动 SSH 服务

```bash
# 启动 SSH 服务
sudo systemctl start ssh

# 设置开机自启
sudo systemctl enable ssh

# 检查服务状态
sudo systemctl status ssh
```

如果看到 "Active: active (running)"，说明 SSH 服务已启动。

### 1.3 配置 SSH 允许端口转发

编辑 SSH 配置文件：

```bash
sudo nano /etc/ssh/sshd_config
```

找到以下行（如果存在），确保设置为 `yes`：
```
AllowTcpForwarding yes
GatewayPorts yes
```

如果这些行不存在，在文件末尾添加：
```
# 允许端口转发
AllowTcpForwarding yes
GatewayPorts yes
```

保存文件（`Ctrl+O`，然后 `Enter`，然后 `Ctrl+X`）

重启 SSH 服务：
```bash
sudo systemctl restart ssh
```

### 1.4 检查防火墙（如果需要）

如果启用了防火墙，确保 SSH 端口（22）已开放：

```bash
# 检查防火墙状态
sudo ufw status

# 如果防火墙已启用，开放 SSH 端口
sudo ufw allow 22/tcp
```

---

## 步骤 2：配置路由器端口转发（SSH 端口 22）

虽然 SSH Tunnel 不需要代理端口转发，但需要确保 SSH 端口（22）可以从公网访问。

### 2.1 访问路由器管理界面

在浏览器中打开：
```
http://192.168.86.1
```

### 2.2 查找端口转发设置

不同品牌的路由器位置不同：

**TP-Link:**
- 高级功能 → 虚拟服务器 → 添加新条目

**华硕 (ASUS):**
- 高级设置 → 虚拟服务器 → 添加

**小米:**
- 高级设置 → 端口转发 → 添加规则

**华为:**
- 高级功能 → NAT → 虚拟服务器 → 添加

### 2.3 添加 SSH 端口转发规则

添加以下规则：
- **服务名称**: SSH（或任意名称）
- **外部端口**: `22`
- **内部 IP**: `192.168.86.100`（你的 Windows 主机 IP）
- **内部端口**: `22`
- **协议**: TCP
- **启用**: 是

保存设置。

---

## 步骤 3：测试 SSH 连接

### 3.1 从本地测试（可选）

在 WSL 中测试 SSH 服务是否正常：

```bash
# 测试本地 SSH 连接
ssh harry@localhost

# 如果连接成功，输入 exit 退出
exit
```

### 3.2 从 AWS EC2 测试连接

在 AWS EC2 上运行：

```bash
# 测试 SSH 连接（不建立隧道，只测试连接）
ssh -v harry@136.56.72.172
```

如果连接成功，你会看到 SSH 提示符或要求输入密码。

**如果连接失败**，可能的原因：
1. 路由器端口转发未配置
2. Windows 防火墙阻止了端口 22
3. SSH 服务未运行

---

## 步骤 4：从 AWS EC2 建立 SSH Tunnel

### 4.1 建立 SSH 隧道

在 AWS EC2 上运行：

```bash
# 建立 SSH 隧道，创建本地 SOCKS5 代理
ssh -D 8080 -N -f harry@136.56.72.172
```

**参数说明：**
- `-D 8080`: 创建本地 SOCKS5 代理，监听 `127.0.0.1:8080`
- `-N`: 不执行远程命令，只建立隧道
- `-f`: 后台运行

**如果提示输入密码**，输入你的 WSL 用户密码（harry 的密码）。

### 4.2 验证隧道是否建立

检查本地是否监听端口 8080：

```bash
# 在 AWS EC2 上运行
netstat -tlnp | grep 8080
# 或
ss -tlnp | grep 8080
```

如果看到 `127.0.0.1:8080`，说明隧道已建立。

### 4.3 测试代理是否工作

```bash
# 测试通过代理访问网站
curl --socks5 127.0.0.1:8080 https://www.google.com

# 检查通过代理访问的 IP
curl --socks5 127.0.0.1:8080 https://api.ipify.org
```

如果返回的是你的公网 IP `136.56.72.172`，说明代理工作正常。

---

## 步骤 5：配置脚本使用代理

在 AWS EC2 上设置环境变量：

```bash
# 设置代理
export PROXY_SERVER=socks5://127.0.0.1:8080

# 设置其他环境变量
export HEADLESS=true
export USE_XVFB=true

# 运行脚本
python login_humanlike.py
```

---

## 步骤 6：保持 SSH 连接（可选）

SSH 隧道会在连接断开时关闭。如果需要保持连接，可以使用以下方法：

### 方法 1：使用 autossh（推荐）

在 AWS EC2 上安装 autossh：

```bash
sudo apt-get install autossh -y
```

使用 autossh 建立隧道：

```bash
autossh -M 20000 -D 8080 -N -f harry@136.56.72.172
```

`autossh` 会自动重连，保持隧道稳定。

### 方法 2：使用 screen 或 tmux

```bash
# 安装 screen
sudo apt-get install screen -y

# 创建新会话
screen -S ssh_tunnel

# 在 screen 中建立 SSH 隧道
ssh -D 8080 -N harry@136.56.72.172

# 按 Ctrl+A 然后 D 分离会话（保持后台运行）
```

---

## 故障排查

### 问题 1：无法从 AWS EC2 SSH 连接到公网 IP

**症状**: `Connection refused` 或 `Connection timed out`

**解决方案**:
1. 检查 SSH 服务是否运行：
   ```bash
   # 在 WSL 中
   sudo systemctl status ssh
   ```

2. 检查路由器端口转发是否正确配置（外部端口 22 → 内部 IP 192.168.86.100:22）

3. 检查 Windows 防火墙是否阻止端口 22：
   - 打开 Windows 防火墙设置
   - 添加入站规则，允许端口 22

4. 测试从本地网络访问：
   ```bash
   # 在 Windows PowerShell 中
   Test-NetConnection -ComputerName 192.168.86.100 -Port 22
   ```

### 问题 2：SSH 连接成功但代理不工作

**解决方案**:
1. 检查隧道是否建立：
   ```bash
   # 在 AWS EC2 上
   netstat -tlnp | grep 8080
   ```

2. 检查代理配置是否正确：
   ```bash
   export PROXY_SERVER=socks5://127.0.0.1:8080
   ```

3. 测试代理：
   ```bash
   curl --socks5 127.0.0.1:8080 https://www.google.com
   ```

### 问题 3：SSH 连接频繁断开

**解决方案**:
1. 使用 `autossh`（见步骤 6）
2. 在 SSH 配置中添加保持连接参数：
   ```bash
   # 在 AWS EC2 上编辑 ~/.ssh/config
   nano ~/.ssh/config
   
   # 添加：
   Host 136.56.72.172
       ServerAliveInterval 60
       ServerAliveCountMax 3
   ```

### 问题 4：需要输入密码，想使用密钥认证

**创建 SSH 密钥对**（在 AWS EC2 上）：

```bash
# 生成密钥对（如果还没有）
ssh-keygen -t rsa -b 4096

# 复制公钥到 WSL
ssh-copy-id harry@136.56.72.172
```

之后建立隧道就不需要输入密码了。

---

## 快速参考

### 在 WSL 中（一次性设置）：
```bash
sudo apt-get install openssh-server -y
sudo systemctl start ssh
sudo systemctl enable ssh
sudo nano /etc/ssh/sshd_config  # 添加 AllowTcpForwarding yes
sudo systemctl restart ssh
```

### 在 AWS EC2 上（每次使用）：
```bash
# 建立隧道
ssh -D 8080 -N -f harry@136.56.72.172

# 设置代理并运行脚本
export PROXY_SERVER=socks5://127.0.0.1:8080
export HEADLESS=true
export USE_XVFB=true
python login_humanlike.py
```

---

## 下一步

完成设置后，在 AWS EC2 上运行脚本测试。如果遇到问题，请查看故障排查部分或告诉我具体的错误信息。
