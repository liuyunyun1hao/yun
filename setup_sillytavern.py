# ...（前面所有代码保持不变，直到 create_launcher() 函数之后）

def create_manage_script():
    """创建交互式管理菜单脚本"""
    manage_script = INSTALL_DIR / "tavern_manage.sh"
    content = f"""#!/bin/bash
cd {INSTALL_DIR}
show_menu() {{
    clear
    echo "╔════════════════════════════════╗"
    echo "║   🍺 SillyTavern 管理面板   ║"
    echo "╠════════════════════════════════╣"
    echo "║ 1. 前台启动 (当前终端)       ║"
    echo "║ 2. 后台启动 (tmux 守护)      ║"
    echo "║ 3. 进入后台会话 (查看输出)   ║"
    echo "║ 4. 停止后台服务              ║"
    echo "║ 5. 显示局域网访问地址        ║"
    echo "║ 6. 退出菜单                  ║"
    echo "╚════════════════════════════════╝"
    echo ""
}}

get_ip() {{
    python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8',80)); print(s.getsockname()[0]); s.close()" 2>/dev/null || echo "未获取到IP"
}}

while true; do
    show_menu
    read -p "请输入选项 [1-6]: " choice
    case $choice in
        1)
            echo "🚀 前台启动 SillyTavern..."
            {START_SCRIPT}
            ;;
        2)
            if tmux has-session -t tavern 2>/dev/null; then
                echo "⚠️ 后台会话已存在，请先停止或进入会话查看"
            else
                echo "🌙 后台启动 (tmux 守护)..."
                tmux new-session -d -s tavern "{START_SCRIPT}"
                echo "✅ 已启动，可使用选项 3 进入查看，或直接访问"
                ip=\\$(get_ip)
                [[ -n "\\$ip" ]] && echo "🌐 访问地址: http://\\$ip:8000"
            fi
            ;;
        3)
            if tmux has-session -t tavern 2>/dev/null; then
                echo "进入会话 (按 Ctrl+b 再按 d 脱离)..."
                sleep 1
                tmux attach -t tavern
            else
                echo "❌ 没有运行中的会话"
            fi
            ;;
        4)
            if tmux has-session -t tavern 2>/dev/null; then
                echo "⏹️ 正在停止后台会话..."
                tmux kill-session -t tavern
                echo "✅ 已停止"
            else
                echo "❌ 没有运行中的会话"
            fi
            ;;
        5)
            ip=\\$(get_ip)
            if [[ -n "\\$ip" ]]; then
                echo "🌐 局域网访问地址: http://\\$ip:8000"
            else
                echo "❌ 无法获取 IP，请检查 WiFi 连接"
            fi
            ;;
        6)
            echo "👋 再见！"
            exit 0
            ;;
        *)
            echo "无效输入，请重试"
            ;;
    esac
    echo ""
    read -p "按回车键继续..."
done
"""
    with open(manage_script, "w") as f:
        f.write(content)
    os.chmod(manage_script, 0o755)

    # 创建全局命令 tavern
    tavern_link = Path("/data/data/com.termux/files/usr/bin/tavern")
    if tavern_link.exists() or os.path.islink(tavern_link):
        tavern_link.unlink()
    tavern_link.symlink_to(manage_script)
    print("✅ 全局管理面板命令 tavern 已创建")

def main():
    check_termux()
    install_deps()
    clone_repo()
    select_version()
    install_npm()
    create_launcher()
    lan_enabled = configure_lan_access()
    create_manage_script()  # 新增

    print("\n🎉 部署完成！")
    print("👉 快速启动: sillytavern")
    print("👉 管理面板: tavern")
    print("👉 后台运行: tmux new-session -d -s tavern 'sillytavern'")
    if lan_enabled:
        ip = get_lan_ip()
        if ip:
            print(f"\n🌐 局域网访问地址: http://{ip}:8000")
            print("   (请确保所有设备在同一 WiFi 下)")
        else:
            print("\n⚠️ 无法获取本机 IP，请手动查看 WiFi 设置中的 IP 地址")