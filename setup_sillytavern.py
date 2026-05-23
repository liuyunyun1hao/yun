#!/usr/bin/env python3
"""
SillyTavern 一键部署脚本 for Termux
用法:
    pkg install python git -y
    python setup_sillytavern.py
静默安装（不询问版本）：
    SILLY_VERSION=release python setup_sillytavern.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# ========== 配置 ==========
REPO_URL = "https://github.com/SillyTavern/SillyTavern.git"
INSTALL_DIR = Path.home() / "sillytavern"
START_SCRIPT = INSTALL_DIR / "start.sh"
SYMLINK_PATH = Path("/data/data/com.termux/files/usr/bin/sillytavern")
# ==========================

def run(cmd, check=True, shell=False):
    """执行命令并实时输出"""
    print(f"\n> {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    if isinstance(cmd, list):
        return subprocess.run(cmd, check=check)
    else:
        return subprocess.run(cmd, shell=True, check=check, executable="/bin/bash")

def check_termux():
    """确保在 Termux 环境中运行"""
    if not Path("/data/data/com.termux").exists():
        print("❌ 此脚本只能在 Termux 中运行！")
        sys.exit(1)
    print("✅ 检测到 Termux 环境")

def install_dependencies():
    """安装 Termux 所需软件包"""
    print("\n=== 更新软件源 & 安装依赖 ===")
    run(["pkg", "update", "-y"])
    # 注意：pkg upgrade 已移除，避免配置冲突卡死
    deps = ["git", "nodejs-lts", "python", "build-essential", "binutils", "clang"]
    run(["pkg", "install", "-y"] + deps)
    # 检查 node 版本
    node_version = subprocess.check_output(["node", "--version"], text=True).strip()
    if int(node_version.lstrip('v').split('.')[0]) < 18:
        print("❌ Node.js 版本过低，需要 18+，当前:", node_version)
        sys.exit(1)
    print(f"✅ Node.js 版本: {node_version}")

def clone_repo():
    """克隆 SillyTavern 仓库"""
    if INSTALL_DIR.exists():
        print(f"⚠️ 目录 {INSTALL_DIR} 已存在，将进入更新模式...")
        os.chdir(INSTALL_DIR)
        run(["git", "fetch", "--all"])
    else:
        print("\n=== 克隆 SillyTavern 仓库 ===")
        run(["git", "clone", REPO_URL, str(INSTALL_DIR)])
        os.chdir(INSTALL_DIR)

def select_version():
    """版本选择（支持环境变量跳过交互）"""
    os.chdir(INSTALL_DIR)
    # 如果环境变量 SILLY_VERSION 已设置，直接使用
    env_version = os.environ.get("SILLY_VERSION")
    if env_version:
        target = env_version
        print(f"✅ 通过环境变量指定版本: {target}")
    else:
        print("\n=== 选择版本 ===")
        print("1. 稳定版 (release 分支)")
        print("2. 最新开发版 (main 分支)")
        print("3. 自定义标签/提交 (手动输入)")
        choice = input("请选择 [1-3] (默认: 1): ").strip() or "1"
        if choice == "1":
            target = "release"
        elif choice == "2":
            target = "main"
        elif choice == "3":
            try:
                tags = subprocess.check_output(["git", "tag", "--sort=-creatordate"], text=True).strip().split("\n")[:10]
                print("可用的最近标签:")
                for t in tags:
                    print(f"  {t}")
            except:
                pass
            target = input("请输入分支名或标签名: ").strip()
            if not target:
                print("❌ 未输入有效值，使用默认 release")
                target = "release"
        else:
            target = "release"

    print(f"✅ 切换至: {target}")
    run(["git", "checkout", target])
    run(["git", "pull", "origin", target])

def install_npm():
    """安装 Node.js 依赖"""
    os.chdir(INSTALL_DIR)
    print("\n=== 安装 npm 依赖 (可能需要几分钟) ===")
    run(["npm", "install"])

def create_launcher():
    """创建健壮的一键启动脚本"""
    # 生成启动脚本（绝对路径，避免软链接歧义）
    script_content = f"""#!/bin/bash
cd {INSTALL_DIR}
echo "Installing Node Modules..."
npm install --no-audit --no-fund --quiet --omit=dev
echo "Entering SillyTavern..."
node server.js
"""
    with open(START_SCRIPT, "w") as f:
        f.write(script_content)
    os.chmod(START_SCRIPT, 0o755)
    print(f"✅ 启动脚本已创建: {START_SCRIPT}")

    # 创建或更新软链接
    if SYMLINK_PATH.exists() or os.path.islink(SYMLINK_PATH):
        SYMLINK_PATH.unlink()
    SYMLINK_PATH.symlink_to(START_SCRIPT)
    print(f"✅ 全局指令已创建: sillytavern")
    print("   以后在 Termux 任意目录输入 sillytavern 即可一键启动")

def main():
    check_termux()
    install_dependencies()
    clone_repo()
    select_version()
    install_npm()
    create_launcher()
    print("\n🎉 部署完成！")
    print("启动方式： 直接输入 sillytavern 并回车")
    print(f"或者手动运行:  {START_SCRIPT}")

if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 命令执行失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户取消操作")
        sys.exit(1)