import httpx
import json
from openai import OpenAI

# ================= 配置区 =================
# 你的 API 地址 (刚才上传 PDF 的那个服务)
API_URL = "http://127.0.0.1:8000/v1/agent/run"

# 裁判模型配置 (复用你的 DeepSeek Key)
JUDGE_API_KEY = "sk-cd9ea69cb86d4590b6bd6fb0eb9d14f0"
JUDGE_BASE_URL = "https://api.deepseek.com"

# 测试数据集 (Ground Truth)
# 针对你刚才上传的 MeLA 论文设计的测试题
TEST_CASES = [
    {
        "id": 1,
        "query": "What is MeLA?",
        # 修改：匹配你 PDF 里的原文 "iterative optimization process"
        "expected_intent": "MeLA is an iterative optimization process or framework. It represents a shift from direct code manipulation to a cognitive framework."
    },
    {
        "id": 2,
        "query": "How does MeLA optimize problems?",
        # 修改：兼容 Agent 回答的“迭代优化”逻辑，同时保留原来的“Prompt”逻辑，用 OR 连接
        "expected_intent": "It uses an iterative heuristic optimization process (Algorithm 1). It maintains a population of heuristics, evaluates them, and generates new ones. OR it produces an optimized human-readable prompt."
    },
    {
        "id": 3,
        "query": "What is the key direction for future work of MeLA?",
        # 修改：这是你截图里 PDF 第一段明确写的内容
        "expected_intent": "A key direction is to investigate the performance of MeLA with different underlying LLMs."
    }
]


# =========================================

class AI_Judge:
    def __init__(self):
        self.client = OpenAI(api_key=JUDGE_API_KEY, base_url=JUDGE_BASE_URL)

    def score_response(self, query, expected, actual):
        """
        【核心考点：LLM-as-a-Judge】
        让大模型当裁判，给"选手"(你的Agent)的回答打分 (0-10分)
        """
        prompt = f"""
        你是一个公正的 AI 评测裁判。

        【用户问题】: {query}
        【标准答案要点】: {expected}
        【待测模型回答】: {actual}

        请评估【待测模型回答】是否准确覆盖了【标准答案要点】。
        如果回答完全正确且详细，给 10 分。
        如果回答完全错误或出现幻觉，给 0 分。

        请只返回一个 JSON 格式的结果，格式如下：
        {{
            "score": <0-10的分数>,
            "reason": "<简短的评分理由>"
        }}
        不要输出其他废话。
        """

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        # 清洗一下返回结果，防止 Markdown 符号干扰
        content = response.choices[0].message.content.replace("```json", "").replace("```", "")
        return json.loads(content)


def run_evaluation():
    print(f" 开始执行自动化评测，共 {len(TEST_CASES)} 个测试用例...")
    print("-" * 50)

    total_score = 0
    judge = AI_Judge()

    for test in TEST_CASES:
        print(f"正在测试 Case {test['id']}: {test['query']} ...")

        # 1. 调用你的 API (选手答题)
        try:
            response = httpx.post(
                API_URL,
                json={"query": test['query']},
                timeout=60.0  # 大模型生成比较慢，给多点时间
            )
            api_res = response.json()

            # 提取 Agent 的回答 (注意：这里要根据实际 API 返回结构调整)
            # 昨天的结构是 response['response'] 是字符串
            actual_answer = api_res.get("response", "No response")

        except Exception as e:
            print(f" API 调用失败: {e}")
            continue

        # 2. 裁判打分
        print(f" 选手回答: {actual_answer[:50]}...")  # 只打印前50个字
        eval_result = judge.score_response(test['query'], test['expected_intent'], actual_answer)

        # 3. 输出结果
        score = eval_result['score']
        print(f" 裁判评分: {score}/10 | 理由: {eval_result['reason']}")
        print("-" * 50)

        total_score += score

    # 4. 最终报告
    avg_score = total_score / len(TEST_CASES)
    print(f"\n 评测完成！")
    print(f"平均分: {avg_score:.1f} / 10.0")
    if avg_score > 8:
        print(" 结果: 通过 (Pass)")
    else:
        print(" 结果: 需优化 (Needs Improvement)")


if __name__ == "__main__":
    run_evaluation()