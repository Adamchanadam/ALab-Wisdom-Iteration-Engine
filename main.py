from flask import Flask, render_template, request, jsonify, send_file
from openai import OpenAI
import os
import re
import tiktoken
import datetime
from replit.object_storage import Client  # 引入 Replit Object Storage
# 設置 Flask 應用程序
app = Flask(__name__)
# 初始化 OpenAI 客戶端
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# 初始化 Replit Object Storage 客戶端
storage_client = Client()
# 設置模型名稱
MODEL_NAME = "gpt-4o-mini-2024-07-18"
COMPARISON_MODEL_NAME = "gpt-4o-mini-2024-07-18"
# 記錄搜索日志
def log_search(user_question, model_name, direct_tokens, final_tokens, best_score):
    log_entry = (
        f"Date: {datetime.datetime.now()}\n"
        f"User Question: {user_question}\n"
        f"Model Used: {model_name}\n"
        f"Direct LLM Tokens: {direct_tokens}\n"
        f"Final Optimized LLM Tokens: {final_tokens}\n"
        f"Best Score: {best_score:.2f}\n"
        "----------------------------------------\n"
    )
    log_filename = "adam-llm-iteration.log"  # system log
    # 上傳日誌到 Object Storage
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
def target_llm(prompt, context=""):
    full_prompt = f"{context}\n\n根據以下問題生成答案：{prompt}"
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": full_prompt}
        ],
        max_tokens=2000,  # 增加 token 上限到 2000
        temperature=0.5
    )
    answer = format_answer(response)
    tokens_used = response.usage.total_tokens
    return answer, tokens_used

# 直接使用 LLM 生成答案
def direct_llm(prompt):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": f"根據以下問題生成答案：{prompt}"}
        ],
        max_tokens=2000,
        temperature=0.7
    )
    answer = format_answer(response)
    tokens_used = response.usage.total_tokens
    return answer, tokens_used

# 評估生成的答案質量
def evaluation_llm(user_question, generated_answer):
    eval_prompt = f"""問題是：{user_question}
答案是：{generated_answer}

請對這個答案進行全面評估，考慮以下方面：
1. 準確性 (0-10分)
2. 全面性 (0-10分)
3. 深度 (0-10分)
4. 相關例子的使用 (0-10分)
5. 論證的邏輯性 (0-10分)

為每個方面打分，並給出簡要評論。最後，給出總評分（滿分50分）和改進建議。
請確保在評分後明確標註"總評分："，例如"總評分：42/50"。"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": eval_prompt}
        ],
        max_tokens=1000,
        temperature=0.3
    )

    evaluation = response.choices[0].message.content.strip()

    total_score_match = re.search(r'總評分：\s*(\d+(?:\.\d+)?)/50', evaluation)
    if total_score_match:
        total_score = float(total_score_match.group(1))
    else:
        scores = []
        for aspect in ["準確性", "全面性", "深度", "相關例子", "論證的邏輯性"]:
            score_match = re.search(rf'{aspect}\s*\((\d+)/10\)', evaluation)
            if score_match:
                scores.append(int(score_match.group(1)))

        if scores:
            total_score = sum(scores)
        else:
            print("警告：無法提取評分，返回默認分數 0")
            total_score = 0

    return total_score / 50, evaluation

# 根據評估結果優化答案
def optimizer_llm(user_question, current_answer, evaluation):
    optimize_prompt = f"""原始問題：{user_question}
當前答案：{current_answer}
評估結果：{evaluation}

根據以上信息，請生成一個新的提示，以改進答案的質量。新提示應該：
1. 針對評估中指出的不足之處
2. 保留原答案中的優點
3. 鼓勵更深入、更全面的回答
4. 要求提供更多相關的具體例子
5. 引用學術研究數據去支持論點(要有出處)
6. 如涉及專業名詞、人名、地方名、公司名稱等，要使用中英對照

請生成新的提示："""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": optimize_prompt}
        ],
        max_tokens=500,
        temperature=0.7
    )

    return format_answer(response)

# 主循環，用於多層次優化
def main_loop(user_question):
    logs = []

    logs.append("\n===== 多層次 LLM (初始回答) =====")
    initial_answer, initial_tokens = target_llm(user_question)
    logs.append(initial_answer)
    logs.append(f"\n<初始回答使用的 token 數>：{initial_tokens}")

    answer = initial_answer
    context = ""
    iteration_count = 0
    max_iterations = 3
    best_score = 0
    best_answer = answer
    total_tokens = initial_tokens

    for i in range(max_iterations):
        score, evaluation = evaluation_llm(user_question, answer)
        logs.append(f"\n迭代 {i+1} - 評分: {score:.2f}")

        if score > best_score:
            best_score = score
            best_answer = answer

        if score > 0.9:
            break

        new_prompt = optimizer_llm(user_question, answer, evaluation)
        context += f"\n前一次回答：{answer}\n評估：{evaluation}\n"
        answer, tokens = target_llm(new_prompt, context)  # 使用新的 token 上限
        total_tokens += tokens
        iteration_count += 1

    logs.append(f"\n===== 最終多層 LLM 回答（評分：{best_score:.2f}）=====")
    logs.append(best_answer)
    logs.append(f"\n<多層 LLM 總共使用的 token 數>：{total_tokens}")
    return best_answer, total_tokens, logs , best_score

# 比較直接 LLM 和最終優化後 LLM 的答案
def compare_answers(user_question, direct_answer, final_answer):
    comparison_prompt = f"""
    請比較以下兩個針對使用者問題「{user_question}」的答案：

    直接 LLM 回答:
    {direct_answer}

    多層次 LLM 回答:
    {final_answer}

    請從質量、全面性和準確性三方面就兩者評分，最低 0 分 ， 最高 10 分，你會推薦使用哪組答案並以 100 字內講出出原因。
    """

    response = client.chat.completions.create(
        model=COMPARISON_MODEL_NAME,
        messages=[
            {"role": "user", "content": comparison_prompt}
        ],
        max_tokens=500,
        temperature=0.6
    )

    comparison_result = format_answer(response)
    return comparison_result

# 定義主頁路由
@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html', MODEL_NAME=MODEL_NAME)

# 定義直接 LLM 路由
@app.route('/direct_llm', methods=['POST'])
def direct_llm_route():
    user_question = request.json.get('user_question')
    if user_question:
        direct_answer, direct_tokens = direct_llm(user_question)
        return jsonify(direct_answer=direct_answer, direct_tokens=direct_tokens)
    return jsonify(error="Invalid input"), 400

# 定義主循環路由
@app.route('/main_loop', methods=['POST'])
def main_loop_route():
    user_question = request.json.get('user_question')
    direct_answer = request.json.get('direct_answer')
    direct_tokens = request.json.get('direct_tokens', 0)
    if user_question and direct_answer:
        final_answer, total_tokens, logs, best_score = main_loop(user_question)
        comparison_result = compare_answers(user_question, direct_answer, final_answer)
        # 記錄日誌
        log_search(user_question, MODEL_NAME, direct_tokens, total_tokens, best_score)
        return jsonify(final_answer=final_answer, total_tokens=total_tokens,
                       logs='\n'.join(logs), comparison_result=comparison_result)
    return jsonify(error="Invalid input"), 400

# 主程序入口
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)