#!/bin/bash

# 檢查當前倉庫狀態
git status

# 添加新文件和更改的文件
git add .

# 提交更改，附上有意義的提交信息
git commit -m "檔案或代碼更新..."

# 推送到 GitHub
git push origin main