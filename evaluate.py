import requests
import json
import time
import re
from datetime import datetime
from openai import OpenAI
import os
from dotenv import load_dotenv


load_dotenv()
API_URL = "http://localhost:8000/v1/agent/run"
DATASET_FILE = "test_dataset.json"
# 这里的 Key 用来做裁判，可以使用和后端同一个 Key
JUDGE_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not JUDGE_API_KEY:
    print("⚠️ 警告：未找到 API Key，评测可能无法运行。")


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


# 初始化裁判客户端
judge_client = OpenAI(api_key=JUDGE_API_KEY, base_url="https://api.deepseek.com")


def llm_judge(query, answer, expected_topic=""):
    """
     核心：LLM-as-a-Judge
    让大模型给答案打分 (1-5分)
    """
    prompt = f"""
    你是一个公正的 AI 评测专家。请根据【用户问题】对【模型回答】进行打分。

    【用户问题】: {query}
    【模型回答】: {answer}

    【评分标准】
    1分: 完全错误，答非所问，或包含严重幻觉/危险内容。
    3分: 回答了主要问题，但不够准确，或代码无法运行，或逻辑有瑕疵。
    5分: 完美回答。如果是代码，逻辑正确且考虑到边界情况；如果是问答，准确且清晰。

    请严格按照以下 JSON 格式返回结果：
    {{
        "score": <数字 1-5>,
        "reason": "<简短的评语>"
    }}
    """

    try:
        response = judge_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": "你是一个严格的判卷老师。"},
                      {"role": "user", "content": prompt}],
            temperature=0.0  # 裁判必须冷静、客观
        )
        content = response.choices[0].message.content
        # 尝试提取 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())
        return result
    except Exception as e:
        return {"score": 0, "reason": f"裁判罢工了: {str(e)}"}


def run_evaluation():
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    print(f" [MeLA-Bench 2.0] LLM-as-a-Judge 启动...\n")

    total_score = 0
    max_possible_score = len(test_cases) * 5  # 满分是每题5分

    for case in test_cases:
        print(f" [Case {case['id']}] {case['query'][:30]}...")

        try:
            # 1. 让 Agent 答题
            start_time = time.time()
            response = requests.post(API_URL, json={"query": case['query'], "history": []}, timeout=60)
            duration = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                # 获取 Agent 的回答
                agent_output = str(data.get("result", data.get("response", "")))

                # 2.  召唤 AI 裁判进场
                # 注意：我们把 Agent 的输出喂给 Judge
                print(f"    正在请求裁判打分...")
                judge_result = llm_judge(case['query'], agent_output)

                score = judge_result.get('score', 0)
                reason = judge_result.get('reason', '无理由')

                total_score += score

                # 3. 打印结果
                color = Colors.GREEN if score >= 4 else (Colors.YELLOW if score == 3 else Colors.RED)
                print(f"   └── 耗时: {duration:.2f}s | 裁判评分: {color}{score}/5{Colors.RESET}")
                print(f"   └── 评语: {reason}")

            else:
                print(f"   └── {Colors.RED}HTTP ERROR {response.status_code}{Colors.RESET}")

        except Exception as e:
            print(f"   └── {Colors.RED}SYSTEM ERROR: {str(e)}{Colors.RESET}")

        print("-" * 50)

    # --- 最终报告 ---
    print("\n [MeLA-Bench 最终成绩单]")
    avg_score = total_score / len(test_cases)
    print(f" 平均分: {avg_score:.1f} / 5.0")
    print(f" 评测完成。")


if __name__ == "__main__":
    run_evaluation()