document.addEventListener('DOMContentLoaded', function() {
    
    const form = document.getElementById('llmForm');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const submitButton = document.querySelector('button[type="submit"]');
    const progressInfo = document.getElementById('progressInfo');
    const additionalInfoInput = document.getElementById('additional_info');
    const additionalInfoLabel = document.querySelector('label[for="additional_info"]');

    let originalMarkdown = ''; // 用於存儲原始 Markdown
    // 在接收到最終答案時保存原始 Markdown
    function saveFinalAnswerMarkdown(markdown) {
        originalMarkdown = markdown;
    }
    
    document.getElementById('copyFinalAnswer').addEventListener('click', function() {
        navigator.clipboard.writeText(originalMarkdown).then(function() {
            const button = document.getElementById('copyFinalAnswer');
            button.classList.add('btn-success');
            button.textContent = '已複製';

            setTimeout(() => {
                button.classList.remove('btn-success');
                button.textContent = '複製答案';
            }, 2000); // 2秒後恢復原狀
        }, function(err) {
            console.error('無法複製文本: ', err);
        });
    });

    function validateUrls(input) {
        const urlRegex = /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/;
        const unsupportedFormatRegex = /\.(jpeg|jpg|gif|png|bmp|svg|webp|pdf|doc|docx|xls|xlsx|ppt|pptx|txt)$/i;

        let urls = input.match(/https?:\/\/[^\s]+/g) || [];
        let validUrls = [];
        let invalidUrls = [];

        for (let url of urls) {
            if (urlRegex.test(url) && !unsupportedFormatRegex.test(url)) {
                validUrls.push(url);
            } else {
                invalidUrls.push(url);
            }
        }

        return { validUrls, invalidUrls };
    }
    
    additionalInfoInput.addEventListener('input', function() {
        const { validUrls, invalidUrls } = validateUrls(this.value);

        if (invalidUrls.length > 0) {
            alert('以下 URL 格式不支援或為圖片/文檔：\n' + invalidUrls.join('\n') + '\n請修正或刪除這些 URL。');
            this.value = validUrls.join('\n');
        }

        if (validUrls.length > 3) {
            alert('最多只能輸入 3 個 URL。超出的部分將被刪除。');
            this.value = validUrls.slice(0, 3).join('\n');
        }
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        // 添加表單驗證
        if (!form.checkValidity()) {
            e.stopPropagation();
            form.classList.add('was-validated');
            return;  // 如果表單無效，停止處理
        }
        loadingIndicator.style.display = 'block';
        submitButton.disabled = true;
        progressInfo.textContent = '正在處理您的請求...';

        const userQuestion = document.getElementById('user_question').value;
        const additionalInfo = additionalInfoInput.value;

        document.getElementById('userQuestionDisplay').innerText = userQuestion;

        clearPreviousResults();

        // 首先發送直接 LLM 請求
        fetch('/direct_llm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_question: userQuestion, additional_info: additionalInfo })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            progressInfo.textContent = '直接 LLM 回答已生成，正在評估...';
            return response.json();
        })
        .then(data => {
            console.log('Direct LLM response:', data);
            if (data.direct_answer) {
                document.getElementById('directAnswerContent').innerText = data.direct_answer;
                document.getElementById('directTokens').innerText = data.direct_tokens;
                document.getElementById('directScore').innerText = data.direct_score.toFixed(2);
                document.getElementById('directAnswerSection').style.display = 'block';

                // 填充核心事實
                const coreFactsList = document.getElementById('coreFactsList');
                coreFactsList.innerHTML = ''; // 清空現有內容
                data.original_facts.split('\n').forEach(fact => {
                    const li = document.createElement('li');
                    li.className = 'list-group-item';
                    li.textContent = fact;
                    coreFactsList.appendChild(li);
                });

                // 如果成功提取內容，添加成功圖示
                if (!additionalInfoLabel.textContent.includes('✅')) {
                    additionalInfoLabel.textContent += ' ✅';
                }

                // 然後發送 main_loop 請求
                progressInfo.textContent = '開始迭代優化...';
                return fetch('/main_loop', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        user_question: userQuestion, 
                        direct_answer: data.direct_answer, 
                        direct_tokens: data.direct_tokens, 
                        direct_score: data.direct_score, 
                        additional_info: additionalInfo,
                        original_facts: data.original_facts
                    })
                });
            } else {
                throw new Error('No direct answer received');
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            progressInfo.textContent = '迭代優化完成，正在生成最終答案...';
            return response.json();
        })
        .then(data => {
            console.log('Main loop response:', data);
            saveFinalAnswerMarkdown(data.final_answer_markdown);
            if (data.final_answer) {
                document.getElementById('finalAnswerContent').innerText = data.final_answer;
                document.getElementById('finalTokens').innerText = data.total_tokens || 'N/A';
                document.getElementById('finalScore').innerText = (data.final_score || 0).toFixed(2);
                document.getElementById('finalAnswerSection').style.display = 'block';
            }
            if (data.comparison_result) {
                const comparisonResultContent = document.getElementById('comparisonResultContent');
                comparisonResultContent.innerHTML = '';  // 清空現有內容
                const resultParagraph = document.createElement('p');
                resultParagraph.textContent = data.comparison_result;
                comparisonResultContent.appendChild(resultParagraph);

                updateComparisonTable(data.initial_scores || [], data.final_scores || []);
                document.getElementById('comparisonResultSection').style.display = 'block';
            }
            if (data.iterations_data && Array.isArray(data.iterations_data)) {
                drawChart(data.initial_score || 0, data.iterations_data);
                document.getElementById('chartSection').style.display = 'block';
            } else {
                console.error('Invalid or missing iterations_data:', data.iterations_data);
            }
            progressInfo.textContent = '處理完成，顯示結果中...';
            renderAllMarkdown();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('發生錯誤：' + error.message);
        })
        .finally(() => {
            loadingIndicator.style.display = 'none';
            submitButton.disabled = false;
        });
    });

    function clearPreviousResults() {
        document.getElementById('directAnswerContent').innerText = '';
        document.getElementById('finalAnswerContent').innerText = '';
        document.getElementById('comparisonResultContent').innerText = '';
        document.getElementById('coreFactsList').innerHTML = '';

        document.getElementById('directAnswerSection').style.display = 'none';
        document.getElementById('finalAnswerSection').style.display = 'none';
        document.getElementById('comparisonResultSection').style.display = 'none';
        document.getElementById('chartSection').style.display = 'none'; 
    }

    function updateComparisonTable(initialScores, finalScores) {
        const table = document.getElementById('comparisonTable');
        table.innerHTML = '';

        const aspects = ['準確性', '全面性', '深度', '相關例子', '論證的邏輯性'];
        aspects.forEach((aspect, index) => {
            const row = table.insertRow();
            row.insertCell(0).textContent = aspect;
            row.insertCell(1).textContent = initialScores[index]?.[1] || 'N/A';
            row.insertCell(2).textContent = finalScores[index]?.[1] || 'N/A';
        });

        const totalRow = table.insertRow();
        totalRow.insertCell(0).textContent = '總分(/50)';
        totalRow.insertCell(1).textContent = initialScores.reduce((sum, score) => sum + (score[1] || 0), 0);
        totalRow.insertCell(2).textContent = finalScores.reduce((sum, score) => sum + (score[1] || 0), 0);
    }

    function drawChart(initialScore, iterationsData) {
        try {
            if (!iterationsData || iterationsData.length === 0) {
                console.error('No iteration data available');
                return;
            }

            const labels = ['Initial', ...iterationsData.map(d => `Iteration ${d.iteration}`)];
            const scores = [initialScore, ...iterationsData.map(d => (d.score || 0) * 10)];

            const getScoreOrDefault = (data, key) => data.scores?.find(s => s[0] === key)?.[1] || NaN;

            const accuracyScores = [NaN, ...iterationsData.map(d => getScoreOrDefault(d, '準確性'))];
            const completenessScores = [NaN, ...iterationsData.map(d => getScoreOrDefault(d, '全面性'))];
            const depthScores = [NaN, ...iterationsData.map(d => getScoreOrDefault(d, '深度'))];
            const exampleScores = [NaN, ...iterationsData.map(d => getScoreOrDefault(d, '相關例子'))];
            const logicScores = [NaN, ...iterationsData.map(d => getScoreOrDefault(d, '論證的邏輯性'))];

            const ctx = document.getElementById('iterationChart').getContext('2d');
            if (window.iterationChart instanceof Chart) {
                window.iterationChart.destroy();
            }
            window.iterationChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: '總分 (Score)',
                            data: scores,
                            type: 'line',
                            borderColor: 'blue',
                            fill: false,
                            yAxisID: 'y-axis-1'
                        },
                        {
                            label: '準確性 (Accuracy)',
                            data: accuracyScores,
                            backgroundColor: 'rgba(255, 99, 132, 0.2)',
                            borderColor: 'rgba(255, 99, 132, 1)',
                            borderWidth: 1,
                            yAxisID: 'y-axis-2'
                        },
                        {
                            label: '全面性 (Completeness)',
                            data: completenessScores,
                            backgroundColor: 'rgba(54, 162, 235, 0.2)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1,
                            yAxisID: 'y-axis-2'
                        },
                        {
                            label: '深度 (Depth)',
                            data: depthScores,
                            backgroundColor: 'rgba(255, 206, 86, 0.2)',
                            borderColor: 'rgba(255, 206, 86, 1)',
                            borderWidth: 1,
                            yAxisID: 'y-axis-2'
                        },
                        {
                            label: '相關例子 (Examples)',
                            data: exampleScores,
                            backgroundColor: 'rgba(75, 192, 192, 0.2)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 1,
                            yAxisID: 'y-axis-2'
                        },
                        {
                            label: '論證的邏輯性 (Logic)',
                            data: logicScores,
                            backgroundColor: 'rgba(153, 102, 255, 0.2)',
                            borderColor: 'rgba(153, 102, 255, 1)',
                            borderWidth: 1,
                            yAxisID: 'y-axis-2'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        'y-axis-1': {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            beginAtZero: true,
                            max: 10,
                            title: {
                                display: true,
                                text: '總分'
                            }
                        },
                        'y-axis-2': {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            beginAtZero: true,
                            max: 10,
                            title: {
                                display: true,
                                text: '各項評分'
                            },
                            grid: {
                                drawOnChartArea: false
                            }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error in drawChart:', error);
            const chartError = document.createElement('div');
            chartError.className = 'alert alert-danger mt-2';
            chartError.textContent = `圖表繪製錯誤：${error.message}`;
            document.getElementById('chartSection').appendChild(chartError);
        }
    }

    // Markdown 渲染
    const markdown = window.markdownit({
      breaks: true,
      html: true
    });

    function renderMarkdown(elementId) {
      const element = document.getElementById(elementId);
      if (element) {
        const text = element.innerText;
        let html = markdown.render(text);

        // 處理數字後跟隨粗體的情況
        html = html.replace(/<li>\s*(\d+\.)\s*<strong>/g, '<li><strong>$1 ');
        html = html.replace(/<p>/g, '<p style="margin-bottom: 0.7em;">');
        html = html.replace(/<li>/g, '<li style="margin-bottom: 0.3em;">');
          
        element.innerHTML = html;
      }
    }

    function optimizeContentLayout(elementId) {
      const element = document.getElementById(elementId);
      if (element) {
        // 移除多餘的空行
        element.innerHTML = element.innerHTML.replace(/(<br\s*\/?>){3,}/gi, '<br><br>');

        // 優化有序列表的間距
        const orderedLists = element.querySelectorAll('ol');
        orderedLists.forEach(list => {
          const items = list.querySelectorAll('li');
          items.forEach(item => {
            item.style.marginBottom = '0.3em';
            item.style.paddingLeft = '0.5em';
          });
        });
      }
    }

    // 在結果顯示後調用 Markdown 渲染
    function renderAllMarkdown() {
        renderMarkdown("directAnswerContent");
        renderMarkdown("finalAnswerContent");
        renderMarkdown("comparisonResultContent");

        

       /*  // 特別處理比較結果內容
        const comparisonResultContent = document.getElementById("comparisonResultContent");
        if (comparisonResultContent) {
            const text = comparisonResultContent.innerText;
            comparisonResultContent.innerHTML = markdown.render(text);
        } */

        // 應用優化佈局
        optimizeContentLayout("directAnswerContent");
        optimizeContentLayout("finalAnswerContent");
        optimizeContentLayout("comparisonResultContent");
    }
});

// 額外的 URL 驗證函數
function validateUrls(input) {
    const urlRegex = /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/;
    const imageRegex = /\.(jpeg|jpg|gif|png|bmp|svg|webp)$/i;
    const documentRegex = /\.(pdf|doc|docx|xls|xlsx|ppt|pptx|txt)$/i;

    let urls = input.match(/https?:\/\/[^\s]+/g) || [];
    let validUrls = [];

    for (let url of urls) {
        if (urlRegex.test(url) && !imageRegex.test(url) && !documentRegex.test(url)) {
            validUrls.push(url);
            if (validUrls.length === 3) break;
        }
    }

    return validUrls.join('\n');
}

document.getElementById('additionalInfo').addEventListener('change', function() {
    this.value = validateUrls(this.value);
});