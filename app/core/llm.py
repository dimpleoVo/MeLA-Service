import logging
from typing import List
import os
from openai import OpenAI

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLM_Engine:
    def __init__(self):
        """
        初始化 DeepSeek 客户端
        """
        # =====================================================
        #  请在这里填入你的 DeepSeek API Key
        # =====================================================
        self.api_key = "your-key"

        if "填入" in self.api_key:
            logger.warning(" 警告：你还没有填入真实的 DeepSeek API Key！")

        # 初始化客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"  # 关键点：指向 DeepSeek 的服务器
        )

        logger.info("DeepSeek LLM Engine initialized.")

    def _construct_messages(self, query: str, context_chunks: List[str]) -> List[dict]:
        """
        构建符合 Chat 格式的消息列表 (Messages Array)
        """
        # 1. 拼接上下文
        context_str = "\n".join([f"- {chunk}" for chunk in context_chunks])

        # 2. System Message (系统人设)
        system_prompt = f"""
你是一个专业的 Fintech 金融风控专家，服务于 Lumos Flow 平台。
你的任务是根据提供的【上下文信息】回答【用户问题】。

【回答原则】
1. 必须基于<context>内的信息回答，不要编造事实。
2. 如果上下文中没有答案，请明确告知“知识库中未找到相关信息”。
3. 保持专业、客观、简洁的语气。

<context>
{context_str}
</context>
"""
        # 3. 返回消息列表
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

    def generate(self, query: str, context_chunks: List[str]) -> str:
        """
        调用 DeepSeek 生成回答
        """
        try:
            # 1. 准备 Prompt
            messages = self._construct_messages(query, context_chunks)

            logger.info(f"Sending request to DeepSeek... Query: {query}")

            # 2. 发起 API 请求 (真调用)
            response = self.client.chat.completions.create(
                model="deepseek-chat",  # DeepSeek 的模型名
                messages=messages,
                temperature=0.1,  # 0.1 意味着非常严谨，不做发散 (RAG 标配)
                max_tokens=500,  # 限制回答长度
                stream=False  # 暂时不用流式，简化开发
            )

            # 3. 解析结果
            answer = response.choices[0].message.content
            logger.info("Received response from DeepSeek.")

            return answer

        except Exception as e:
            logger.error(f"DeepSeek API Error: {e}")
            return f"抱歉，调用 AI 模型时出现错误: {str(e)}"


# 单例模式
llm_service = LLM_Engine()