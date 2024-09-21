from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import os
import re
import tiktoken
from replit.object_storage import Client  # 引入 Replit Object Storage
from firecrawl import FirecrawlApp  # 引入 Firecrawl
import tiktoken
import datetime

# 設置 Firecrawl API 金鑰
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
firecrawl_app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

CURRENT_DATE = datetime.datetime.now().strftime("%Y-%m-%d")

# 設置 Flask 應用程序
app = Flask(__name__, static_folder='static')

# 初始化 OpenAI 客戶端
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 初始化 Replit Object Storage 客戶端
storage_client = Client()

# 設置模型名稱
MODEL_NAME = "gpt-4o-mini-2024-07-18"


# 記錄搜索日志
def log_search(user_question, model_name, direct_tokens, final_tokens, best_score):
    log_entry = (f"Date: {datetime.datetime.now()}\n"
                 f"User Question: {user_question}\n"
                 f"Model Used: {model_name}\n"
                 f"Direct LLM Tokens: {direct_tokens}\n"
                 f"Final Optimized LLM Tokens: {final_tokens}\n"
                 f"Best Score: {best_score:.2f}\n"
                 "----------------------------------------\n")
    log_filename = "adam-llm-iteration.log"  # system log
    existing_log = ""
    try:
        existing_log = storage_client.download_as_text(log_filename)
    except Exception:
        pass  # 日誌文件不存在，略過
    new_log = existing_log + log_entry
    storage_client.upload_from_text(log_filename, new_log)


# 添加查看 adam-llm-iteration.log 的路由
@app.route('/view-log', methods=['GET'])
def view_log():
    try:
        log_content = storage_client.download_as_text("adam-llm-iteration.log")
        return log_content
    except Exception as e:
        return str(e), 500


# 計算文本的 token 數量
def count_tokens(text):
    encoder = tiktoken.encoding_for_model(MODEL_NAME)
    return len(encoder.encode(text))


# 格式化回答
def format_answer(response):
    answer = response.choices[0].message.content.strip()
    if response.choices[0].finish_reason == 'length':
        answer += '... ...'
    return answer


# 使用目標 LLM 生成答案
def target_llm(prompt, additional_info=""):
    if additional_info:
        prompt = f"今天是 {CURRENT_DATE}。以下是原始的補充資料(參考資料不一定正確)，請謹慎地分析、篩選合適的資料來組織答案，留意資料中所屬的時間範圍是否與問題有關，如果問題涉及 2023 年10月前你要運用你的知識庫去回答，再用補充資料來輔助(如有);如果問題涉及 2023 年10月後，你要從補充資料中提取有關資料去回答(如有)，再用知識庫去輔助 ：\n\n{additional_info}\n\n{prompt}"
    full_prompt = f"今天是 {CURRENT_DATE}。{prompt}"
    response = client.chat.completions.create(model=MODEL_NAME,
                                              messages=[{
                                                  "role": "user",
                                                  "content": 
                                                  f"根據以下問題以繁體中文生成答案：{prompt}"
                                              }],
                                              max_tokens=2000,
                                              temperature=0.3)
    answer = format_answer(response)
    tokens_used = response.usage.total_tokens
    print(f"[INFO] target_llm: tokens_used = {tokens_used}")  # 添加日誌
    return answer, tokens_used

# 直接使用 LLM 生成答案
def direct_llm(prompt, additional_info=""):
    if additional_info:
        additional_info_processed = handle_additional_info(additional_info)
        full_additional_info = additional_info_processed["content"]

        prompt = f"今天是 {CURRENT_DATE}。以下是原始的補充資料(參考資料不一定正確)，請謹慎地分析、篩選合適的資料來組織答案，留意資料中所屬的時間範圍是否與問題有關，如果問題涉及 2023 年10月前你要運用你的知識庫去回答，再用補充資料來輔助(如有);如果問題涉及 2023 年10月後，你要優先從補充資料中提取有關資料去回答(如有)，再用知識庫去輔助 ：\n\n{full_additional_info}\n\n{prompt}"
    response = client.chat.completions.create(model=MODEL_NAME,
                                              messages=[{
                                                  "role":
                                                  "user",
                                                  "content":
                                                  f"根據以下問題以繁體中文生成答案：{prompt}"
                                              }],
                                              max_tokens=2000,
                                              temperature=0.3)
    answer = format_answer(response)
    tokens_used = response.usage.total_tokens
    print(f"[INFO] direct_llm: tokens_used = {tokens_used}")  # 添加日誌
    return answer, tokens_used


# 處理補充資料，從網址中提取內容
cached_data = {}
def handle_additional_info(additional_info, token_limit=None):
    urls = re.findall(r'http[s]?://\S+', additional_info)
    relevant_content = ""
    encoder = tiktoken.encoding_for_model(MODEL_NAME)

    valid_urls = []
    for url in urls[:3]:  # 限制最多處理 3 條網址
        if not re.search(r'\.(jpeg|jpg|gif|png|bmp|svg|webp|pdf|doc|docx|xls|xlsx|ppt|pptx|txt)$', url, re.I):
            valid_urls.append(url)

    if valid_urls:
        for url in valid_urls:
            if url in cached_data:
                content = cached_data[url]
                print(f"[INFO] 使用快取內容，網址 {url}")
            else:
                try:
                    scrape_result = firecrawl_app.scrape_url(url, params={'formats': ['markdown']})
                    print(f"[INFO] 抓取結果，網址 {url}: {scrape_result}")

                    # 修正：直接從 scrape_result 中獲取 metadata 和 markdown
                    status_code = scrape_result.get('metadata', {}).get('statusCode')
                    content = scrape_result.get('markdown', '')

                    if status_code == 200:
                        print(f"[INFO] 成功提取內容，網址 {url}")
                        print(f"[INFO] 狀態碼: {status_code}")
                        print(f"[INFO] 提取內容預覽: {content[:100]}...")  # 日誌顯示首100字符
                        if content:
                            # 提取元數據
                            metadata = scrape_result.get('metadata', {})
                            title = metadata.get('title', '')
                            description = metadata.get('description', '')

                            # 將元數據添加到內容中
                            content = f"標題: {title}\n描述: {description}\n\n{content}"
                            #print(f"*** Firecrawl 提取內容: {content[:500]}...")  # 只打印前500個字符

                            tokenize_content = encoder.encode(content)
                            if token_limit and len(tokenize_content) > token_limit:
                                content = encoder.decode(tokenize_content[:token_limit])
                            cached_data[url] = content
                            relevant_content += f"來源: {url}\n{content}\n\n"
                        else:
                            print(f"[INFO] 狀態碼 200 但無內容，網址 {url}")
                    else:
                        print(f"[INFO] 意外狀態碼 {status_code}，網址 {url}")
                    cached_data[url] = content  # 無論內容是否為空,都快取結果
                except Exception as e:
                    print(f"[錯誤] 抓取網址 {url} 時發生異常: {e}")
                    cached_data[url] = ""

    sanitized_additional_info = re.sub(r'\s+', ' ', additional_info).strip()


    return {
        "content": relevant_content + "\n" + sanitized_additional_info
    }

# 評估生成的答案質量
def evaluation_llm(user_question, generated_answer, original_facts, additional_info=""):
    eval_prompt = f"""問題是：{user_question}
答案是：{generated_answer}
核心事實：{original_facts}

{"用戶提供的補充資料：" + additional_info if additional_info else ""}

請嚴格地對這個答案進行全面評估，考慮以下方面：
1. 準確性 (0-10分)：評估答案的正確性，特別注意是否正確包含並強調了核心事實。
2. 全面性 (0-10分)︰評估是否有遺漏的關鍵信息或觀點或有關的延伸思考。
3. 深度 (0-10分)︰評估是否有深入的分析或只是表面的描述。
4. 相關例子 (0-10分)︰評估是否提供了合乎具體性與描述完整性相關範例。如沒有，給予0分。
5. 論證的邏輯性 (0-10分)︰評估論點之間的連貫性和推理的合理性。

評分時，請特別考慮以下幾點：
- 答案是否準確利用了相關信息？
- 如果有補充資料，答案是否完全覆蓋了這些信息？
- 答案是否提供了額外的有價值信息？

為每個方面打分，並給出簡要評論。最後，以繁體中文給出 "總評分"（滿分50分）和 "改進建議"。
請確保在評分後明確標註"總評分："，例如"總評分：42/50"。
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": eval_prompt}],
        max_tokens=800,
        temperature=0.2
    )

    evaluation = response.choices[0].message.content.strip()
    print("Evaluation response:", evaluation)

    scores = []

    total_score_match = re.search(r'總評分：\s*(\d+(?:\.\d+)?)/50', evaluation)
    if total_score_match:
        total_score = float(total_score_match.group(1))
    else:
        total_score = 0  # 確保 total_score 始終有值

    for aspect in ["準確性", "全面性", "深度", "相關例子", "論證的邏輯性"]:
        score_match = re.search(rf'{aspect}.*?(\d+)/10', evaluation)
        if score_match:
            scores.append((aspect, int(score_match.group(1))))
        else:
            scores.append((aspect, 0))  # 若無匹配則設為0

    return total_score / 50, evaluation, scores  # 返回總分（0-1範圍）、評估文本和詳細分數


def optimizer_llm(user_question, current_answer, evaluation, original_facts):
    optimize_prompt = f"""原始問題：{user_question}
當前答案：{current_answer}
評估結果：{evaluation}
核心事實：{original_facts}

請根據以上信息，生成一個新的、更優化的回答。在優化過程中，請特別注意以下幾點：

1. 仔細閱讀評估結果中的 "改進建議"，並確保在新答案中針對性地應用這些建議。
2. 保留並強化原答案中被評為優秀的部分，並且要邏輯連貫。
3. 確保新答案準確包含並強調核心事實。
4. 提供更深入、更全面的分析，包括可能的原因、影響和未來趨勢。
5. 增加相關的具體例子來支持您的論點。
6. 引用可靠的學術研究數據去支持論點，必須提供資料來源和出處。
7. 對於不確定的內容，明確表示不確定性。

請基於以上指導原則，以繁體中文生成一個新的、更優化的回答："""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": optimize_prompt}],
        max_tokens=2000,
        temperature=0.5
    )

    return format_answer(response)

def extract_core_facts(answer, question):
    prompt = f"""從以下回答中提取與問題"{question}"直接相關的核心事實：

{answer}

今天是 {CURRENT_DATE}。請列出最重要的 1-3 個核心事實，不能根據推測。若問題涉及日期或時間的概念，請確保使用有效且符合問題要求的資料來回答（例如：問題詢問 2020 年的 CPI 經濟數據，必須使用 2020 年的資料）。如答案中資料的時間與問題要求的時間範圍不符，請明確指出。如果問題涉及 2023 年 10 月前的資料，請使用你的知識庫回答；若問題涉及 2023 年 10 月後的資料，請從補充資料中提取相關內容（如有）。回答格式應為簡潔的要點列表。"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.1
    )

    return response.choices[0].message.content.strip()

def fact_check(answer, core_facts, question):
    prompt = f"""請檢查以下回答是否包含並正確陳述了這些核心事實：

核心事實：
{core_facts}

回答：
{answer}

問題：
{question}

今天是 {CURRENT_DATE}。請檢查回答的資料年份是否符合問題要求的時間範圍。如果問題涉及 2023 年 10 月前的內容，使用你的知識庫回答；若涉及 2023 年 10 月後，從補充資料中提取相關內容（如有）。如回答缺少或錯誤陳述核心事實，請直接修改並提供正確答案，不需添加評論；若回答正確無誤，則直接返回原回答。請避免在回答中包含任何檢查過程的描述或評論。"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.1
    )

    return response.choices[0].message.content.strip()


# 主循環，用於多層次優化
def main_loop(user_question, additional_info="", original_facts=""):
    logs = []
    iterations_data = []
    logs.append("\n===== 多層次 LLM (初始回答) =====")

    # 構造帶有補充資料的完整問題
    full_question = user_question
    additional_content = ""
    if additional_info:
        additional_info_processed = handle_additional_info(additional_info)
        additional_content = additional_info_processed["content"]

        full_question = f"以下是原始的補充資料，請謹慎地分析、篩選合適的資料來組織答案，留意資料中涉及的時間範圍(如有)是否與問題有關 ：\n\n{additional_content}\n\n{user_question}"

    initial_answer, initial_tokens = target_llm(full_question)
    logs.append(initial_answer)
    logs.append(f"\n<初始回答使用的 token 數>：{initial_tokens}")

    # 提取核心事實
    core_facts = original_facts if original_facts else extract_core_facts(initial_answer, user_question)

    # 評估初始回答
    initial_score, initial_evaluation, initial_scores = evaluation_llm(user_question, initial_answer, core_facts, additional_content)

    answer = initial_answer
    context = ""
    iteration_count = 0
    max_iterations = 2 # 2 = 3 次
    best_score = initial_score
    best_answer = answer
    best_scores = initial_scores
    total_tokens = initial_tokens

    logs.append(f"\n初始評分: {initial_score:.2f}")
    logs.append(f"詳細評分: {initial_scores}")
    iterations_data.append({
        'iteration': 0,
        'answer': initial_answer,
        'score': initial_score,
        'evaluation': initial_evaluation,
        'scores': initial_scores
    })

    for i in range(max_iterations):
        score, evaluation, scores = evaluation_llm(user_question, answer, core_facts, additional_content)
        logs.append(f"\n迭代 {i + 1} - 評分: {score:.2f}")
        logs.append(f"詳細評分: {scores}")
        iterations_data.append({
            'iteration': i + 1,
            'answer': answer,
            'score': score,
            'evaluation': evaluation,
            'scores': scores
        })

        if score > best_score:
            best_score = score
            best_answer = answer
            best_scores = scores
        if score > 0.9:
            break

        new_prompt = optimizer_llm(user_question, answer, evaluation, core_facts)
        context += f"\n前一次回答：{answer}\n評估：{evaluation}\n"

        # 使用已爬取的補充資料進行優化迭代
        new_full_question = f"{new_prompt}\n\n補充資料：\n{additional_content}\n核心事實：{core_facts}"
        answer, tokens = target_llm(new_full_question, context)

        # 事實檢查步驟
        answer = fact_check(answer, core_facts, user_question)

        total_tokens += tokens
        iteration_count += 1

    logs.append(f"\n===== 最終多層 LLM 回答（評分：{best_score:.2f}）=====")
    logs.append(best_answer)
    logs.append(f"\n<多層 LLM 總共使用的 token 數>：{total_tokens}")

    # 生成最終的完整答案
    final_prompt = f"""請根據以下信息生成一個完整、獨立的回答：

問題：{user_question}
核心事實：{core_facts}
優化後的回答：{best_answer}

回答應該是完整的、可以獨立閱讀的 'best_answer' 內容，包括所有細節、相關例子、邏輯論證、資料出處。請確保回答準確、全面、有學術深度。使用中英對照解釋專業名詞、人名、地方名、公司名稱等。如果內容裡包括數字、中文與英文，字與字之間要加入 (空隔) 作分隔，方便閱讀 (例如︰約翰 (John) 是一位老師, 英國國家統計局 (ONS) 為英國統計局的執行機構, 明年是 2025 年)。"""
    #但不應包含任何元描述或評論
    
    final_answer, final_tokens = target_llm(final_prompt)
    #print(f"*** main_loop *** final_answer Markdown content:\n{final_answer}")
    total_tokens += final_tokens

    # 比較初始回答和最終回答
    comparison_result = compare_answers(user_question, initial_answer, final_answer, initial_scores, best_scores)

    response_data = {
        'initial_answer': initial_answer,
        'final_answer': final_answer,
        'final_answer_markdown': final_answer,
        'initial_score': initial_score * 10,  # 轉為10分制
        'final_score': best_score * 10,  # 轉為10分制
        'initial_tokens': initial_tokens,
        'total_tokens': total_tokens,
        'logs': '\n'.join(logs),
        'comparison_result': comparison_result,
        'iterations_data': iterations_data,
        'initial_scores': initial_scores,
        'final_scores': best_scores,
        'core_facts': core_facts
    }

    return jsonify(response_data)



# 比較直接 LLM 和最終優化後 LLM 的答案
def compare_answers(user_question, direct_answer, final_answer, direct_scores, final_scores):
    comparison_prompt = f"""請對以下兩個回答進行答案的質量分析：

問題："{user_question}"

直接 LLM 回答：
{direct_answer}

最終多層次 LLM 回答：
{final_answer}

請從以下幾個方面進行分析和比較：
1. 準確性：評估兩個回答中提供的信息是否準確。檢查是否存在任何事實錯誤或誤導性陳述。
2. 全面性：分析兩個回答是否涵蓋了問題的所有重要方面。評估是否有遺漏的關鍵信息或觀點。
3. 深度：評估兩個回答在解釋概念和提供見解方面的深度。分析是否有深入的分析或只是表面的描述。
4. 相關例子 ︰評估是否提供了相關範例，並檢視範例的具體性與描述完整性。
5. 論證的邏輯性：評估兩個回答的論證結構和邏輯流程。分析論點之間的連貫性和推理的合理性。

請以 200 字內繁體中文，提供一份分析報告，突出兩個回答之間的主要差異。最後，說明推薦使用哪個答案更好。

關於 "{user_question}" 的答案分析報告：
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": comparison_prompt}],
        max_tokens=600,
        temperature=0.7
    )

    comparison_text = response.choices[0].message.content.strip()
    return comparison_text

# 定義主頁路由
@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html', MODEL_NAME=MODEL_NAME)


# 定義直接 LLM 路由
@app.route('/direct_llm', methods=['POST'])
def direct_llm_route():
    user_question = request.json.get('user_question')
    additional_info = request.json.get('additional_info', "")
    print("[INFO] Received direct_llm_route Request")
    if user_question:
        if additional_info:
            additional_content = handle_additional_info(additional_info)
            user_question_with_info = f"{user_question}\n\n補充資料：\n{additional_content}"
        else:
            user_question_with_info = user_question
        direct_answer, direct_tokens = direct_llm(user_question_with_info)

        # 提取核心事實
        original_facts = extract_core_facts(direct_answer, user_question)

        # 評估直接回答
        direct_score, _, _ = evaluation_llm(user_question, direct_answer, original_facts, additional_info)
        return jsonify(
            direct_answer=direct_answer,
            direct_tokens=direct_tokens,
            direct_score=direct_score * 10,  # 總評分轉為10分制
            original_facts=original_facts  # 添加這行，將核心事實傳遞給前端
        )
    return jsonify(error="Invalid input"), 400

# 主循環路由
@app.route('/main_loop', methods=['POST'])
def main_loop_route():
    user_question = request.json.get('user_question')
    direct_answer = request.json.get('direct_answer')
    direct_tokens = request.json.get('direct_tokens', 0)
    direct_score = request.json.get('direct_score', 0)
    additional_info = request.json.get('additional_info', "")
    original_facts = request.json.get('original_facts', "")
    print("[INFO] Received main_loop_route Request")

    if user_question and direct_answer:
        # 直接調用 main_loop 並返回其結果
        return main_loop(user_question, additional_info, original_facts)
    return jsonify(error="Invalid input"), 400

# 主程序入口
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)