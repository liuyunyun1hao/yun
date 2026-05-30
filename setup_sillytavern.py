#!/usr/bin/env python3
"""
SillyTavern 一键部署 v4 - 修复 SSL 后端冲突 + 局域网访问配置
用法: pkg install python git -y && python setup_sillytavern.py
"""

import os, sys, subprocess, socket
from pathlib import Path

REPO_URL = "https://github.com/SillyTavern/SillyTavern.git"
INSTALL_DIR = Path.home() / "sillytavern"
START_SCRIPT = INSTALL_DIR / "start.sh"
SYMLINK_PATH = Path("/data/data/com.termux/files/usr/bin/sillytavern")

def run(cmd, check=True):
    print(f"\n> {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)

def fix_ssl():
    """修复 TLS 证书问题，并移除可能不支持的 sslBackend 设置"""
    print("🔧 配置证书环境...")
    # 清除之前可能设置的错误 SSL 后端
    subprocess.run(["git", "config", "--global", "--unset", "http.sslBackend"],
                   capture_output=True)
    # 安装最新 CA 证书包
    run(["pkg", "install", "-y", "ca-certificates"])
    # 更新系统证书链接 (Termux 中可用)
    os.system("update-ca-certificates 2>/dev/null")

def check_termux():
    if not Path("/data/data/com.termux").exists():
        sys.exit("❌ 请在 Termux 中运行")
    print("✅ Termux 环境")

def install_deps():
    run(["pkg", "update", "-y"])
    run(["pkg", "install", "-y", "git", "nodejs-lts", "python",
         "build-essential", "binutils", "clang", "ca-certificates"])
    fix_ssl()
    # 安装修改配置所需的 pyyaml
    run([sys.executable, "-m", "pip", "install", "pyyaml"])

def clone_repo():
    if INSTALL_DIR.exists():
        print(f"⚠️ 目录 {INSTALL_DIR} 已存在，进入更新模式")
        os.chdir(INSTALL_DIR)
        run(["git", "fetch", "--all", "--tags", "--prune"])
    else:
        run(["git", "clone", REPO_URL, str(INSTALL_DIR)])
        os.chdir(INSTALL_DIR)

def stash_changes():
    os.chdir(INSTALL_DIR)
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if result.stdout.strip():
        print("⚠️ 检测到本地改动，自动 stash...")
        run(["git", "stash", "push", "--include-untracked", "-m", "auto-stash"])

def is_tag(target):
    res = subprocess.run(["git", "tag", "-l", target], capture_output=True, text=True)
    return res.stdout.strip() == target

def is_branch(target):
    res = subprocess.run(["git", "branch", "-r", "--list", f"origin/{target}"],
                         capture_output=True, text=True)
    return bool(res.stdout.strip())

def select_version():
    os.chdir(INSTALL_DIR)
    env_ver = os.environ.get("SILLY_VERSION")
    target = None
    if env_ver:
        target = env_ver
        print(f"✅ 环境变量指定版本: {target}")
    else:
        print("\n=== 选择版本 ===")
        print("1. 稳定版 (release)")
        print("2. 开发版 (main)")
        print("3. 自定义标签/提交")
        choice = input("选择 [1-3] (默认: 1): ").strip() or "1"
        if choice == "1":
            target = "release"
        elif choice == "2":
            target = "main"
        elif choice == "3":
            try:
                tags = subprocess.check_output(
                    ["git", "tag", "--sort=-creatordate"], text=True).strip().split("\n")[:10]
                print("最近标签:", ", ".join(tags))
            except:
                pass
            target = input("请输入分支/标签/提交: ").strip() or "release"
        else:
            target = "release"

    stash_changes()
    print(f"✅ 切换至: {target}")

    if is_tag(target):
        print(f"📌 目标 {target} 是一个标签，直接 checkout (不 pull)")
        run(["git", "checkout", f"tags/{target}"])
    else:
        run(["git", "checkout", target])
        if is_branch(target):
            print(f"🌿 目标 {target} 是一个分支，执行 pull 更新...")
            try:
                run(["git", "pull", "origin", target])
            except subprocess.CalledProcessError:
                print("⚠️ pull 失败，可能网络问题，但已切换版本，继续安装依赖...")
        else:
            print("📌 目标是一个提交号，不执行 pull")

def install_npm():
    os.chdir(INSTALL_DIR)
    print("\n=== 安装 npm 依赖 ===")
    for i in range(3):
        try:
            run(["npm", "install", "--no-audit", "--no-fund"])
            return
        except subprocess.CalledProcessError:
            if i == 2:
                raise
            print(f"npm install 失败，第 {i+1} 次重试...")
            subprocess.run(["npm", "cache", "clean", "--force"])

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

    if SYMLINK_PATH.exists() or os.path.islink(SYMLINK_PATH):
        SYMLINK_PATH.unlink()
    SYMLINK_PATH.symlink_to(START_SCRIPT)
    print("✅ 全局指令 sillytavern 已创建")

def get_lan_ip():
    """获取手机当前的局域网 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return None

def configure_lan_access():
    """询问并配置 SillyTavern 以允许局域网访问"""
    print("\n=== 局域网访问设置 ===")
    print("是否允许同一 WiFi 下的手机/平板访问 SillyTavern？")
    choice = input("启用局域网访问？(y/n) [默认: y]: ").strip().lower()
    if choice and choice != 'y':
        print("⏭️ 保持默认监听本地，只能本机访问。")
        return False

    import yaml
    config_path = INSTALL_DIR / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}
    # 强制开启监听所有接口，并关闭白名单限制
    config['listen'] = True
    config['whitelistMode'] = 'disabled'
    # 移除可能存在的旧白名单列表
    config.pop('whitelist', None)
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    print("✅ 已配置 SillyTavern 监听所有网络接口（0.0.0.0:8000）")
    return True

def main():
    check_termux()
    install_deps()
    clone_repo()
    select_version()
    install_npm()
    create_launcher()
    lan_enabled = configure_lan_access()

    print("\n🎉 部署完成！")
    print("👉 快速启动: sillytavern")
    print("👉 后台运行: tmux new-session -d -s tavern 'sillytavern'")
    if lan_enabled:
        ip = get_lan_ip()
        if ip:
            print(f"\n🌐 局域网访问地址: http://{ip}:8000")
            print("   (请确保手机和平板/手机在同一 WiFi 下)")
        else:
            print("\n⚠️ 无法获取本机 IP，请手动查看 WiFi 设置中的 IP 地址")

if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 部署失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户取消")
        sys.exit(1)