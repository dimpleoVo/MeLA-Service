import logging
from typing import Dict, Any, List
from app.core.llm import llm_service
from app.core.rag import rag_service
from app.core.engine import ELE_Service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentState:
    def __init__(self, query: str, history: List[Dict]):
        self.query = query
        self.history = history  #  存储历史
        self.final_answer = ""


class MeLA_Workflow:
    def __init__(self):
        logger.info("Initializing Agent Workflow...")

    def router_node(self, state: AgentState) -> str:
        # 路由时也可以带上 history，但为了省 token，通常只看最新 query
        # 或者简化为只看 query
        intent = llm_service.chat(
            prompt=f"用户输入: '{state.query}'\n请判断意图：如果涉及写代码/数学/优化/TSP，返回'OPTIMIZE'。如果是闲聊/概念解释，返回'CHAT'。只返回单词。",
            system_prompt="你是一个意图分类器。"
        )
        if "OPTIMIZE" in intent.upper():
            return "node_optimizer"
        else:
            return "node_chat"

    def optimizer_node(self, state: AgentState):
        """
        【工具节点】调用 ELE 引擎执行优化任务
        """
        logger.info(" Agent is using Tool: Optimization Engine...")

        # 1. 初始化优化引擎
        task_config = {"problem": {"problem_name": "User_Task"}, "max_fe": 10}
        ele = ELE_Service(task_config, llm_client=llm_service)

        # 2. 执行任务
        result = ele.run(query=state.query)

        # 3. 更新状态
        if result['status'] == 'success':
            #展示代码和运行结果
            code_block = f"###  生成的代码\n```python\n{result.get('generated_code', '# No code')}\n```"
            output_block = f"###  运行结果\n{result['output']}"
            state.final_answer = f"{code_block}\n\n{output_block}"
        else:
            state.final_answer = f"执行出错: {result.get('error')}"

        return state

    def chat_node(self, state: AgentState):
        logger.info("💬 Tool: RAG Chat...")
        # 简单 RAG：先不带 History 检索，但带 History 生成
        search_res = rag_service.search(state.query)
        docs = search_res["results"]

        context_str = "\n".join(docs)
        sys_prompt = f"你是一个知识助手。结合上下文回答。\n知识库上下文:\n{context_str}"

        #  这里把 history 传进去！
        answer = llm_service.chat(prompt=state.query, system_prompt=sys_prompt, history=state.history)
        state.final_answer = answer
        return state

    def run(self, query: str, history: List[Dict] = []):
        state = AgentState(query, history)
        next_step = self.router_node(state)

        if next_step == "node_optimizer":
            self.optimizer_node(state)
        elif next_step == "node_chat":
            self.chat_node(state)

        return state.final_answer


agent_workflow = MeLA_Workflow()