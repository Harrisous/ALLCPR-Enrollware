#!/bin/bash
# 配置 SSH 允许端口转发

SSH_CONFIG="/etc/ssh/sshd_config"
BACKUP_FILE="${SSH_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"

echo "=========================================="
echo "配置 SSH 端口转发"
echo "=========================================="
echo ""

# 备份配置文件
if [ ! -f "$BACKUP_FILE" ]; then
    echo "备份 SSH 配置文件..."
    sudo cp "$SSH_CONFIG" "$BACKUP_FILE"
    echo "✅ 已备份到: $BACKUP_FILE"
fi

echo ""
echo "检查当前配置..."

# 检查 AllowTcpForwarding
if grep -q "^AllowTcpForwarding yes" "$SSH_CONFIG"; then
    echo "✅ AllowTcpForwarding 已设置为 yes"
else
    if grep -q "^AllowTcpForwarding" "$SSH_CONFIG"; then
        echo "⚠️  AllowTcpForwarding 存在但未设置为 yes，需要修改"
        sudo sed -i 's/^AllowTcpForwarding.*/AllowTcpForwarding yes/' "$SSH_CONFIG"
        echo "✅ 已更新 AllowTcpForwarding 为 yes"
    else
        echo "添加 AllowTcpForwarding yes..."
        echo "AllowTcpForwarding yes" | sudo tee -a "$SSH_CONFIG" > /dev/null
        echo "✅ 已添加 AllowTcpForwarding yes"
    fi
fi

# 检查 GatewayPorts
if grep -q "^GatewayPorts yes" "$SSH_CONFIG"; then
    echo "✅ GatewayPorts 已设置为 yes"
else
    if grep -q "^GatewayPorts" "$SSH_CONFIG"; then
        echo "⚠️  GatewayPorts 存在但未设置为 yes，需要修改"
        sudo sed -i 's/^GatewayPorts.*/GatewayPorts yes/' "$SSH_CONFIG"
        echo "✅ 已更新 GatewayPorts 为 yes"
    else
        echo "添加 GatewayPorts yes..."
        echo "GatewayPorts yes" | sudo tee -a "$SSH_CONFIG" > /dev/null
        echo "✅ 已添加 GatewayPorts yes"
    fi
fi

echo ""
echo "验证配置..."
if grep -q "^AllowTcpForwarding yes" "$SSH_CONFIG" && grep -q "^GatewayPorts yes" "$SSH_CONFIG"; then
    echo "✅ 配置验证成功"
    echo ""
    echo "重启 SSH 服务..."
    sudo systemctl restart ssh
    echo "✅ SSH 服务已重启"
    echo ""
    echo "检查 SSH 服务状态..."
    sudo systemctl status ssh --no-pager | head -5
    echo ""
    echo "=========================================="
    echo "配置完成！"
    echo "=========================================="
    echo ""
    echo "下一步："
    echo "1. 配置路由器端口转发（SSH 端口 22）"
    echo "2. 从 AWS EC2 建立 SSH 隧道"
else
    echo "❌ 配置验证失败，请手动检查配置文件"
    exit 1
fi
