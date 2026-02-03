## 1. EC2 实例准备

### 1.1 创建 EC2 实例
1. **登录 AWS 控制台**，进入 EC2 服务
2. **启动实例**，推荐配置：
   - **操作系统**：Ubuntu 22.04 LTS 或 Amazon Linux 2023
   - **实例类型**：`t3.small` 或更高（至少 2GB RAM）
   - **存储**：至少 20GB
   - **安全组**：确保允许 SSH（端口 22）访问

### 1.3 更新系统包

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y


### 2.1 安装 Google Chrome

Chrome 浏览器是运行 Selenium 的必需依赖。

#### Ubuntu/Debian:

```bash
# 下载并安装 Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb -y

# 验证安装
google-chrome --version

sudo apt install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    git \
    wget \
    curl \
    unzip \
    xvfb \
    libnss3 \
    libatk-bridge2.0-0t64 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2t64
