#!/bin/bash

# 檢查當前倉庫狀態
git status

# 添加除 deploy.sh 和 update.sh 外的所有文件到 Git 的追踪範圍
git add --all

# 排除 deploy.sh 和 update.sh
git reset deploy.sh update.sh

# 提交更改，附上有意義的提交信息
git commit -m "一般更新..."

# 命令拉取遠程 main 分支的更改並將您的更改應用在上面，避免產生額外的合併提交。
git pull origin main --rebase

# 推送到 GitHub
git push origin main