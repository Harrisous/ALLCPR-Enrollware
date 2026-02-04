#!/bin/bash
# 快速测试代理服务器连接

set -e

echo "=========================================="
echo "代理服务器连接测试"
echo "=========================================="
echo ""

# 检查参数
if [ -z "$1" ]; then
    echo "用法: $0 <代理地址>"
    echo "示例: $0 http://136.56.72.172:8080"
    exit 1
fi

PROXY_URL="$1"

echo "测试代理: $PROXY_URL"
echo ""

# 测试 1: 基本连接
echo "测试 1: 基本连接测试..."
if curl -x "$PROXY_URL" --connect-timeout 10 -s -o /dev/null -w "%{http_code}" https://www.google.com > /tmp/proxy_test_1.txt 2>&1; then
    HTTP_CODE=$(cat /tmp/proxy_test_1.txt)
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
        echo "✅ 基本连接成功 (HTTP $HTTP_CODE)"
    else
        echo "⚠️  连接成功但返回异常状态码: $HTTP_CODE"
    fi
else
    echo "❌ 基本连接失败"
    cat /tmp/proxy_test_1.txt
    exit 1
fi

echo ""

# 测试 2: 访问目标网站
echo "测试 2: 访问 Enrollware 网站..."
if curl -x "$PROXY_URL" --connect-timeout 10 -s -o /dev/null -w "%{http_code}" https://www.enrollware.com > /tmp/proxy_test_2.txt 2>&1; then
    HTTP_CODE=$(cat /tmp/proxy_test_2.txt)
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
        echo "✅ 可以访问 Enrollware (HTTP $HTTP_CODE)"
    else
        echo "⚠️  可以连接但返回状态码: $HTTP_CODE"
    fi
else
    echo "❌ 无法访问 Enrollware"
    cat /tmp/proxy_test_2.txt
    exit 1
fi

echo ""

# 测试 3: 检查 IP 地址
echo "测试 3: 检查通过代理访问的 IP 地址..."
PROXY_IP=$(curl -x "$PROXY_URL" --connect-timeout 10 -s https://api.ipify.org 2>/dev/null || echo "无法获取")
if [ -n "$PROXY_IP" ] && [ "$PROXY_IP" != "无法获取" ]; then
    echo "✅ 通过代理访问的 IP: $PROXY_IP"
    echo "   如果这是你的本地网络 IP，说明代理工作正常"
else
    echo "⚠️  无法获取 IP 地址"
fi

echo ""

# 测试 4: 直接访问 IP（对比）
echo "测试 4: 直接访问的 IP（对比）..."
DIRECT_IP=$(curl --connect-timeout 10 -s https://api.ipify.org 2>/dev/null || echo "无法获取")
if [ -n "$DIRECT_IP" ] && [ "$DIRECT_IP" != "无法获取" ]; then
    echo "✅ 直接访问的 IP: $DIRECT_IP"
    if [ "$PROXY_IP" != "$DIRECT_IP" ] && [ "$PROXY_IP" != "无法获取" ]; then
        echo "✅ IP 地址不同，说明代理正在工作"
    elif [ "$PROXY_IP" = "$DIRECT_IP" ]; then
        echo "⚠️  IP 地址相同，代理可能未生效"
    fi
else
    echo "⚠️  无法获取直接访问的 IP"
fi

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
echo ""
echo "如果所有测试都通过，可以在脚本中使用："
echo "  export PROXY_SERVER=$PROXY_URL"
echo "  python login_humanlike.py"
