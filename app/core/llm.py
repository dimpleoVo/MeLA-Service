import logging
from typing import List, Optional, Dict
import os
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLM_Engine:
    def __init__(self):
        #  修改点：不再写死 Key，而是从环境变量获取
        self.api_key = os.getenv("DEEPSEEK_API_KEY")

        if not self.api_key:
            # 如果没读到，抛出错误提示用户去配置 .env
            raise ValueError(" 未找到 API Key！请在 .env 文件中配置 DEEPSEEK_API_KEY。")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )

    # ---  修改点：增加 history 参数 ---
    def chat(self, prompt: str, system_prompt: str = "你是一个有用的助手。", history: List[Dict] = []) -> str:
        """
        通用对话接口，支持历史记忆
        """
        try:
            # 1. 构造消息链：System -> History -> Current User Query
            messages = [{"role": "system", "content": system_prompt}]

            # 2. 追加历史 (过滤掉出错的或格式不对的)
            for msg in history:
                if msg.get("role") in ["user", "assistant"] and msg.get("content"):
                    messages.append({"role": msg["role"], "content": str(msg["content"])})

            # 3. 追加当前问题
            messages.append({"role": "user", "content": prompt})

            logger.info(f"Sending request with history ({len(history)} msgs)...")

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.1,
                stream=False
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"DeepSeek Chat Error: {e}")
            return f"Error: {str(e)}"

    # RAG 用的 generate 方法简单保留即可，暂时不加 History 以免混淆 Context
    def generate(self, query: str, context_chunks: List[str]) -> str:
        context_str = "\n".join([f"- {chunk}" for chunk in context_chunks])
        sys_prompt = f"你是一个助手。根据上下文回答。\n上下文:\n{context_str}"
        return self.chat(query, system_prompt=sys_prompt)


llm_service = LLM_Engine()