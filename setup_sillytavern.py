#!/usr/bin/env python3
"""
SillyTavern 一键部署脚本 for Termux (自动 stash 版本)
用法:
    pkg install python git -y
    python setup_sillytavern.py
"""

import os, sys, subprocess
from pathlib import Path

REPO_URL = "https://github.com/SillyTavern/SillyTavern.git"
INSTALL_DIR = Path.home() / "sillytavern"
START_SCRIPT = INSTALL_DIR / "start.sh"
SYMLINK_PATH = Path("/data/data/com.termux/files/usr/bin/sillytavern")

def run(cmd, check=True, shell=False):
    print(f"\n> {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    if isinstance(cmd, list):
        return subprocess.run(cmd, check=check)
    else:
        return subprocess.run(cmd, shell=True, check=check, executable="/bin/bash")

def check_termux():
    if not Path("/data/data/com.termux").exists():
        sys.exit("❌ 请在 Termux 中运行")
    print("✅ Termux 环境")

def install_deps():
    run(["pkg", "update", "-y"])
    run(["pkg", "install", "-y", "git", "nodejs-lts", "python", "build-essential", "binutils", "clang"])
    v = subprocess.check_output(["node", "--version"], text=True).strip()
    if int(v.lstrip('v').split('.')[0]) < 18:
        sys.exit(f"❌ Node.js 版本过低: {v}")

def clone_repo():
    if INSTALL_DIR.exists():
        print(f"⚠️ 目录 {INSTALL_DIR} 已存在，更新模式")
        os.chdir(INSTALL_DIR)
        run(["git", "fetch", "--all"])
    else:
        run(["git", "clone", REPO_URL, str(INSTALL_DIR)])
        os.chdir(INSTALL_DIR)

def stash_changes():
    """自动 stash 所有本地改动，保证干净切换"""
    os.chdir(INSTALL_DIR)
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if result.stdout.strip():
        print("⚠️ 检测到本地改动，自动 stash...")
        run(["git", "stash", "push", "--include-untracked", "-m", "auto-stash"])

def select_version():
    os.chdir(INSTALL_DIR)
    env_ver = os.environ.get("SILLY_VERSION")
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
                tags = subprocess.check_output(["git", "tag", "--sort=-creatordate"], text=True).strip().split("\n")[:10]
                print("最近标签:", ", ".join(tags))
            except: pass
            target = input("请输入分支/标签/提交: ").strip() or "release"
        else:
            target = "release"

    stash_changes()  # ✅ 自动处理本地修改
    print(f"✅ 切换至: {target}")
    run(["git", "checkout", target])
    run(["git", "pull", "origin", target])

def install_npm():
    os.chdir(INSTALL_DIR)
    print("\n=== 安装 npm 依赖 ===")
    run(["npm", "install"])

def create_launcher():
    script = f"""#!/bin/bash
cd {INSTALL_DIR}
echo "Installing Node Modules..."
npm install --no-audit --no-fund --quiet --omit=dev
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

def main():
    check_termux()
    install_deps()
    clone_repo()
    select_version()
    install_npm()
    create_launcher()
    print("\n🎉 完成！输入 sillytavern 启动")

if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 失败: {e}")
        sys.exit(1)