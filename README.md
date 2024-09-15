# 智慧迭代器 (Wisdom Iteration Engine)

## 簡介
這個項目是一個基於 Flask 和 OpenAI 的多層次答案生成系統，旨在通過迭代優化來生成高質量的回答。系統通過多次評估和優化，不斷改進初始回答，適用於需要深度分析和全面解答的複雜問題。

## 功能
- 提交用戶問題，生成直接 LLM 回答。
- 通過多輪迭代優化，生成最終的優化答案。
- 比較直接 LLM 回答與優化後的多層次 LLM 回答。
- 顯示回答過程中的操作日誌。

## 安裝和運行
### 環境需求
- Python 版本 3.10 或更高
- `poetry` 作為依賴管理工具

### 安裝步驟
1. 克隆此倉庫：
    ```sh
    git clone https://github.com/Adamchanadam/ALab-Wisdom-Iteration-Engine.git
    cd ALab-Wisdom-Iteration-Engine
    ```

2. 安裝依賴：
    ```sh
    poetry install
    ```

3. 環境變量配置：
    創建 `.env` 文件並添加您的 OpenAI API Key
    ```sh
    OPENAI_API_KEY=your_openai_api_key
    ```

4. 運行應用程序：
    ```sh
    poetry run python main.py
    ```

應用會在 `http://0.0.0.0:8080` 運行。

## 目錄結構
智慧迭代器/
├── main.py # 主程序文件
├── templates/ # HTML 模板文件
│ └── index.html
├── pyproject.toml # Poetry 配置文件
└── README.md # 項目說明文件


## 貢獻
歡迎提交 issue 和 pull request 來改進此項目。

## 許可證
此項目基於 MIT 許可證 - 詳見 [LICENSE](LICENSE.md) 文件。