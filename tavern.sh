#!/bin/bash

# ==========================================
# SillyTavern 傻酒馆 智能环境穿梭版 (支持新老版本无缝兼顾与OTA)
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
    echo_info "正在装配 Termux 基础环境 (默认安装最新 LTS 稳定版)..."
    pkg update && pkg upgrade -y
    pkg install git nodejs-lts python make clang tmux net-tools -y
    
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
    if ! command -v tmux &> /dev/null; then pkg install tmux -y; fi
    
    if tmux has-session -t tavern 2>/dev/null; then
        echo_warn "酒馆已经在后台稳定运行中！"
        echo_info "手机本机访问: http://127.0.0.1:8000"
    else
        cd "$INSTALL_DIR" || exit
        tmux new-session -d -s tavern 'node server.js'
        echo_info "🚀 傻酒馆已进入后台守护模式！"
        echo_info "现在你可以放心去做别的事，就算切出 Termux，酒馆也会保持运行。"
        echo_warn "手机本机访问: http://127.0.0.1:8000"
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

# 4. 开启局域网互连 (同 WiFi 访问)
enable_lan_access() {
    if [ ! -d "$INSTALL_DIR" ]; then echo_err "请先部署酒馆"; return; fi
    cd "$INSTALL_DIR" || exit
    echo_info "正在配置局域网访问权限..."
    
    if [ ! -f "config.yaml" ]; then
        echo_err "未找到 config.yaml。请先执行一次【选项 2】启动酒馆，让其生成默认配置后再试。"
        return
    fi
    
    # 修改配置并开启白名单模式防止安全报错闪退
    sed -i 's/listen: false/listen: true/g' config.yaml
    sed -i 's/whitelistMode: false/whitelistMode: true/g' config.yaml
    
    WIFI_IP=$(ifconfig 2>/dev/null | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | head -n 1)
    
    if [ -z "$WIFI_IP" ]; then
        echo_err "无法获取 WiFi 局域网 IP，请检查手机是否已连接 WiFi！"
    else
        echo_warn "================================================="
        echo_warn "🌐 局域网共享已配置成功！"
        echo_info "请确保你的其他设备和这台手机连着【同一个 WiFi】"
        echo_info "然后在其他设备的浏览器中输入以下地址："
        echo_warn "👉 http://$WIFI_IP:8000"
        echo_warn "================================================="
    fi
}

# 5. 智能版本管理 (核心进化：带环境自动侦测降级/升级)
manage_versions() {
    if [ ! -d "$INSTALL_DIR" ]; then echo_err "请先部署酒馆"; return; fi
    cd "$INSTALL_DIR" || exit
    
    # 强制杀掉当前可能运行的酒馆
    pkill node; tmux kill-session -t tavern 2>/dev/null
    
    echo_info "正在从云端拉取官方所有历史版本标签..."
    git fetch --tags
    echo_warn "最近的 10 个正式版本号参考："
    git tag -l | tail -n 10
    echo "------------------------------------------"
    
    read -p "请输入你想切换的版本号 (例如 1.15.0、1.18.0 或 release): " v_num
    if [ -z "$v_num" ]; then echo_err "版本号不能为空！"; return; fi
    
    # 先安全备份当前的用户 data 数据
    [ -d "data" ] && cp -r data "$HOME/temp_tavern_data_run"
    
    # --- 💡 核心魔法逻辑：环境自动穿梭 ---
    if [[ "$v_num" == "1.15."* || "$v_num" == "1.14."* || "$v_num" == "1.13."* ]]; then
        echo_warn "⚠️ 检测到属于老旧版本，正在为您将底层环境安全降级至 Node.js v20..."
        pkg uninstall nodejs-lts nodejs -y > /dev/null 2>&1
        pkg install nodejs20 -y
    else
        echo_info "✨ 检测到属于新版分支，正在为您将底层环境安全升级至最新 Node.js LTS..."
        pkg uninstall nodejs20 nodejs -y > /dev/null 2>&1
        pkg install nodejs-lts -y
    fi
    # -------------------------------------

    echo_info "正在强制重置酒馆代码切片至: $v_num ..."
    git checkout -f "$v_num"
    
    # 恢复数据防丢
    if [ -d "$HOME/temp_tavern_data_run" ]; then
        rm -rf data && mv "$HOME/temp_tavern_data_run" data
    fi
    
    echo_info "正在深度清理旧缓存，并根据新环境重装专属依赖..."
    rm -rf node_modules package-lock.json data/_webpack
    npm config set registry https://registry.npmmirror.com/
    npm config set fetch-retries 5
    npm config set fetch-timeout 600000
    npm install
    
    echo_info "🎉 恭喜！版本 $v_num 及其对应的底层 Node.js 环境已全部全自动配套搭建完毕！"
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
    mkdir -p "$PREFIX/tmp"
    curl -sL "$RAW_URL" -o "$TMP_FILE"
    
    if grep -q "SillyTavern" "$TMP_FILE"; then
        mv "$TMP_FILE" "$HOME/tavern.sh"
        chmod +x "$HOME/tavern.sh"
        echo_info "🎉 脚本已成功从你的 Github 更新到最新版！"
        echo_warn "正在自动重启面板，请稍候..."
        sleep 2
        exec bash "$HOME/tavern.sh"
    else
        echo_err "更新失败！可能是网络波动，请稍后再试。"
        rm -f "$TMP_FILE"
    fi
}

# 主菜单
while true; do
    clear
    echo -e "${GREEN}==========================================${NC}"
    echo -e "${GREEN}   SillyTavern 傻酒馆 智能环境穿梭版      ${NC}"
    echo -e "${GREEN}==========================================${NC}"
    echo -e "${BLUE} 1. [部署] 一键自动部署酒馆基础环境${NC}"
    echo -e "${BLUE} 2. [启动] 🚀 后台静默启动 (锁屏不断联)${NC}"
    echo -e "${BLUE} 3. [停止] ⏹ 关闭后台运行的酒馆${NC}"
    echo "------------------------------------------"
    echo -e "${BLUE} 4. [局域] 🌐 获取局域网直连 IP (同 WiFi 互通)${NC}"
    echo -e "${BLUE} 5. [版本] 🔄 智能无痛切换版本 (含环境自适应)${NC}"
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
        4) enable_lan_access; read -p "按回车键返回..." ;;
        5) manage_versions; read -p "按回车键返回..." ;;
        6) manage_data; read -p "按回车键返回..." ;;
        7) setup_shortcut; read -p "按回车键返回..." ;;
        8) self_update ;; 
        0) echo_info "再见！"; exit 0 ;;
        *) echo_err "无效输入！"; sleep 1 ;;
    esac
done
