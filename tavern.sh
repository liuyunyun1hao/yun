#!/bin/bash

# ==========================================
# SillyTavern 傻酒馆 终极后台守护版 (支持穿透与OTA)
# ==========================================

INSTALL_DIR="$HOME/SillyTavern"
BACKUP_DIR="$HOME/SillyTavern_Data_Backup"
RAW_URL="https://raw.githubusercontent.com/liuyunyun1hao/yun/main/tavern.sh"

GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m'

echo_info() { echo -e "${GREEN}[+] $1${NC}"; }
echo_warn() { echo -e "${YELLOW}[!] $1${NC}"; }
echo_err() { echo -e "${RED}[-] $1${NC}"; }

# 1. 一键全自动部署
deploy_tavern() {
    echo_info "正在装配 Termux 基础环境 (含 Tmux 与 SSH 穿透依赖)..."
    pkg update && pkg upgrade -y
    pkg install git nodejs-lts python make clang tmux openssh -y
    
    if [ -d "$INSTALL_DIR" ]; then
        echo_warn "已存在 $INSTALL_DIR 目录，跳过克隆。"
    else
        echo_info "正在克隆 SillyTavern 最新纯净代码..."
        git clone https://github.com/SillyTavern/SillyTavern.git "$INSTALL_DIR"
    fi
    
    cd "$INSTALL_DIR" || exit
    echo_info "正在配置镜像源并安装运行依赖..."
    rm -rf node_modules package-lock.json
    npm config set registry https://registry.npmmirror.com/
    npm install
    echo_info "🎉 部署完成！"
}

# 2. 后台守护启动 (Tmux)
start_tavern_bg() {
    if [ ! -d "$INSTALL_DIR" ]; then echo_err "未找到酒馆程序，请先部署"; return; fi
    # 检查 tmux 是否安装
    if ! command -v tmux &> /dev/null; then pkg install tmux -y; fi
    
    if tmux has-session -t tavern 2>/dev/null; then
        echo_warn "酒馆已经在后台稳定运行中！"
        echo_info "内网访问: http://127.0.0.1:8000"
    else
        cd "$INSTALL_DIR" || exit
        # 创建一个名为 tavern 的 tmux 后台会话并运行 node server.js
        tmux new-session -d -s tavern 'node server.js'
        echo_info "🚀 傻酒馆已进入后台守护模式！"
        echo_info "现在你可以放心去做别的事，就算切出 Termux，酒馆也会保持运行。"
        echo_warn "内网访问: http://127.0.0.1:8000"
    fi
}

# 3. 停止后台守护
stop_tavern_bg() {
    if tmux has-session -t tavern 2>/dev/null; then
        tmux kill-session -t tavern
        echo_info "已成功关闭后台运行的酒馆服务器。"
    else
        echo_err "当前没有在后台运行的酒馆程序。"
    fi
}

# 4. 一键内网穿透 (Pinggy)
start_tunnel() {
    echo_info "正在为您配置极速内网穿透环境..."
    if ! command -v ssh &> /dev/null; then pkg install openssh -y; fi
    
    echo_warn "================================================="
    echo_warn "通道建立后，屏幕上会出现一个以 [https://] 开头的网址。"
    echo_warn "复制该网址，即可在任何网络环境下访问你的酒馆！"
    echo_warn "结束穿透请直接按键盘上的 [Ctrl + C]。"
    echo_warn "================================================="
    sleep 3
    # 利用 Pinggy 极简隧道将本地 8000 端口映射到公网
    ssh -p 443 -R0:localhost:8000 -o StrictHostKeyChecking=no a.pinggy.io
}

# 5. 版本管理
manage_versions() {
    if [ ! -d "$INSTALL_DIR" ]; then echo_err "请先部署酒馆"; return; fi
    cd "$INSTALL_DIR" || exit
    git fetch --tags
    echo_warn "最近的 10 个正式版本号参考："
    git tag -l | tail -n 10
    read -p "请输入要切换的版本号 (如 1.12.0): " v_num
    if [ -n "$v_num" ]; then
        [ -d "data" ] && cp -r data "$HOME/temp_tavern_data"
        git checkout -f "$v_num"
        [ -d "$HOME/temp_tavern_data" ] && rm -rf data && mv "$HOME/temp_tavern_data" data
        rm -rf node_modules package-lock.json
        npm install
        echo_info "🎉 成功切换至版本 $v_num ！"
    fi
}

# 6. 数据备份与恢复
manage_data() {
    echo "============================="
    echo " 1. 备份当前数据到安全区"
    echo " 2. 将备份数据恢复到酒馆"
    echo "============================="
    read -p "请选择 [1-2]: " d_choice
    case $d_choice in
        1)
            [ ! -d "$INSTALL_DIR/data" ] && echo_err "无可备份数据" && return
            rm -rf "$BACKUP_DIR" && cp -r "$INSTALL_DIR/data" "$BACKUP_DIR"
            echo_info "🎉 数据已备份至: $BACKUP_DIR"
            ;;
        2)
            [ ! -d "$BACKUP_DIR" ] && echo_err "无备份数据" && return
            rm -rf "$INSTALL_DIR/data" && cp -r "$BACKUP_DIR" "$INSTALL_DIR/data"
            echo_info "🎉 数据已完美恢复！"
            ;;
        *) echo_err "无效输入" ;;
    esac
}

# 7. 快捷指令写入
setup_shortcut() {
    echo_info "正在配置全局唤醒指令..."
    echo "bash $HOME/tavern.sh" > $PREFIX/bin/酒馆
    chmod +x $PREFIX/bin/酒馆
    echo_info "🎉 配置成功！以后在 Termux 中输入【酒馆】并回车即可随时唤出面板！"
}

# 8. OTA 脚本自我更新
self_update() {
    echo_info "正在连接 Github 检查最新脚本代码..."
    TMP_FILE="$PREFIX/tmp/tavern_new.sh"
    # 静默下载云端代码到临时文件
    curl -sL "$RAW_URL" -o "$TMP_FILE"
    
    # 简单的完整性验证：确保下载下来的文件里包含我们的核心关键词
    if grep -q "SillyTavern" "$TMP_FILE"; then
        mv "$TMP_FILE" "$HOME/tavern.sh"
        chmod +x "$HOME/tavern.sh"
        echo_info "🎉 脚本已成功从你的 Github 更新到最新版！"
        echo_warn "正在自动重启面板，请稍候..."
        sleep 2
        exec bash "$HOME/tavern.sh"
    else
        echo_err "更新失败！可能是网络波动或未读取到 Github 数据，请稍后再试。"
        rm -f "$TMP_FILE"
    fi
}

# 主菜单
while true; do
    clear
    echo -e "${GREEN}==========================================${NC}"
    echo -e "${GREEN}   SillyTavern 傻酒馆 终极后台守护版      ${NC}"
    echo -e "${GREEN}==========================================${NC}"
    echo -e "${BLUE} 1. [部署] 一键自动部署酒馆基础环境${NC}"
    echo -e "${BLUE} 2. [启动] 🚀 后台静默启动 (锁屏不断联)${NC}"
    echo -e "${BLUE} 3. [停止] ⏹ 关闭后台运行的酒馆${NC}"
    echo "------------------------------------------"
    echo -e "${BLUE} 4. [穿透] 🌐 生成公网链接 (免费无门槛)${NC}"
    echo -e "${BLUE} 5. [版本] 🔄 回退或更新指定酒馆版本${NC}"
    echo -e "${BLUE} 6. [数据] 💾 备份 或 恢复个人核心数据${NC}"
    echo "------------------------------------------"
    echo -e "${BLUE} 7. [系统] ⌨️  写入全局指令 (输入“酒馆”秒开)${NC}"
    echo -e "${BLUE} 8. [升级] ⬆️  一键更新本面板脚本 (OTA)${NC}"
    echo -e "${BLUE} 0. 退出面板${NC}"
    echo "=========================================="
    read -p "请输入选择 [0-8]: " choice

    case $choice in
        1) deploy_tavern; read -p "按回车键返回..." ;;
        2) start_tavern_bg; read -p "按回车键返回..." ;;
        3) stop_tavern_bg; read -p "按回车键返回..." ;;
        4) start_tunnel; read -p "按回车键返回..." ;;
        5) manage_versions; read -p "按回车键返回..." ;;
        6) manage_data; read -p "按回车键返回..." ;;
        7) setup_shortcut; read -p "按回车键返回..." ;;
        8) self_update ;; # 更新后会自动 exec 重启，无需 read 暂停
        0) echo_info "再见！"; exit 0 ;;
        *) echo_err "无效输入！"; sleep 1 ;;
    esac
done
