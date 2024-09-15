#!/bin/bash

# 初始化 Git
git init

# 檢查當前倉庫狀態
git status

# 添加除 deploy.sh 和 update.sh 外的所有文件到 Git 的追踪範圍
git add --all

# 排除 deploy.sh 和 update.sh
git reset deploy.sh update.sh

# 提交更改，附上有意義的提交信息
git commit -m "初始化項目，添加所有文件"

# 將本地倉庫與 GitHub 遠程倉庫關聯
git remote add origin https://github.com/Adamchanadam/ALab-Wisdom-Iteration-Engine.git

# 推送到 GitHub
git push -u origin main