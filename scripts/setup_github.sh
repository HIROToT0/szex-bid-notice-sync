#!/usr/bin/env bash
# GitHub 发布脚本：将技能包发布到 GitHub
# 用法: ./scripts/publish_github.sh [github_repo_url]
# 需要先在 GitHub 上创建空仓库

set -e

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SKILL_DIR"

if [ -z "$1" ]; then
    echo "用法: $0 <git_remote_url>"
    echo "例如: $0 https://github.com/yourname/szex-bid-notice-sync.git"
    exit 1
fi

REMOTE="$1"

# 检查是否有 git 仓库
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "初始化 Git 仓库..."
    git init
    git remote add origin "$REMOTE"
else
    echo "Git 仓库已存在"
fi

# 创建 .gitignore
cat > "$SKILL_DIR/.gitignore" << 'EOF'
config/config.json
config/email.json
__pycache__/
*.pyc
*.log
EOF

# 添加所有文件（排除敏感配置）
git add .
git status

echo ""
echo "以上文件将被提交到 GitHub。"
read -p "确认提交? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo "已取消"
    exit 0
fi

BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "main")
git commit -m "feat: 深圳交易集团招标公告抓取技能 v1.0

- 抓取深圳交易集团招标公告（API方式）
- 支持按工程类型/时间范围过滤
- 详情页提取投标截止时间、招标估算等字段
- 写入飞书多维表格
- 支持邮件通知"

echo ""
read -p "推送到 GitHub? (y/n): " push_confirm
if [ "$push_confirm" == "y" ]; then
    git push -u origin "$BRANCH"
    echo "✅ 推送成功!"
fi
