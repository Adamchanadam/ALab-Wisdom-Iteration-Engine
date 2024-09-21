
# 答案迭代器 (Answer Iteration Engine)

## 簡介
這個項目是一個基於 Flask 和 OpenAI 的多層次答案生成系統，旨在通過多次迭代優化來生成高質量的回答。系統通過直接回答、評估和優化流程，不斷改進初始回答，適用於需要深度分析和全面解答的複雜問題。

## 功能
- **提交用戶問題**：用戶輸入問題，系統生成初始的直接 LLM 回答。
- **多層次優化**：系統通過多次評估和優化，生成最終的優化答案。
- **答案比較**：比較直接 LLM 回答與多層次優化回答的質量、全面性和準確性。
- **可視化呈現**：使用圖表顯示每次迭代的評分變化。
- **操作日誌**：記錄每次回答的評分和優化過程，便於查看和分析。

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
    創建 `.env` 文件並添加您的 OpenAI API Key 及 Firecrawl API Key
    ```sh
    OPENAI_API_KEY=your_openai_api_key
    FIRECRAWL_API_KEY=your_firecrawl_api_key
    ```

4. 運行應用程序：
    ```sh
    poetry run python main.py
    ```

應用會在 `http://0.0.0.0:8080` 運行。

## 使用說明
1. 在首頁輸入問題並提交。
2. 系統會生成直接 LLM 回答並顯示在頁面上。
3. 繼續進行多次迭代優化，生成最終的多層次 LLM 回答。
4. 可在頁面查看比較結果、評分及優化過程圖表。

## 目錄結構
<pre><code>
ALab-Wisdom-Iteration-Engine/
├── main.py             # 主程序文件
├── templates/          # HTML 模板文件
│   └── index.html
├── static/             # 靜態文件夾
│   ├── script.js       # 前端 JavaScript
│   └── styles.css      # 頁面樣式
├── pyproject.toml      # Poetry 配置文件
├── README.md           # 項目說明文件
└── .env.example        # 環境變量範例文件
</code></pre>

## 貢獻
歡迎提交 issue 和 pull request 來改進此項目。

## 許可證
此項目基於 MIT 許可證 - 詳見 [LICENSE](LICENSE.md) 文件。
