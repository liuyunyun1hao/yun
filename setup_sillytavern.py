#!/usr/bin/env python3
"""
SillyTavern 全能管理脚本 v2
功能：部署、启动、停止、查看IP、切换版本、修复配置
用法: python sillytavern_manager.py
"""

import os, sys, subprocess
from pathlib import Path

INSTALL_DIR = Path.home() / "sillytavern"
START_SCRIPT = INSTALL_DIR / "start.sh"
SYMLINK_PATH = Path("/data/data/com.termux/files/usr/bin/sillytavern")
REPO_URL = "https://github.com/SillyTavern/SillyTavern.git"
SESSION_NAME = "tavern"

def run(cmd, check=True, capture_output=False, shell=False):
    """执行命令"""
    if shell:
        return subprocess.run(cmd, shell=True, check=check, executable="/bin/bash",
                              capture_output=capture_output, text=True)
    else:
        return subprocess.run(cmd, check=check, capture_output=capture_output, text=True)

def clear_screen():
    os.system("clear")

def print_banner():
    print("""
╔══════════════════════════════════╗
║   🍺 SillyTavern 管理面板 v2   ║
╚══════════════════════════════════╝
""")

def check_termux():
    if not Path("/data/data/com.termux").exists():
        sys.exit("❌ 只能在 Termux 中运行")

def fix_pip_ssl():
    """修复 pip SSL 问题"""
    run(["pip", "config", "set", "global.index-url", "https://pypi.org/simple"], check=False)
    run(["pip", "config", "set", "global.trusted-host", "pypi.org"], check=False)
    run(["pip", "config", "set", "global.trusted-host", "files.pythonhosted.org"], check=False)

def fix_git_ssl():
    """修复 git SSL 配置"""
    subprocess.run(["git", "config", "--global", "--unset", "http.sslBackend"], capture_output=True)
    run(["pkg", "install", "-y", "ca-certificates"], check=False)
    os.system("update-ca-certificates 2>/dev/null")

def install_deps():
    """安装系统依赖"""
    print("📦 安装/更新系统依赖...")
    run(["pkg", "update", "-y"])
    deps = ["git", "nodejs-lts", "python", "build-essential", "binutils", "clang", "ca-certificates", "tmux"]
    run(["pkg", "install", "-y"] + deps)
    fix_git_ssl()
    fix_pip_ssl()

def deploy_first_time():
    """首次部署或强制修复"""
    if not INSTALL_DIR.exists():
        print("🚀 首次部署 SillyTavern ...")
        run(["git", "clone", REPO_URL, str(INSTALL_DIR)])
    else:
        print("🔧 目录已存在，将执行修复/更新...")
        os.chdir(INSTALL_DIR)
        run(["git", "fetch", "--all", "--tags", "--prune"])
    os.chdir(INSTALL_DIR)
    # 自动切换到稳定版 release 分支
    stash_changes()
    print("📥 切换到 release 分支...")
    run(["git", "checkout", "release"])
    run(["git", "pull", "origin", "release"])
    print("📦 安装 npm 依赖...")
    run(["npm", "install", "--no-audit", "--no-fund"])
    # 安装 Python 依赖
    req = INSTALL_DIR / "requirements.txt"
    if req.exists():
        run(["pip", "install", "-r", str(req)], check=False)
    # 生成启动脚本
    create_launcher()
    # 默认开放局域网
    set_listen_all()
    print("✅ 部署完成！")

def stash_changes():
    os.chdir(INSTALL_DIR)
    res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if res.stdout.strip():
        print("⚠️ 自动 stash 本地改动...")
        run(["git", "stash", "push", "--include-untracked", "-m", "auto-stash"])

def create_launcher():
    script = f"""#!/bin/bash
cd {INSTALL_DIR}
echo "Installing Node Modules..."
npm install --no-audit --no-fund --quiet --omit=dev 2>/dev/null
echo "Entering SillyTavern..."
node server.js
"""
    with open(START_SCRIPT, "w") as f:
        f.write(script)
    os.chmod(START_SCRIPT, 0o755)
    # 更新软链接
    if SYMLINK_PATH.exists() or os.path.islink(SYMLINK_PATH):
        SYMLINK_PATH.unlink()
    SYMLINK_PATH.symlink_to(START_SCRIPT)

def set_listen_all():
    """配置监听 0.0.0.0 并关闭白名单"""
    cfg = INSTALL_DIR / "config.yaml"
    if not cfg.exists():
        return
    with open(cfg, "r") as f:
        content = f.read()
    import re
    # 设置 listen: true
    content = re.sub(r"^(\s*listen:\s*).*", r"\1true", content, flags=re.MULTILINE)
    # 关闭白名单
    content = re.sub(r"^(\s*whitelistMode:\s*).*", r"\1false", content, flags=re.MULTILINE)
    with open(cfg, "w") as f:
        f.write(content)

def get_ip():
    """获取本机局域网 IP"""
    try:
        res = subprocess.check_output(["ip", "addr", "show", "wlan0"], text=True)
        for line in res.split("\n"):
            if "inet " in line:
                return line.strip().split()[1].split("/")[0]
    except:
        pass
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "未知"

def is_running():
    """检查酒馆是否正在运行"""
    res = subprocess.run(["pgrep", "-f", "node server.js"], capture_output=True, text=True)
    return bool(res.stdout.strip())

def start_tavern(background=True):
    """启动酒馆"""
    if is_running():
        print("⚠️ 酒馆已在运行中，无需重复启动。")
        return
    if background:
        print("🚀 后台启动酒馆 (tmux)...")
        run(["tmux", "new-session", "-d", "-s", SESSION_NAME, "sillytavern"])
        print("✅ 酒馆已在后台启动，可通过 http://{}:8000 访问".format(get_ip()))
    else:
        print("🚀 前台启动酒馆...")
        os.system("sillytavern")

def stop_tavern():
    """停止酒馆"""
    print("🛑 停止所有酒馆进程...")
    run(["pkill", "-f", "node server.js"], check=False)
    run(["tmux", "kill-session", "-t", SESSION_NAME], check=False)
    print("✅ 已停止")

def restart_tavern():
    """重启酒馆"""
    stop_tavern()
    start_tavern()

def show_ip():
    """显示访问地址"""
    ip = get_ip()
    print(f"🌐 局域网访问地址: http://{ip}:8000")
    print("   (确保手机/平板在同一 WiFi)")

def switch_version():
    """交互式切换版本"""
    os.chdir(INSTALL_DIR)
    print("\n=== 切换版本 ===")
    print("1. 稳定版 (release)")
    print("2. 开发版 (main)")
    print("3. 自定义标签/提交")
    choice = input("选择 [1-3]: ").strip()
    if choice == "1":
        target = "release"
    elif choice == "2":
        target = "main"
    else:
        try:
            tags = subprocess.check_output(["git", "tag", "--sort=-creatordate"], text=True).strip().split("\n")[:10]
            print("最近标签:", ", ".join(tags))
        except:
            pass
        target = input("请输入分支/标签/提交: ").strip() or "release"

    # 先停止酒馆
    stop_tavern()
    stash_changes()
    print(f"✅ 切换至: {target}")
    if target in subprocess.check_output(["git", "tag", "-l", target], text=True):
        run(["git", "checkout", f"tags/{target}"])
    else:
        run(["git", "checkout", target])
        run(["git", "pull", "origin", target], check=False)
    print("📦 重新安装依赖...")
    run(["npm", "install", "--no-audit", "--no-fund"])
    print("✅ 版本切换完成，请手动启动酒馆。")

def fix_config():
    """修复配置（开放局域网、关白名单）"""
    set_listen_all()
    print("✅ 已配置监听 0.0.0.0 并关闭白名单，重启后生效。")

def menu():
    """主菜单"""
    while True:
        clear_screen()
        print_banner()
        status = "🟢 运行中" if is_running() else "🔴 未运行"
        print(f"酒馆状态: {status}")
        print("")
        print("1. 🚀 启动酒馆 (后台 tmux)")
        print("2. 🛑 停止酒馆")
        print("3. 🔄 重启酒馆")
        print("4. 🌐 显示局域网访问地址")
        print("5. 🔀 切换酒馆版本")
        print("6. 🔧 修复/开放局域网访问")
        print("7. ♻️  重新部署/修复依赖")
        print("0. 退出")
        choice = input("\n请选择操作: ").strip()
        if choice == "1":
            start_tavern()
            input("按 Enter 键返回...")
        elif choice == "2":
            stop_tavern()
            input("按 Enter 键返回...")
        elif choice == "3":
            restart_tavern()
            input("按 Enter 键返回...")
        elif choice == "4":
            show_ip()
            input("按 Enter 键返回...")
        elif choice == "5":
            switch_version()
            input("按 Enter 键返回...")
        elif choice == "6":
            fix_config()
            restart_tavern()
            input("按 Enter 键返回...")
        elif choice == "7":
            print("⚠️ 这将重新克隆/更新仓库并安装依赖，但不会丢失你的聊天数据。")
            confirm = input("确定？(y/n): ").strip().lower()
            if confirm == "y":
                install_deps()
                deploy_first_time()
                input("按 Enter 键返回...")
        elif choice == "0":
            print("👋 再见！")
            break
        else:
            print("❌ 无效选项")
            input("按 Enter 键继续...")

def main():
    check_termux()
    # 如果酒馆目录不存在，强制先部署
    if not INSTALL_DIR.exists():
        print("🧰 检测到酒馆未安装，正在首次部署...")
        install_deps()
        deploy_first_time()
        input("部署完成，按 Enter 键进入管理面板...")
    menu()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 已退出")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)