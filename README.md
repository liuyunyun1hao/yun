最新的部署脚本已加入自动 stash 功能，无论 start.sh 被修改成什么样，切换版本都不会再报错。

🚀 一键部署指令（在 Termux 中粘贴执行）

```bash
pkg install python git -y && \
curl -O https://raw.githubusercontent.com/liuyunyun1hao/yun/main/setup_sillytavern.py && \
python setup_sillytavern.py
```

运行后会让你选择版本（稳定版 / 开发版 / 自定义标签）。

如果你想完全免交互安装，可改用：
SILLY_VERSION=release python setup_sillytavern.py

---

🧠 新脚本特性

· ✅ 自动 stash 本地所有改动，切换版本零障碍
· ✅ 重新生成的 start.sh 使用绝对路径，彻底解决 sillytavern 软链接报错
· ✅ 不再执行 pkg upgrade，避免配置文件冲突卡死
· ✅ 支持环境变量 SILLY_VERSION 静默指定版本

部署完成后，任何时候只需输入：

```bash
sillytavern
```

即可一键启动酒馆。
