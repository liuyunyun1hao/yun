# SillyTavern 傻酒馆 Termux 一键云端部署脚本

专为 Android Termux 环境设计的 SillyTavern（傻酒馆）全自动部署与管理脚本。完美避开 Node.js 版本过高导致的底层冲突，支持一键无痛换源、版本自由穿梭及数据安全管理。

## ✨ 核心特性

* **环境自适应**：从零自动配置 Git、Node.js (LTS 稳定版) 以及 C++ 编译环境。
* **全局秒唤醒**：支持配置中文指令，随时随地输入 `酒馆` 即可唤出管理面板。
* **数据防丢屏障**：安全分离 `data` 目录。不论你怎么重装、降级，你的所有专属角色卡、世界书和聊天记录都能一键无缝恢复，沉浸式剧情永不丢失。
* **自由穿梭机**：无需懂 Git 命令，一键查询官方历史标签，输入版本号即可精准回退/更新，并自动重配对应版本的依赖包。

---

## 🚀 极速部署指南 (适用于全新 Termux)

打开 Termux，直接复制并运行以下一行命令（自动拉取云端脚本并运行）：

```bash
curl -O [https://raw.githubusercontent.com/liuyunyun1hao/yun/main/tavern.sh](https://raw.githubusercontent.com/liuyunyun1hao/yun/main/tavern.sh) && chmod +x tavern.sh && ./tavern.sh
```