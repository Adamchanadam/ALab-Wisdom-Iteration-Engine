#!/bin/bash

# 初始化Git
git init

# 添加所有文件到Git的追踪範圍
git add .

# 提交文件
git commit -m "初始化項目，添加所有文件"

# 將本地倉庫與GitHub遠程倉庫關聯
git remote add origin https://github.com/Adamchanadam/ALab-Wisdom-Iteration-Engine.git

# 推送到GitHub
git push -u origin main