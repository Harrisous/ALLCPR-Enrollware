# SSH 连接超时快速修复指南

## ✅ 当前状态检查

根据诊断，你的 WSL 端配置正常：
- ✅ SSH 服务正在运行
- ✅ SSH 正在监听端口 22
- ✅ WSL 用户: `harry`
- ✅ WSL 内部 IP: `172.26.4.164`

**问题很可能在以下两个方面：**

---

## 🔧 解决方案（按优先级）

### 1. 配置路由器端口转发（最重要！）

这是**90%的连接超时问题的原因**。

**步骤：**

1. **登录路由器**
   - 打开浏览器访问：`http://192.168.86.1`
   - 或查看路由器背面标签获取管理地址

2. **找到端口转发设置**
   - TP-Link: 高级功能 → 虚拟服务器 → 添加新条目
   - 华硕: 高级设置 → 虚拟服务器 → 添加
   - 小米: 高级设置 → 端口转发 → 添加规则
   - 华为: 高级功能 → NAT → 虚拟服务器 → 添加

3. **添加 SSH 端口转发规则**
   ```
   服务名称: SSH
   外部端口: 22
   内部 IP: 192.168.86.100  ← 你的 Windows 主机 IP
   内部端口: 22
   协议: TCP
   启用: 是
   ```

4. **保存设置**

5. **测试端口转发**
   - 访问：https://canyouseeme.org
   - 输入端口：`22`
   - 点击 "Check Port"
   - ✅ 如果显示 "Success"，说明配置正确
   - ❌ 如果显示 "Error"，继续下一步

---

### 2. 配置 Windows 防火墙

Windows 防火墙可能阻止了端口 22 的入站连接。

**方法 1：使用 PowerShell 脚本（推荐）**

在 Windows PowerShell（**以管理员身份运行**）中：

```powershell
cd C:\Users\harry\github_ALLCPR\ALLCPR-Enrollware
.\configure_windows_firewall.ps1
```

**方法 2：手动配置**

1. 打开 Windows 设置 → 隐私和安全性 → Windows 安全中心
2. 点击 "防火墙和网络保护" → "高级设置"
3. 点击 "入站规则" → "新建规则"
4. 选择 "端口" → TCP → 特定本地端口：`22`
5. 选择 "允许连接"
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

### 3. 验证 SSH 配置

确保 SSH 允许端口转发：

```bash
# 在 WSL 中运行
sudo nano /etc/ssh/sshd_config
```

确保包含：
```
AllowTcpForwarding yes
GatewayPorts yes
```

如果修改了配置，重启 SSH：
```bash
sudo systemctl restart ssh
```

或使用自动配置脚本：
```bash
sudo bash configure_ssh_forwarding.sh
```

---

## 🧪 测试连接

完成以上配置后，按顺序测试：

### 步骤 1：测试本地 SSH（在 WSL 中）
```bash
ssh harry@localhost
# 如果成功，输入 exit 退出
```

### 步骤 2：测试从 Windows 访问（在 Windows PowerShell 中）
```powershell
Test-NetConnection -ComputerName 192.168.86.100 -Port 22
```

### 步骤 3：测试从公网访问
- 访问：https://canyouseeme.org
- 输入端口：`22`
- 点击 "Check Port"
- ✅ 应该显示 "Success"

### 步骤 4：测试从 AWS EC2 连接（详细模式）
```bash
# 在 AWS EC2 上运行
ssh -v harry@136.56.72.172
```

**如果看到类似以下输出，说明连接成功：**
```
OpenSSH_8.2p1, OpenSSL 1.1.1f ...
debug1: Connecting to 136.56.72.172 [136.56.72.172] port 22.
debug1: Connection established.
```

### 步骤 5：建立 SSH 隧道
```bash
# 在 AWS EC2 上运行
ssh -D 8080 -N -f harry@136.56.72.172
```

### 步骤 6：验证隧道
```bash
# 在 AWS EC2 上运行
netstat -tlnp | grep 8080
# 应该看到：127.0.0.1:8080

# 测试代理
curl --socks5 127.0.0.1:8080 https://api.ipify.org
# 应该返回：136.56.72.172
```

---

## 📋 完整检查清单

- [ ] SSH 服务正在运行（✅ 已确认）
- [ ] SSH 监听端口 22（✅ 已确认）
- [ ] SSH 配置允许端口转发（需要检查）
- [ ] Windows 防火墙允许端口 22（需要配置）
- [ ] 路由器端口转发已配置（需要配置）
- [ ] 可以从公网访问端口 22（需要测试）

---

## 🚨 如果仍然无法连接

### 检查 Windows 主机 IP 是否正确

你的 Windows 主机 IP 应该是 `192.168.86.100`。如果 IP 变化了，需要更新：
1. 路由器端口转发规则中的内部 IP
2. 确保 Windows 防火墙规则仍然有效

**查看当前 Windows IP：**
```powershell
# 在 Windows PowerShell 中
ipconfig | findstr IPv4
```

### 使用替代方案

如果 SSH Tunnel 配置困难，可以考虑：

**方案 A：Python 简单代理**
- 更简单，不需要 SSH
- 需要路由器端口转发（端口 8080）
- 详见 `proxy_setup.md` 方案 A

**方案 C：Cloudflare Tunnel**
- 完全不需要端口转发
- 不需要公网 IP
- 自动处理 NAT 穿透
- 详见 `proxy_setup.md` 方案 C

---

## 📚 详细文档

- **完整故障排查指南**: `SSH_TROUBLESHOOTING.md`
- **代理设置指南**: `proxy_setup.md`
- **SSH Tunnel 设置**: `SSH_TUNNEL_GUIDE.md`

---

## 💡 提示

1. **路由器端口转发是最关键的**，90% 的问题都是因为这个
2. **Windows 防火墙**也可能阻止连接
3. **使用详细模式测试**：`ssh -v` 可以显示详细的连接信息
4. **逐步测试**：先本地，再局域网，最后公网
