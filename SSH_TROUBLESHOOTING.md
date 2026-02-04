# SSH 连接超时故障排查快速指南

当你遇到 `ssh: connect to host 136.56.72.172 port 22: Connection timed out` 错误时，按照以下步骤逐一检查。

## 🔍 快速诊断

### 在 WSL 中运行诊断脚本：
```bash
cd /home/harry/github_ALLCPR/ALLCPR-Enrollware
bash troubleshoot_ssh.sh
```

这个脚本会自动检查大部分常见问题。

---

## ✅ 检查清单

### 1. WSL SSH 服务 ✅

**检查：**
```bash
sudo systemctl status ssh
```

**如果未运行：**
```bash
sudo systemctl start ssh
sudo systemctl enable ssh
```

**验证端口监听：**
```bash
sudo netstat -tlnp | grep :22
# 应该看到类似：0.0.0.0:22
```

---

### 2. SSH 配置 ✅

**检查配置：**
```bash
sudo nano /etc/ssh/sshd_config
```

**确保包含：**
```
Port 22
AllowTcpForwarding yes
GatewayPorts yes
```

**重启服务：**
```bash
sudo systemctl restart ssh
```

**或使用自动配置脚本：**
```bash
sudo bash configure_ssh_forwarding.sh
```

---

### 3. WSL 防火墙 ✅

**检查防火墙状态：**
```bash
sudo ufw status
```

**如果已启用，开放端口：**
```bash
sudo ufw allow 22/tcp
sudo ufw reload
```

---

### 4. Windows 防火墙 ✅

**方法 1：使用 PowerShell 脚本（推荐）**

在 Windows PowerShell（以管理员身份运行）中：
```powershell
cd C:\Users\harry\github_ALLCPR\ALLCPR-Enrollware
.\configure_windows_firewall.ps1
```

**方法 2：手动配置**

1. 打开 Windows 设置 → 隐私和安全性 → Windows 安全中心
2. 点击"防火墙和网络保护" → "高级设置"
3. 点击"入站规则" → "新建规则"
4. 选择"端口" → TCP → 特定本地端口：`22`
5. 选择"允许连接"
6. 完成并命名规则为 "SSH"

**方法 3：使用命令行**

在 PowerShell（管理员）中：
```powershell
New-NetFirewallRule -DisplayName "SSH" -Direction Inbound -LocalPort 22 -Protocol TCP -Action Allow
```

**测试 Windows 防火墙：**
```powershell
Test-NetConnection -ComputerName 192.168.86.100 -Port 22
# 应该显示 TcpTestSucceeded: True
```

---

### 5. 路由器端口转发 ✅（最重要！）

这是**最常见的问题**。SSH Tunnel 需要从公网访问你的 WSL，必须配置路由器端口转发。

**步骤：**

1. **登录路由器管理界面**
   - 地址：`http://192.168.86.1`
   - 或查看路由器背面标签

2. **找到端口转发设置**
   - TP-Link: 高级功能 → 虚拟服务器
   - 华硕: 高级设置 → 虚拟服务器
   - 小米: 高级设置 → 端口转发
   - 华为: 高级功能 → NAT → 虚拟服务器

3. **添加规则**
   - **服务名称**: SSH（或任意名称）
   - **外部端口**: `22`
   - **内部 IP**: `192.168.86.100`（你的 Windows 主机 IP）
   - **内部端口**: `22`
   - **协议**: TCP
   - **启用**: 是

4. **保存设置**

**测试端口转发：**

使用在线工具测试：
- 访问 https://canyouseeme.org
- 输入端口 `22`
- 点击 "Check Port"
- 如果显示 "Success"，说明配置正确

**注意：** 如果 Windows 主机 IP 变化，需要更新端口转发规则中的内部 IP。

---

### 6. 测试连接流程

**步骤 1：测试本地 SSH（在 WSL 中）**
```bash
ssh harry@localhost
# 如果成功，输入 exit 退出
```

**步骤 2：测试从 Windows 访问 WSL（在 Windows PowerShell 中）**
```powershell
Test-NetConnection -ComputerName 192.168.86.100 -Port 22
```

**步骤 3：测试从公网访问（使用在线工具）**
- 访问 https://canyouseeme.org
- 测试端口 22

**步骤 4：测试从 AWS EC2 连接（详细模式）**
```bash
# 在 AWS EC2 上运行
ssh -v harry@136.56.72.172
# -v 参数显示详细连接信息
```

**步骤 5：如果连接成功，建立 SSH 隧道**
```bash
ssh -D 8080 -N -f harry@136.56.72.172
```

---

## 🚨 常见错误和解决方案

### 错误 1: Connection timed out

**原因：** 路由器端口转发未配置或 Windows 防火墙阻止

**解决：**
1. ✅ 配置路由器端口转发（步骤 5）
2. ✅ 配置 Windows 防火墙（步骤 4）

---

### 错误 2: Connection refused

**原因：** SSH 服务未运行或端口未监听

**解决：**
1. ✅ 启动 SSH 服务（步骤 1）
2. ✅ 检查端口监听（步骤 1）

---

### 错误 3: Permission denied

**原因：** 认证失败

**解决：**
1. 确认用户名正确（应该是 `harry`）
2. 配置 SSH 密钥认证（推荐）：
   ```bash
   # 在 AWS EC2 上
   ssh-keygen -t rsa -b 4096
   ssh-copy-id harry@136.56.72.172
   ```

---

## 🔄 替代方案

如果 SSH Tunnel 配置困难，可以考虑：

### 方案 A：Python 简单代理
- ✅ 更简单，不需要 SSH
- ⚠️ 需要路由器端口转发（端口 8080）
- 详见 `proxy_setup.md` 方案 A

### 方案 C：Cloudflare Tunnel
- ✅ 完全不需要端口转发
- ✅ 不需要公网 IP
- ✅ 自动处理 NAT 穿透
- 详见 `proxy_setup.md` 方案 C

---

## 📋 完整检查命令

**在 WSL 中：**
```bash
# 1. 检查 SSH 服务
sudo systemctl status ssh

# 2. 检查端口监听
sudo netstat -tlnp | grep :22

# 3. 检查 SSH 配置
sudo grep -E "^(Port|AllowTcpForwarding|GatewayPorts)" /etc/ssh/sshd_config

# 4. 检查防火墙
sudo ufw status

# 5. 运行诊断脚本
bash troubleshoot_ssh.sh
```

**在 Windows PowerShell（管理员）中：**
```powershell
# 1. 测试端口
Test-NetConnection -ComputerName 192.168.86.100 -Port 22

# 2. 检查防火墙规则
Get-NetFirewallRule -DisplayName "SSH"

# 3. 运行配置脚本
.\configure_windows_firewall.ps1
```

**在 AWS EC2 上：**
```bash
# 1. 测试连接（详细模式）
ssh -v harry@136.56.72.172

# 2. 如果成功，建立隧道
ssh -D 8080 -N -f harry@136.56.72.172

# 3. 验证隧道
netstat -tlnp | grep 8080

# 4. 测试代理
curl --socks5 127.0.0.1:8080 https://api.ipify.org
# 应该返回你的公网 IP: 136.56.72.172
```

---

## 💡 提示

1. **路由器端口转发是最关键的步骤**，90% 的连接超时问题都是因为这个
2. **Windows 防火墙**也可能阻止连接，确保已配置
3. **使用详细模式测试**：`ssh -v` 可以显示详细的连接信息，有助于诊断
4. **逐步测试**：先测试本地，再测试局域网，最后测试公网
5. **如果所有步骤都正确但仍无法连接**，可能是 ISP 阻止了入站连接，考虑使用 Cloudflare Tunnel（方案 C）

---

## 📞 需要帮助？

如果按照以上步骤仍无法解决，请提供：
1. `troubleshoot_ssh.sh` 的输出
2. `ssh -v harry@136.56.72.172` 的输出
3. 路由器端口转发配置截图
4. Windows 防火墙规则截图
