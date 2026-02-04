#!/bin/bash
# SSH Tunnel 代理设置脚本（方案 B）

set -e

echo "=========================================="
echo "SSH Tunnel 代理设置（方案 B）"
echo "=========================================="
echo ""

# 检查是否在 WSL 中
if [ -z "$WSL_DISTRO_NAME" ] && [ -z "$WSLENV" ]; then
    echo "⚠️  这个脚本需要在 WSL 中运行"
    echo "请在 WSL 终端中运行此脚本"
    exit 1
fi

echo "步骤 1: 检查 SSH 服务器..."
if ! command -v ssh &> /dev/null; then
    echo "安装 OpenSSH Server..."
    sudo apt-get update
    sudo apt-get install openssh-server -y
else
    echo "✅ SSH 已安装"
fi

echo ""
echo "步骤 2: 启动 SSH 服务..."
if sudo systemctl is-active --quiet ssh; then
    echo "✅ SSH 服务已在运行"
else
    echo "启动 SSH 服务..."
    sudo systemctl start ssh
    sudo systemctl enable ssh
    echo "✅ SSH 服务已启动"
fi

echo ""
echo "步骤 3: 检查 SSH 配置..."
SSH_CONFIG="/etc/ssh/sshd_config"

# 备份配置
if [ ! -f "${SSH_CONFIG}.backup" ]; then
    sudo cp "$SSH_CONFIG" "${SSH_CONFIG}.backup"
    echo "✅ 已备份 SSH 配置"
fi

# 检查并更新配置
if ! grep -q "^AllowTcpForwarding yes" "$SSH_CONFIG"; then
    echo "配置允许端口转发..."
    echo "AllowTcpForwarding yes" | sudo tee -a "$SSH_CONFIG" > /dev/null
fi

if ! grep -q "^GatewayPorts yes" "$SSH_CONFIG"; then
    echo "配置 GatewayPorts..."
    echo "GatewayPorts yes" | sudo tee -a "$SSH_CONFIG" > /dev/null
fi

sudo systemctl restart ssh
echo "✅ SSH 配置已更新"

echo ""
echo "步骤 4: 检查防火墙..."
if command -v ufw &> /dev/null; then
    if sudo ufw status | grep -q "22/tcp"; then
        echo "✅ SSH 端口已在防火墙中开放"
    else
        echo "开放 SSH 端口..."
        sudo ufw allow 22/tcp
        echo "✅ SSH 端口已开放"
    fi
else
    echo "⚠️  未检测到 ufw，请手动确保防火墙允许 SSH（端口 22）"
fi

echo ""
echo "=========================================="
echo "设置完成！"
echo "=========================================="
echo ""
echo "你的 Windows 主机 IP: 192.168.86.100"
echo "你的公网 IP: 136.56.72.172"
echo ""
echo "下一步："
echo "1. 在 AWS EC2 上运行以下命令建立 SSH 隧道："
echo ""
echo "   ssh -D 8080 -N -f $(whoami)@136.56.72.172"
echo ""
echo "   或者如果使用密码认证："
echo "   ssh -D 8080 -N -f $(whoami)@136.56.72.172"
echo ""
echo "2. 如果提示输入密码，请输入你的 WSL 用户密码"
echo ""
echo "3. 在 AWS EC2 上设置代理环境变量："
echo "   export PROXY_SERVER=socks5://127.0.0.1:8080"
echo ""
echo "4. 运行脚本："
echo "   python login_humanlike.py"
echo ""
echo "注意："
echo "- 如果无法从 AWS EC2 SSH 到你的公网 IP，可能需要配置路由器端口转发 SSH（端口 22）"
echo "- 或者使用 Cloudflare Tunnel（方案 C，完全不需要端口转发）"
