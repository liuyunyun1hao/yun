#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SillyTavern 智能管理脚本 v5 - 融合版
特性：部署/更新、启动/停止、版本切换、局域网修复、后台保活
用法: python sillytavern_control.py
"""

import os
import sys
import time
import json
import signal
import socket
import subprocess
from pathlib import Path

# ========== 配置 ==========
REPO_URL = "https://github.com/SillyTavern/SillyTavern.git"
INSTALL_DIR = Path.home() / "sillytavern"
START_SCRIPT = INSTALL_DIR / "start.sh"
SYMLINK_PATH = Path("/data/data/com.termux/files/usr/bin/sillytavern")
PID_FILE = "st_pid.txt"        # 本地 PID 记录
SESSION_NAME = "tavern"         # tmux 会话名
PORT = 8000

# ========== 工具函数 ==========
def run(cmd, check=True, capture_output=False, shell=False):
    """执行命令并打印"""
    print(f"  > {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    if shell:
        return subprocess.run(cmd, shell=True, check=check,
                              executable="/bin/bash",
                              capture_output=capture_output, text=True)
    else:
        return subprocess.run(cmd, check=check,
                              capture_output=capture_output, text=True)

def check_port(port):
    """检查端口是否被占用"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('0.0.0.0', port))
        sock.close()
        return False
    except OSError:
        return True

def get_local_ip():
    """
    获取本机局域网 IP（借鉴 YunYun 代理脚本，智能识别物理网卡）
    """
    # 方法1：通过 UDP 路由自动获取
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('223.5.5.5', 80))  # 不发送真实数据，仅触发路由选择
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith('127.'):
            return ip
    except:
        pass

    # 方法2：解析 ifconfig，过滤虚拟网卡
    try:
        res = subprocess.run(['ifconfig'], capture_output=True, text=True, timeout=2)
        for line in res.stdout.split('\n'):
            line = line.strip()
            if line.startswith('inet ') and '127.0.0.1' not in line:
                parts = line.split()
                if len(parts) >= 2:
                    ip = parts[1]
                    # 排除 Docker 网桥、蓝牙共享等
                    if not (ip.startswith('172.17.') or ip.startswith('172.18.') or
                            ip.startswith('169.254.') or ip.startswith('192.0.0.')):
                        return ip
    except:
        pass

    # 方法3：通过主机名解析（可能返回 127.0.0.1）
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith('127.') and not ip.startswith('169.254.'):
                return ip
    except:
        pass

    return "127.0.0.1"

def is_running():
    """检查酒馆是否正在运行（通过 PID 文件或端口）"""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
                os.kill(pid, 0)   # 检测进程是否存在
                return True
        except:
            os.remove(PID_FILE)
    # 如果 PID 文件无效，检查端口
    return check_port(PORT)

def kill_by_pid_file():
    """根据 PID 文件安全终止进程"""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.5)
                try:
                    os.kill(pid, 0)
                    os.kill(pid, signal.SIGKILL)  # 强制结束
                except OSError:
                    pass
        except Exception as e:
            print(f"  ⚠️ 进程终止异常: {e}")
        finally:
            try:
                os.remove(PID_FILE)
            except:
                pass

def tmux_kill_session():
    """终止 tmux 会话（如果存在）"""
    subprocess.run(["tmux", "kill-session", "-t", SESSION_NAME],
                   capture_output=True, check=False)

# ========== 环境准备 ==========
def fix_ssl_and_pip():
    """修复 Git SSL 和 pip 镜像问题"""
    print("\n🔧 修复网络环境...")
    # 清除可能导致 Git 错误的 SSL 后端配置
    subprocess.run(["git", "config", "--global", "--unset", "http.sslBackend"], capture_output=True)
    run(["pkg", "install", "-y", "ca-certificates"], check=False)
    os.system("update-ca-certificates 2>/dev/null")
    # 设置 pip 官方源并信任，避免镜像 SSL 错误
    run(["pip", "config", "set", "global.index-url", "https://pypi.org/simple"], check=False)
    run(["pip", "config", "set", "global.trusted-host", "pypi.org"], check=False)
    run(["pip", "config", "set", "global.trusted-host", "files.pythonhosted.org"], check=False)

def install_system_deps():
    """安装系统依赖：git, nodejs-lts, tmux 等"""
    print("\n📦 安装/更新系统依赖...")
    run(["pkg", "update", "-y"])
    deps = ["git", "nodejs-lts", "python", "build-essential", "binutils", "clang",
            "ca-certificates", "tmux"]
    run(["pkg", "install", "-y"] + deps)
    fix_ssl_and_pip()

# ========== 酒馆部署/更新 ==========
def stash_local_changes():
    """自动 stash 所有本地改动，保证版本切换干净"""
    os.chdir(INSTALL_DIR)
    res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if res.stdout.strip():
        print("  ⚠️ 检测到本地改动，自动 stash ...")
        run(["git", "stash", "push", "--include-untracked", "-m", "auto-stash"])

def deploy_or_update():
    """
    首次部署或强制修复：
    1. 如果目录不存在 -> 克隆仓库
    2. 否则 -> fetch 最新，并切换至稳定版 release，自动 stash 本地修改
    """
    if not INSTALL_DIR.exists():
        print("\n📥 首次部署 SillyTavern ...")
        run(["git", "clone", REPO_URL, str(INSTALL_DIR)])
    else:
        print(f"\n🔄 目录已存在，更新代码...")
        os.chdir(INSTALL_DIR)
        run(["git", "fetch", "--all", "--tags", "--prune"])
        stash_local_changes()
        # 默认切换至 release 分支
        print("  📌 切换至稳定版 release ...")
        run(["git", "checkout", "release"])
        run(["git", "pull", "origin", "release"])
        # 安装 npm 依赖
        print("\n📦 安装 npm 依赖...")
        run(["npm", "install", "--no-audit", "--no-fund"])
        # 生成启动脚本
        create_launcher_script()
        # 修复局域网配置
        configure_lan_access()
        print("✅ 更新完成！")

def create_launcher_script():
    """创建全局 sillytavern 启动脚本（使用绝对路径）"""
    script = f"""#!/bin/bash
cd {INSTALL_DIR}
echo "Installing Node Modules..."
npm install --no-audit --no-fund --quiet --omit=dev 2>/dev/null
echo "Entering SillyTavern..."
node server.js
"""
    with open(START_SCRIPT, 'w') as f:
        f.write(script)
    os.chmod(START_SCRIPT, 0o755)
    # 更新软链接
    if SYMLINK_PATH.exists() or os.path.islink(SYMLINK_PATH):
        SYMLINK_PATH.unlink()
    SYMLINK_PATH.symlink_to(START_SCRIPT)

def configure_lan_access():
    """一键开启局域网访问：设置 listen: true，关闭白名单"""
    config_path = INSTALL_DIR / "config.yaml"
    if not config_path.exists():
        print("⚠️ config.yaml 未找到，跳过网络配置。")
        return
    with open(config_path, 'r') as f:
        content = f.read()
    import re
    # 将 listen: false 改为 listen: true
    content = re.sub(r"^(\s*listen:\s*).*", r"\1true", content, flags=re.MULTILINE)
    # 将 whitelistMode: true 改为 whitelistMode: false
    content = re.sub(r"^(\s*whitelistMode:\s*).*", r"\1false", content, flags=re.MULTILINE)
    with open(config_path, 'w') as f:
        f.write(content)
    print("✅ 已配置监听 0.0.0.0:8000 并关闭白名单")

# ========== 版本切换 ==========
def switch_version():
    """交互式切换酒馆版本（支持标签、分支）"""
    if not INSTALL_DIR.exists():
        print("❌ 酒馆尚未安装，请先执行部署。")
        return
    os.chdir(INSTALL_DIR)
    # 获取最新标签
    try:
        tags = subprocess.check_output(
            ["git", "tag", "--sort=-creatordate"], text=True).strip().split("\n")[:10]
        print("\n最近标签:", ", ".join(tags))
    except:
        tags = []
    print("1. 稳定版 (release)")
    print("2. 开发版 (main)")
    print("3. 自定义标签/提交")
    choice = input("选择版本 [1-3] (默认: 1): ").strip() or "1"
    if choice == "1":
        target = "release"
    elif choice == "2":
        target = "main"
    else:
        target = input("请输入分支名或标签名: ").strip()
        if not target:
            target = "release"

    # 如果酒馆正在运行，先停止
    if is_running():
        print("  🛑 检测到酒馆正在运行，先停止...")
        stop_tavern()

    stash_local_changes()
    print(f"  ✅ 切换至: {target}")
    # 判断是否是标签
    res = subprocess.run(["git", "tag", "-l", target], capture_output=True, text=True)
    if res.stdout.strip() == target:
        run(["git", "checkout", f"tags/{target}"])
    else:
        run(["git", "checkout", target])
        # 如果是分支，尝试 pull
        branch_check = subprocess.run(
            ["git", "branch", "-r", "--list", f"origin/{target}"],
            capture_output=True, text=True)
        if branch_check.stdout.strip():
            run(["git", "pull", "origin", target], check=False)
    # 重新安装依赖
    print("\n📦 重新安装 npm 依赖...")
    run(["npm", "install", "--no-audit", "--no-fund"])
    print("✅ 版本切换完成，可使用菜单重新启动酒馆。")

# ========== 启动/停止 ==========
def start_tavern():
    """使用 tmux 后台启动酒馆"""
    if is_running():
        print("⚠️ 酒馆已在运行中，无需重复启动。")
        return
    if not INSTALL_DIR.exists():
        print("❌ 酒馆尚未部署，请先执行部署。")
        return

    # 确保启动脚本存在
    if not START_SCRIPT.exists():
        create_launcher_script()
    # 确保配置了局域网访问
    configure_lan_access()

    print("\n🚀 正在后台启动酒馆 (tmux)...")
    # 先杀掉可能残留的 tmux 会话
    tmux_kill_session()
    # 创建新 tmux 会话，后台运行 sillytavern
    run(["tmux", "new-session", "-d", "-s", SESSION_NAME, "sillytavern"])
    # 等待一下让服务启动
    time.sleep(3)
    if check_port(PORT):
        local_ip = get_local_ip()
        print("✅ 酒馆启动成功！")
        print(f"   🌐 本机访问: http://127.0.0.1:{PORT}")
        print(f"   📱 局域网访问: http://{local_ip}:{PORT}")
        # 保存 PID 方便管理（但其实 tmux 管理了，这里可选）
        # 我们通过 tmux 会话管理，不依赖 PID 文件
    else:
        print("⚠️ 启动可能失败，请检查终端输出。")

def stop_tavern():
    """停止酒馆（终止 tmux 会话 + 杀进程）"""
    if not is_running():
        print("⚠️ 酒馆未在运行。")
        return
    print("\n🛑 停止酒馆...")
    # 终止 tmux 会话
    tmux_kill_session()
    # 强制结束所有 node server.js 进程
    subprocess.run(["pkill", "-f", "node server.js"], check=False)
    # 清除 PID 文件
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    time.sleep(1)
    if not check_port(PORT):
        print("✅ 酒馆已停止。")
    else:
        print("⚠️ 端口仍被占用，可能需要手动处理。")

def show_status():
    """显示酒馆运行状态和访问地址"""
    running = is_running()
    print("\n🍺 SillyTavern 状态")
    print("─" * 30)
    print(f"  运行状态: {'🟢 运行中' if running else '🔴 已停止'}")
    if running:
        local_ip = get_local_ip()
        print(f"  局域网 IP: {local_ip}")
        print(f"  访问地址: http://{local_ip}:{PORT}")
    else:
        print("  酒馆未启动，无法提供地址。")
    print("─" * 30)
    input("\n按 Enter 返回...")

# ========== 主菜单 ==========
def clear_screen():
    os.system('clear')

def show_menu():
    clear_screen()
    status = "🟢 运行中" if is_running() else "🔴 已停止"
    print("╭────────────────────────────────╮")
    print("│   🍺 SillyTavern 控制台 v5   │")
    print("╰────────────────────────────────╯")
    print(f"   状态: {status}")
    print("─" * 34)
    print("  1. 🚀 部署/更新酒馆")
    print("  2. ▶️  启动酒馆 (后台)")
    print("  3. ⏹️  停止酒馆")
    print("  4. 📡 查看状态与地址")
    print("  5. 🔀 切换酒馆版本")
    print("  6. 🔧 一键修复局域网访问")
    print("  7. 🛠️  安装/修复系统环境")
    print("  0. 退出")
    print("─" * 34)

def main():
    # 确保在 Termux 环境中
    if not Path("/data/data/com.termux").exists():
        print("❌ 请在 Termux 中运行此脚本。")
        sys.exit(1)

    while True:
        show_menu()
        choice = input(" 请输入数字选项: ").strip()
        if choice == "1":
            install_system_deps()
            deploy_or_update()
        elif choice == "2":
            start_tavern()
        elif choice == "3":
            stop_tavern()
        elif choice == "4":
            show_status()
        elif choice == "5":
            switch_version()
        elif choice == "6":
            configure_lan_access()
            print("✅ 局域网访问已开启，如酒馆正在运行，重启后生效。")
        elif choice == "7":
            install_system_deps()
            print("✅ 环境修复完成。")
        elif choice == "0":
            print("👋 再见！")
            break
        else:
            print("❌ 无效选项，请重试。")
        if choice != "0":
            input("\n👉 按 Enter 返回主菜单...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 已退出")
        sys.exit(0)