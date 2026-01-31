import streamlit as st
import requests
import json

# 设置页面标题和图标
st.set_page_config(page_title="MeLA AI Agent", page_icon="🤖")

st.title(" MeLA-Service AI 助手")
st.caption("基于 DeepSeek + Docker 沙箱的智能 Agent")

# 初始化聊天记录 (让它有记忆的假象，虽然后端暂时还是无状态的)
if "messages" not in st.session_state:
    st.session_state.messages = []

# 1. 展示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 2. 处理用户输入
if prompt := st.chat_input("请输入你的问题（例如：求解TSP问题 / 什么是大模型）..."):
    # 显示用户的问题
    with st.chat_message("user"):
        st.markdown(prompt)
    # 记录到历史
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 3. 调用后端 API
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown(" Agent 正在思考中... (如果是复杂代码任务可能需要几十秒)")

        try:
            # 发送请求给你的 FastAPI 后端
            payload = {
                "query": prompt,
                "history": st.session_state.messages[:-1]  # 发送除了当前这一句之外的所有历史
            }

            response = requests.post(
                "http://localhost:8000/v1/agent/run",
                json=payload,  # 使用新的 payload
                timeout=120
            )

            if response.status_code == 200:
                data = response.json()

                # 关键修改：从 JSON 里提取真正的纯文本结果
                # 后端 main.py 返回的是 {"status": "success", "result": "..."}
                # 所以我们要取 "result" 字段
                answer_text = data.get("result", str(data))

                # 1. 更新 UI 显示 (只显示文本，看着更清爽)
                message_placeholder.markdown(answer_text)

                # 2. 存入历史 (必须是纯字符串，否则下次发请求会报 422)
                st.session_state.messages.append({"role": "assistant", "content": answer_text})

            else:
                # ... 保持不变 ...
                error_msg = f" 请求失败 (状态码 {response.status_code})"
                message_placeholder.error(error_msg)

        except Exception as e:
            message_placeholder.error(f" 连接后端失败: {str(e)}\n请检查 docker-compose 是否正在运行！")

# 侧边栏：使用说明
with st.sidebar:
    st.header(" 功能面板")
    st.markdown("""
    **支持的能力：**
    -  **通用问答** (RAG 模式)
    -  **代码生成与执行** (Docker 沙箱)

    **试一试这些 Prompt:**
    1. `请生成一个包含5个城市的TSP旅行商问题求解代码，并打印最优路径长度。`
    2. `写一个计算斐波那契数列第10项的Python代码，打印结果。`
    3. `你好，介绍一下你自己。`
    """)