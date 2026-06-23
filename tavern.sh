#!/bin/bash

# ==========================================
# SillyTavern 傻酒馆 完美避坑版云端部署脚本
# ==========================================

INSTALL_DIR="$HOME/SillyTavern"
BACKUP_DIR="$HOME/SillyTavern_Data_Backup"

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
    echo_info "正在装配 Termux 基础环境..."
    pkg update && pkg upgrade -y
    pkg install git nodejs-lts python make clang -y
    
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

# 2. 一键启动酒馆
start_tavern() {
    if [ ! -d "$INSTALL_DIR" ]; then echo_err "未找到酒馆程序，请先部署"; return; fi
    cd "$INSTALL_DIR" || exit
    echo_info "🚀 傻酒馆正在启动..."
    echo_warn "请在手机浏览器访问: http://127.0.0.1:8000"
    node server.js
}

# 3. 版本管理
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

# 4. 数据备份与恢复
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

# 快捷指令写入
setup_shortcut() {
    echo_info "正在配置全局唤醒指令..."
    echo "bash $HOME/tavern.sh" > $PREFIX/bin/酒馆
    chmod +x $PREFIX/bin/酒馆
    echo_info "🎉 配置成功！以后在 Termux 中输入【酒馆】并回车即可唤醒本面板！"
}

# 主菜单
while true; do
    clear
    echo -e "${GREEN}==========================================${NC}"
    echo -e "${GREEN}   SillyTavern 傻酒馆 完美避坑云端版      ${NC}"
    echo -e "${GREEN}==========================================${NC}"
    echo -e "${BLUE} 1. [部署] 一键全自动部署环境与酒馆${NC}"
    echo -e "${BLUE} 2. [打开] 一键启动酒馆服务器${NC}"
    echo "------------------------------------------"
    echo -e "${BLUE} 3. [版本] 回退或更新到指定版本号${NC}"
    echo -e "${BLUE} 4. [数据] 备份 或 恢复个人数据${NC}"
    echo -e "${BLUE} 5. [全局] 写入“酒馆”全局快捷唤醒指令${NC}"
    echo "------------------------------------------"
    echo -e "${BLUE} 0. 退出${NC}"
    echo "=========================================="
    read -p "请输入选择 [0-5]: " choice

    case $choice in
        1) deploy_tavern; read -p "按回车键返回..." ;;
        2) start_tavern; read -p "按回车键返回..." ;;
        3) manage_versions; read -p "按回车键返回..." ;;
        4) manage_data; read -p "按回车键返回..." ;;
        5) setup_shortcut; read -p "按回车键返回..." ;;
        0) echo_info "再见！"; exit 0 ;;
        *) echo_err "无效输入！"; sleep 1 ;;
    esac
done
