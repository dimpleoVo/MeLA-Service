import os
import logging
import subprocess
import uuid
import re


# 简单的配置类
class SimpleConfig:
    def __init__(self, dictionary):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                value = SimpleConfig(value)
            setattr(self, key, value)


class ELE_Service:
    def __init__(self, task_config: dict, llm_client, base_temp_dir: str = "/tmp/mela_tasks"):
        self.cfg = SimpleConfig(task_config)
        self.llm = llm_client  # 这里就是 llm.py 里的 llm_service
        self.task_id = str(uuid.uuid4())
        logging.basicConfig(level=logging.INFO)

    def _extract_code(self, llm_response: str) -> str:
        """
        从 LLM 的回复中提取 ```python ... ``` 之间的代码
        """
        # 使用正则提取 Markdown 代码块
        match = re.search(r"```python(.*?)```", llm_response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 兜底：如果没找到 python 标签，尝试找通用代码块
        match_general = re.search(r"```(.*?)```", llm_response, re.DOTALL)
        if match_general:
            return match_general.group(1).strip()

        return llm_response.replace("```", "").strip()

    def _generate_code_with_llm(self, query: str) -> str:
        """
        让 DeepSeek 编写解决问题的 Python 代码
        """
        # 1. 定义 System Prompt (人设)
        sys_prompt = "你是一个 Python 编程专家。只返回代码，不要解释。"

        # 2. 定义 User Prompt (具体要求)
        user_prompt = f"""
        请编写一个完整的 Python 脚本来解决以下问题：
        "{query}"

        要求：
        1. 代码必须是完整的、可运行的。
        2. 必须将最终结果通过 print() 打印到控制台。
        3. 不要使用 input() 等待用户输入。
        4. 引入必要的库（如 math, random 等）。
        5. 代码必须包裹在 ```python 和 ``` 之间。
        """

        logging.info(f"🤖 Asking DeepSeek to write code for: {query}")

        #  关键调用：使用我们在 llm.py 新增的 chat 方法
        response = self.llm.chat(prompt=user_prompt, system_prompt=sys_prompt)

        return self._extract_code(response)

    def _run_code_in_docker(self, code_content: str):
        """
        流式注入代码到 Docker 容器
        """
        cmd = [
            "docker", "run", "--rm", "-i", "--network", "none",
            "--cpus", "1.0", "--memory", "512m",
            "python:3.9-slim", "python", "-"
        ]
        logging.info(f"Sandbox Execution: {' '.join(cmd)}")
        try:
            # input=code_content 是核心，直接把代码喂给 stdin
            result = subprocess.run(
                cmd, input=code_content, capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                return {"status": "success", "output": result.stdout}
            else:
                return {"status": "error", "error": result.stderr}
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "Code execution timed out"}
        except Exception as e:
            return {"status": "system_error", "error": str(e)}



    def run(self, query: str = "Solve TSP"):
            logging.info(f"Task {self.task_id} started. Query: {query}")

            # 1. 真·LLM 代码生成
            try:
                generated_code = self._generate_code_with_llm(query)
                logging.info("Code generated successfully.")
            except Exception as e:
                logging.error(f"LLM Generation failed: {e}")
                return {"status": "llm_error", "error": str(e)}

            # 2. Docker 执行
            execution_result = self._run_code_in_docker(generated_code)

            # 把生成的代码也放进结果里！
            execution_result["generated_code"] = generated_code

            logging.info(f"Task finished. Result: {execution_result}")
            return execution_result