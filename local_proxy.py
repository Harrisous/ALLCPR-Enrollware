#!/usr/bin/env python3
"""
简单的 HTTP/HTTPS 代理服务器

用于在本地搭建代理服务器，让 AWS EC2 上的脚本通过此代理访问网站，
从而绕过 AWS IP 被 Cloudflare 检测的问题。

使用方法：
    python local_proxy.py [--host HOST] [--port PORT] [--allowed-ips IP1,IP2]

示例：
    # 默认监听 0.0.0.0:8080，允许所有 IP 访问
    python local_proxy.py

    # 只允许特定 IP 访问（推荐用于安全）
    python local_proxy.py --host 0.0.0.0 --port 8080 --allowed-ips 54.123.45.67

    # 只监听本地（用于测试）
    python local_proxy.py --host 127.0.0.1 --port 8080
"""
import argparse
import logging
import socket
import socketserver
import sys
from typing import Optional, Set
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class ProxyRequestHandler(socketserver.BaseRequestHandler):
    """处理代理请求的处理器"""

    allowed_ips: Optional[Set[str]] = None

    def handle(self):
        """处理客户端请求"""
        client_ip = self.client_address[0]
        logger.info(f"收到来自 {client_ip} 的连接请求")

        # 检查 IP 白名单
        if self.allowed_ips and client_ip not in self.allowed_ips:
            logger.warning(f"拒绝来自 {client_ip} 的连接（不在白名单中）")
            self.request.close()
            return

        try:
            # 读取请求的第一行（CONNECT 或 GET/POST 等）
            request_line = self.request.recv(4096).decode("utf-8", errors="ignore")
            if not request_line:
                return

            lines = request_line.split("\r\n")
            first_line = lines[0]
            logger.debug(f"请求行: {first_line}")

            # 解析请求
            parts = first_line.split()
            if len(parts) < 2:
                logger.error("无效的请求格式")
                return

            method = parts[0]
            target = parts[1]

            # 处理 CONNECT 方法（HTTPS）
            if method == "CONNECT":
                self.handle_connect(target, client_ip)
            # 处理 HTTP 方法（GET, POST 等）
            elif method in ("GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"):
                self.handle_http(method, target, request_line, client_ip)
            else:
                logger.warning(f"不支持的 HTTP 方法: {method}")
                self.send_error_response(405, "Method Not Allowed")

        except Exception as e:
            logger.exception(f"处理请求时出错: {e}")
        finally:
            try:
                self.request.close()
            except Exception:
                pass

    def handle_connect(self, target: str, client_ip: str):
        """处理 HTTPS CONNECT 请求"""
        # CONNECT 格式: CONNECT host:port HTTP/1.1
        if ":" not in target:
            logger.error(f"无效的 CONNECT 目标: {target}")
            self.send_error_response(400, "Bad Request")
            return

        host, port = target.split(":", 1)
        port = int(port)
        logger.info(f"[{client_ip}] CONNECT {host}:{port}")

        try:
            # 连接到目标服务器
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.settimeout(10)
            remote_socket.connect((host, port))

            # 发送 200 Connection Established 响应
            self.request.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")

            # 转发数据
            self.forward_data(self.request, remote_socket)

        except socket.timeout:
            logger.error(f"连接超时: {host}:{port}")
            self.send_error_response(504, "Gateway Timeout")
        except Exception as e:
            logger.error(f"连接失败 {host}:{port}: {e}")
            self.send_error_response(502, "Bad Gateway")
        finally:
            try:
                remote_socket.close()
            except Exception:
                pass

    def handle_http(self, method: str, target: str, request_line: str, client_ip: str):
        """处理 HTTP 请求（GET, POST 等）"""
        # 解析目标 URL
        if target.startswith("http://") or target.startswith("https://"):
            parsed = urlparse(target)
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            path = parsed.path or "/"
        else:
            # 相对路径，从 Host 头获取主机
            host = None
            port = 80
            path = target

            # 从请求头中提取 Host
            lines = request_line.split("\r\n")
            for line in lines[1:]:
                if line.lower().startswith("host:"):
                    host = line.split(":", 1)[1].strip()
                    if ":" in host:
                        host, port_str = host.rsplit(":", 1)
                        port = int(port_str)
                    break

        if not host:
            logger.error("无法确定目标主机")
            self.send_error_response(400, "Bad Request")
            return

        logger.info(f"[{client_ip}] {method} {host}:{port}{path}")

        try:
            # 连接到目标服务器
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.settimeout(30)
            remote_socket.connect((host, port))

            # 修改请求行，使用相对路径
            modified_request = request_line.replace(target, path, 1)

            # 发送请求到目标服务器
            remote_socket.sendall(modified_request.encode("utf-8"))

            # 转发响应
            self.forward_data(remote_socket, self.request)

        except socket.timeout:
            logger.error(f"请求超时: {host}:{port}")
            self.send_error_response(504, "Gateway Timeout")
        except Exception as e:
            logger.error(f"请求失败 {host}:{port}: {e}")
            self.send_error_response(502, "Bad Gateway")
        finally:
            try:
                remote_socket.close()
            except Exception:
                pass

    def forward_data(self, source: socket.socket, destination: socket.socket):
        """在两个 socket 之间转发数据"""
        try:
            while True:
                data = source.recv(4096)
                if not data:
                    break
                destination.sendall(data)
        except Exception as e:
            logger.debug(f"转发数据时出错（可能是正常关闭）: {e}")

    def send_error_response(self, code: int, message: str):
        """发送错误响应"""
        response = f"HTTP/1.1 {code} {message}\r\n\r\n"
        try:
            self.request.sendall(response.encode("utf-8"))
        except Exception:
            pass


class ThreadingProxyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """支持多线程的代理服务器"""
    allow_reuse_address = True
    daemon_threads = True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="简单的 HTTP/HTTPS 代理服务器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 默认配置（监听所有接口，端口 8080）
  python local_proxy.py

  # 只允许特定 IP 访问（推荐）
  python local_proxy.py --allowed-ips 54.123.45.67,54.123.45.68

  # 自定义端口
  python local_proxy.py --port 8888

  # 只监听本地（用于测试）
  python local_proxy.py --host 127.0.0.1
        """,
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="监听的主机地址（默认: 0.0.0.0，监听所有接口）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="监听的端口（默认: 8080）",
    )
    parser.add_argument(
        "--allowed-ips",
        help="允许访问的 IP 地址列表（逗号分隔），如果不指定则允许所有 IP",
    )

    args = parser.parse_args()

    # 解析允许的 IP 列表
    allowed_ips = None
    if args.allowed_ips:
        allowed_ips = set(ip.strip() for ip in args.allowed_ips.split(","))
        logger.info(f"IP 白名单: {allowed_ips}")
    else:
        logger.warning("⚠️  未设置 IP 白名单，所有 IP 都可以访问代理服务器！")
        logger.warning("⚠️  建议使用 --allowed-ips 参数限制访问")

    # 设置允许的 IP
    ProxyRequestHandler.allowed_ips = allowed_ips

    # 创建并启动服务器
    try:
        server = ThreadingProxyServer((args.host, args.port), ProxyRequestHandler)
        logger.info("=" * 60)
        logger.info(f"代理服务器已启动")
        logger.info(f"监听地址: {args.host}:{args.port}")
        if allowed_ips:
            logger.info(f"允许的 IP: {', '.join(allowed_ips)}")
        else:
            logger.info("允许的 IP: 所有 IP")
        logger.info("=" * 60)
        logger.info("按 Ctrl+C 停止服务器")
        logger.info("")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\n正在关闭服务器...")
        server.shutdown()
        logger.info("服务器已关闭")
    except OSError as e:
        if e.errno == 98:  # Address already in use
            logger.error(f"端口 {args.port} 已被占用，请使用其他端口或关闭占用该端口的程序")
        else:
            logger.exception(f"启动服务器失败: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"服务器错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
