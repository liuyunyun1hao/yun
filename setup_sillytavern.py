#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SillyTavern 智能管理脚本 v6 - 完美修正版
特点：智能等待启动、网络容错、自动修复软链接、健壮版本切换、无坑菜单
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
SESSION_NAME = "tavern"         # tmux 会话名
PORT = 8000

# ========== 核心工具函数 ==========
def run(cmd, check=True, capture_output=False, shell=False, timeout=None):
    """安全执行命令，打印并返回结果"""
    if isinstance(cmd, list):
        print(f"  > {' '.join(cmd)}")
    else:
        print(f"  > {cmd}")
    try:
        if shell:
            return subprocess.run(cmd, shell=True, check=check,
                                  executable="/bin/bash",
                                  capture_output=capture_output, text=True,
                                  timeout=timeout)
        else:
            return subprocess.run(cmd, check=check,
                                  capture_output=capture_output, text=True,
                                  timeout=timeout)
    except subprocess.CalledProcessError as e:
        if not check:
            return None
        print(f"  ❌ 命令执行失败: {e}")
        return None
    except subprocess.TimeoutExpired:
        print("  ⏱️ 命令超时")
        return None

def check_port(port):
    """检查指定端口是否已被占用（尝试绑定）"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        # 尝试绑定，如果成功则说明端口空闲
        sock.bind(('0.0.0.0', port))
        sock.close()
        return False
    except OSError:
        return True

def wait_for_port(port, timeout=30):
    """等待端口变为开放状态，返回 True 表示成功"""
    print(f"  ⏳ 等待端口 {port} 就绪 (最多 {timeout}s)...", end='', flush=True)
    for i in range(timeout * 2):   # 每0.5秒检查一次
        if check_port(port):
            print(" ✅")
            return True
        time.sleep(0.5)
        if i % 4 == 0:
            print(".", end='', flush=True)
    print(" ❌")
    return False

def get_local_ip():
    """智能获取本机局域网 IP（多级回退）"""
    # 方法1：UDP 路由
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('223.5.5.5', 80))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith('127.'):
            return ip
    except:
        pass
    # 方法2：ifconfig 过滤
    try:
        res = subprocess.run(['ifconfig'], capture_output=True, text=True, timeout=3)
        for line in res.stdout.split('\n'):
            if 'inet ' in line and '127.0.0.1' not in line:
                parts = line.split()
                ip = parts[1] if len(parts) > 1 else None
                if ip and not (ip.startswith('172.17.') or ip.startswith('172.18.') or
                               ip.startswith('169.254.') or ip.startswith('192.0.0.')):
                    return ip
    except:
        pass
    # 方法3：主机名
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
    """检查酒馆是否在运行（通过端口状态）"""
    return check_port(PORT)

def kill_by_tmux():
    """终止 tmux 会话及残留进程"""
    subprocess.run(["tmux", "kill-session", "-t", SESSION_NAME],
                   capture_output=True, check=False)
    # 强制杀死 node server.js 进程
    subprocess.run(["pkill", "-f", "node server.js"], capture_output=True, check=False)

def safe_stop():
    """安全停止酒馆"""
    if is_running():
        print("  🛑 正在停止酒馆...")
        kill_by_tmux()
        # 等待端口释放
        for _ in range(10):
            if not check_port(PORT):
                print("  ✅ 已停止")
                return
            time.sleep(0.5)
        print("  ⚠️ 端口仍被占用，尝试强制结束...")
        subprocess.run(["fuser", "-k", f"{PORT}/tcp"], capture_output=True, check=False)
    else:
        print("  ℹ️ 酒馆未运行")

def stash_changes():
    """暂存本地修改"""
    os.chdir(INSTALL_DIR)
    res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if res.stdout.strip():
        print("  ⚠️ 检测到本地改动，自动 stash 保存...")
        run(["git", "stash", "push", "--include-untracked", "-m", "auto-stash"])

def create_launcher():
    """重建全局启动脚本和软链接"""
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
    if SYMLINK_PATH.exists() or os.path.islink(SYMLINK_PATH):
        SYMLINK_PATH.unlink()
    SYMLINK_PATH.symlink_to(START_SCRIPT)
    print("  ✅ 全局命令 sillytavern 已更新")

def fix_lan_config():
    """一键开启局域网监听并关闭白名单"""
    cfg = INSTALL_DIR / "config.yaml"
    if not cfg.exists():
        print("  ⚠️ config.yaml 不存在，跳过网络配置")
        return
    import re
    with open(cfg, 'r') as f:
        content = f.read()
    content = re.sub(r"^(\s*listen:\s*).*", r"\1true", content, flags=re.MULTILINE)
    content = re.sub(r"^(\s*whitelistMode:\s*).*", r"\1false", content, flags=re.MULTILINE)
    with open(cfg, 'w') as f:
        f.write(content)
    print("  ✅ 已设置监听 0.0.0.0:8000 并关闭白名单")

# ========== 环境准备 ==========
def fix_network():
    """修复 Git SSL 和 pip 源问题"""
    print("\n🔧 修复网络环境...")
    subprocess.run(["git", "config", "--global", "--unset", "http.sslBackend"], capture_output=True)
    run(["pkg", "install", "-y", "ca-certificates"], check=False)
    os.system("update-ca-certificates 2>/dev/null")
    run(["pip", "config", "set", "global.index-url", "https://pypi.org/simple"], check=False)
    run(["pip", "config", "set", "global.trusted-host", "pypi.org"], check=False)
    run(["pip", "config", "set", "global.trusted-host", "files.pythonhosted.org"], check=False)

def install_deps():
    """安装/更新系统依赖"""
    print("\n📦 更新软件源并安装依赖...")
    run(["pkg", "update", "-y"])
    deps = ["git", "nodejs-lts", "python", "build-essential", "binutils", "clang",
            "ca-certificates", "tmux"]
    run(["pkg", "install", "-y"] + deps)
    fix_network()

# ========== 部署与更新 ==========
def deploy_or_update():
    """首次部署或更新至稳定版"""
    if not INSTALL_DIR.exists():
        print("\n📥 克隆 SillyTavern 仓库...")
        if run(["git", "clone", REPO_URL, str(INSTALL_DIR)]) is None:
            print("❌ 克隆失败，请检查网络")
            return
        os.chdir(INSTALL_DIR)
    else:
        print(f"\n🔄 更新现有酒馆...")
        os.chdir(INSTALL_DIR)
        run(["git", "fetch", "--all", "--tags", "--prune"])
        stash_changes()
        # 默认切换到 release 分支
        print("  📌 切换到稳定版 release ...")
        if run(["git", "checkout", "release"]) is None:
            print("❌ 切换分支失败")
            return
        # 尝试 pull，失败不中断（网络问题）
        run(["git", "pull", "origin", "release"], check=False)

    print("\n📦 安装 npm 依赖（可能需要几分钟）...")
    for i in range(3):
        if run(["npm", "install", "--no-audit", "--no-fund"]) is not None:
            break
        print(f"    安装失败，第 {i+1} 次重试...")
        subprocess.run(["npm", "cache", "clean", "--force"], capture_output=True)
        time.sleep(2)
    else:
        print("❌ npm 安装多次失败，请检查网络或手动执行 npm install")

    create_launcher()
    fix_lan_config()
    print("\n✅ 部署/更新完成！")

# ========== 版本切换 ==========
def switch_version():
    """交互式切换版本，自动 stash、安装依赖"""
    if not INSTALL_DIR.exists():
        print("❌ 酒馆尚未安装，请先部署")
        return
    os.chdir(INSTALL_DIR)
    try:
        tags = subprocess.check_output(
            ["git", "tag", "--sort=-creatordate"], text=True).strip().split("\n")[:10]
        print("\n📌 最近标签:", ", ".join(tags))
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
        target = input("请输入分支名或标签名: ").strip() or "release"

    safe_stop()   # 切换前先停止
    stash_changes()
    print(f"  ✅ 切换至: {target}")
    # 判断是否为 tag
    res = subprocess.run(["git", "tag", "-l", target], capture_output=True, text=True)
    if res.stdout.strip() == target:
        run(["git", "checkout", f"tags/{target}"])
    else:
        if run(["git", "checkout", target]) is None:
            print("❌ 切换失败")
            return
        # 如果是分支，拉取最新
        branch_check = subprocess.run(
            ["git", "branch", "-r", "--list", f"origin/{target}"],
            capture_output=True, text=True)
        if branch_check.stdout.strip():
            run(["git", "pull", "origin", target], check=False)

    print("\n📦 安装 npm 依赖...")
    if run(["npm", "install", "--no-audit", "--no-fund"]) is None:
        print("⚠️ npm 安装可能失败，请稍后重试")
    else:
        print("✅ 版本切换完成，可使用菜单启动酒馆")

# ========== 启动与停止 ==========
def start_tavern():
    """后台启动酒馆 (tmux)，并等待端口就绪"""
    if is_running():
        print("⚠️ 酒馆已在运行中")
        return
    if not INSTALL_DIR.exists():
        print("❌ 请先执行部署 (选项1)")
        return

    # 确保启动脚本存在
    if not START_SCRIPT.exists():
        create_launcher()
    fix_lan_config()   # 自动保证局域网可用

    # 清除残留
    kill_by_tmux()
    time.sleep(1)

    print("\n🚀 后台启动酒馆...")
    run(["tmux", "new-session", "-d", "-s", SESSION_NAME, "sillytavern"])
    if wait_for_port(PORT, timeout=30):
        ip = get_local_ip()
        print("\n✅ 酒馆启动成功！")
        print(f"   📱 局域网访问: http://{ip}:{PORT}")
        print(f"   💻 本机访问: http://127.0.0.1:{PORT}")
    else:
        print("❌ 启动超时，请检查以下可能原因：")
        print("   1. 依赖未完整安装 → 运行选项7 修复环境")
        print("   2. 端口被占用 → 运行选项3 停止后再启动")
        print("   3. 配置文件错误 → 删除 ~/sillytavern/config.yaml 后重新部署")
        print("\n   可以执行 'tmux attach -t tavern' 查看实时日志")

def stop_tavern():
    """停止酒馆"""
    safe_stop()

def restart_tavern():
    """重启酒馆"""
    stop_tavern()
    start_tavern()

def show_status():
    """显示运行状态与地址"""
    running = is_running()
    print("\n🍺 SillyTavern 状态")
    print("─" * 30)
    print(f"  运行状态: {'🟢 运行中' if running else '🔴 已停止'}")
    if running:
        ip = get_local_ip()
        print(f"  局域网 IP: {ip}")
        print(f"  访问地址: http://{ip}:{PORT}")
    else:
        print("  酒馆未启动")
    print("─" * 30)

# ========== 菜单系统 ==========
def clear_screen():
    os.system('clear')

def show_menu():
    clear_screen()
    status = "🟢 运行中" if is_running() else "🔴 已停止"
    print("╭────────────────────────────────╮")
    print("│   🍺 SillyTavern 控制台 v6   │")
    print("╰────────────────────────────────╯")
    print(f"   状态: {status}")
    print("─" * 34)
    print("  1. 🚀 部署/更新酒馆")
    print("  2. ▶️  启动酒馆 (后台)")
    print("  3. ⏹️  停止酒馆")
    print("  4. 🔁 重启酒馆")
    print("  5. 📡 查看状态与地址")
    print("  6. 🔀 切换酒馆版本")
    print("  7. 🔧 一键修复网络/环境")
    print("  8. 🌐 强制开启局域网访问")
    print("  0. 退出")
    print("─" * 34)

def main():
    if not Path("/data/data/com.termux").exists():
        print("❌ 请在 Termux 中运行此脚本")
        sys.exit(1)

    while True:
        show_menu()
        choice = input(" 请输入选项: ").strip()
        if choice == "1":
            deploy_or_update()
        elif choice == "2":
            start_tavern()
        elif choice == "3":
            stop_tavern()
        elif choice == "4":
            restart_tavern()
        elif choice == "5":
            show_status()
        elif choice == "6":
            switch_version()
        elif choice == "7":
            install_deps()
            print("✅ 环境修复完成，可重新部署或启动")
        elif choice == "8":
            fix_lan_config()
            print("✅ 已强制开启局域网监听并关闭白名单，重启后生效")
        elif choice == "0":
            print("👋 再见！")
            break
        else:
            print("❌ 无效选项")
        if choice != "0":
            input("\n👉 按 Enter 返回主菜单...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 已退出")
        sys.exit(0)