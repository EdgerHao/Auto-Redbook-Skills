# Agent Cluster for Auto-Redbook-Skills

中文 | [English](#english)

## 中文

这是该项目的自用 Agent 集群接入说明（fork + 自用分支模式）。

### 远端策略
- `origin`: 你的 fork（`EdgerHao/Auto-Redbook-Skills`）
- `upstream`: 原项目（`comeonzhj/Auto-Redbook-Skills`）

### 常用同步
```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

### 创建任务（自用分支）
```bash
cd /mnt/c/Users/18024/.openclaw/workspace/Auto-Redbook-Skills
python3 scripts/agent_cluster.py add \
  --id redbook-self-001 \
  --description "self-use feature" \
  --tmux-session redbook-001 \
  --base origin/main \
  --worktree-root /mnt/c/Users/18024/.openclaw/workspace/Auto-Redbook-Skills/worktrees
```

### 启动会话（替换为真实 agent 命令）
```bash
tmux new-session -d -s redbook-001 \
  -c /mnt/c/Users/18024/.openclaw/workspace/Auto-Redbook-Skills/worktrees/redbook-self-001 \
  'sleep 1200'
```

### 监控与恢复
```bash
python3 scripts/agent_cluster.py monitor --json
python3 scripts/cluster_autorestart.py
```

### PR 门禁
```bash
python3 scripts/pr_gate.py <PR_NUMBER>
```

---

## English

This is the self-use Agent Cluster setup for this repo (fork + private branch workflow).

### Remote layout
- `origin`: your fork (`EdgerHao/Auto-Redbook-Skills`)
- `upstream`: source repo (`comeonzhj/Auto-Redbook-Skills`)

### Keep fork updated
```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

### Create a task (self branch)
```bash
cd /mnt/c/Users/18024/.openclaw/workspace/Auto-Redbook-Skills
python3 scripts/agent_cluster.py add \
  --id redbook-self-001 \
  --description "self-use feature" \
  --tmux-session redbook-001 \
  --base origin/main \
  --worktree-root /mnt/c/Users/18024/.openclaw/workspace/Auto-Redbook-Skills/worktrees
```

### Start an agent session (replace with real runner)
```bash
tmux new-session -d -s redbook-001 \
  -c /mnt/c/Users/18024/.openclaw/workspace/Auto-Redbook-Skills/worktrees/redbook-self-001 \
  'sleep 1200'
```

### Monitor and auto-recover
```bash
python3 scripts/agent_cluster.py monitor --json
python3 scripts/cluster_autorestart.py
```

### PR gate
```bash
python3 scripts/pr_gate.py <PR_NUMBER>
```
