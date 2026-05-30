好的，以下三条指令涵盖了从部署到后台保活的全过程，按顺序执行即可。

1️⃣ 全新一键部署

```bash
git config --global --unset http.sslBackend ; pkg install python git tmux -y && curl -O https://raw.githubusercontent.com/liuyunyun1hao/yun/main/setup_sillytavern.py && python setup_sillytavern.py
```

部署完成后，sillytavern 命令即可全局使用。

2️⃣ 快速前台启动（临时使用）

```bash
sillytavern
```

3️⃣ 后台持续运行（关闭 Termux 也不中断）

```bash
tmux new-session -d -s tavern 'sillytavern'
```

· 需要查看运行状态：tmux attach -t tavern
· 在会话中按 Ctrl+b 再按 d 即可安全脱离
· 彻底关闭：tmux kill-session -t tavern

使用后台模式后，手机息屏、切出 Termux 都不会影响酒馆运行，建议配合电池优化白名单与 Wakelock 使用以获得最佳稳定性。
