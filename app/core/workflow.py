import logging
from typing import Dict, Any
from app.core.llm import llm_service
from app.core.rag import rag_service
# 引入我们在 Module 1 写的引擎 (为了调用 run 方法)
from app.core.engine import ELE_Service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentState:
    """
    用于在不同步骤之间传递数据的"黑板"
    """

    def __init__(self, query: str):
        self.query = query
        self.memory = []  # 所有的对话历史
        self.current_step = "start"
        self.final_answer = ""


class MeLA_Workflow:
    def __init__(self):
        logger.info("Initializing Agent Workflow...")

    def router_node(self, state: AgentState) -> str:
        """
        【路由节点】
        判断用户的意图：是想聊天(Chat)？还是想优化代码(Optimize)？
        """
        logger.info(" Agent is thinking (Routing)...")

        # 使用 DeepSeek 进行意图识别
        prompt = f"""
        用户输入: "{state.query}"
        请判断用户意图。
        - 如果用户想解决数学优化问题、写代码、求解TSP/背包问题，返回 "OPTIMIZE"。
        - 如果用户只是询问知识、定义概念或闲聊，返回 "CHAT"。
        只返回单词，不要标点。
        """
        # 这里为了演示简单，直接调 generate。生产环境会用 Function Calling。
        intent = llm_service.generate(prompt, context_chunks=[])

        if "OPTIMIZE" in intent.upper():
            return "node_optimizer"
        else:
            return "node_chat"

    def optimizer_node(self, state: AgentState):
        """
        【工具节点】调用 ELE 引擎执行优化任务
        """
        logger.info(" Agent is using Tool: Optimization Engine...")

        # 1. 初始化优化引擎 (这里为了演示简化了配置)
        task_config = {"problem": {"problem_name": "User_Task"}, "max_fe": 10}
        ele = ELE_Service(task_config, llm_client=llm_service)

        # 2. 执行任务 (Module 1 的核心逻辑)
        # 这里会触发 Docker/Mock
        result = ele.run()

        # 3. 更新状态
        state.final_answer = f" 优化任务已完成。\n引擎运行结果: {result['output']}"
        return state

    def chat_node(self, state: AgentState):
        """
        【对话节点】调用 RAG + LLM 回答问题
        """
        logger.info("💬 Agent is chatting (RAG Mode)...")

        # 1. RAG 检索
        search_res = rag_service.search(state.query)
        docs = search_res["results"]

        # 2. LLM 生成
        answer = llm_service.generate(state.query, context_chunks=docs)

        state.final_answer = answer
        return state

    def run(self, query: str):
        """
        【图执行引擎】模拟 LangGraph 的运行逻辑
        Start -> Router -> (Optimizer / Chat) -> End
        """
        state = AgentState(query)

        # 1. 路由阶段
        next_step = self.router_node(state)

        # 2. 执行阶段
        if next_step == "node_optimizer":
            self.optimizer_node(state)
        elif next_step == "node_chat":
            self.chat_node(state)

        return state.final_answer


# 单例
agent_workflow = MeLA_Workflow()