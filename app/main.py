import uuid
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi import UploadFile, File
import shutil
import os
# 导入引擎
from app.core.engine import ELE_Service
from app.core.rag import rag_service
from app.core.llm import llm_service
from app.core.workflow import agent_workflow
from app.core.ingestion import ingestion_service

app = FastAPI(title="MeLA Agent Service", version="1.0.0")


# --- 1. 定义数据模型 (Schema) ---
class OptimizeRequest(BaseModel):
    problem_name: str
    problem_description: str
    max_iterations: int = 5
    openai_key: Optional[str] = None


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class DocumentInput(BaseModel):
    text: str
    source: str = "user_upload"

class SearchInput(BaseModel):
    query: str
    top_k: int = 3

class ChatRequest(BaseModel):  #  新增这个类
    query: str
    history: Optional[list] = []

class AgentRequest(BaseModel):
    query: str

# --- 2. 模拟数据库 (内存版) ---
TASK_DB = {}


# --- 3. 核心任务逻辑 ---
def run_mela_background_task(task_id: str, request: OptimizeRequest):
    print(f" [Task {task_id}] 开始处理任务...")
    TASK_DB[task_id] = {"status": "running", "result": None}

    try:
        # 1. 构造配置
        task_config = {
            "problem": {"problem_name": request.problem_name},
            "max_fe": request.max_iterations
        }

        # 2. 初始化服务 (LLM先传None，反正跑Mock)
        service = ELE_Service(task_config, llm_client=None)

        # 3. 运行 (这会触发 engine.py 里的 run -> _run_code_in_docker -> Mock)
        result = service.run()

        # 4. 任务完成，存入结果
        TASK_DB[task_id]["status"] = "completed"
        TASK_DB[task_id]["result"] = str(result)
        print(f" [Task {task_id}] 任务完成: {result}")

    except Exception as e:
        TASK_DB[task_id]["status"] = "failed"
        TASK_DB[task_id]["error"] = str(e)
        print(f" [Task {task_id}] 任务失败: {e}")


# --- 4. 编写接口 (API Endpoint) ---


@app.post("/v1/optimize", response_model=TaskResponse)
async def submit_optimization_task(
        request: OptimizeRequest,
        background_tasks: BackgroundTasks
):
    """
    提交一个优化任务 (异步非阻塞)
    """
    # 生成任务 ID
    task_id = str(uuid.uuid4())

    # 将任务丢给后台运行
    background_tasks.add_task(run_mela_background_task, task_id, request)

    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Optimization task has been submitted."
    }


@app.get("/v1/task/{task_id}")
async def get_task_status(task_id: str):
    """
    轮询任务状态
    """
    task = TASK_DB.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.post("/v1/rag/add")
async def add_knowledge(doc: DocumentInput):
    """
    【数据入库】把一条知识存入向量库
    """
    try:
        count = rag_service.add_documents(
            documents=[doc.text],
            metadatas=[{"source": doc.source}]
        )
        return {"status": "success", "message": f"Added {count} document."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/rag/search")
async def search_knowledge(query: SearchInput):
    """
    【语义检索】根据问题，在知识库里找答案
    """
    results = rag_service.search(query.query, query.top_k)
    return results


@app.post("/v1/rag/upload_pdf")
async def upload_pdf_knowledge(file: UploadFile = File(...)):
    """ (Unstructured Data)
    【ETL 入口】上传 PDF -> 解析 -> 切片 -> 存入向量库
    """
    # 1. 保存上传的文件到临时目录
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = f"{temp_dir}/{file.filename}"

    # 流式写入磁盘，防止大文件撑爆内存
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 2. 调用 Ingestion 引擎进行 ETL 处理
        texts, metadatas = ingestion_service.process_pdf(temp_path)

        # 3. 存入 ChromaDB (复用 Module 2 的 RAG 服务)
        # 直接复用了之前的 add_documents 方法
        count = rag_service.add_documents(texts, metadatas)

        return {
            "status": "success",
            "filename": file.filename,
            "chunks_processed": len(texts),
            "message": f"成功解析并入库 {count} 个知识片段"
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        # 4. 清理现场：删除临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/v1/chat")
async def chat_with_agent(req: ChatRequest):
    """
    【RAG 完整链路】
    Query -> Vector Search -> Context -> Prompt -> LLM -> Answer
    """
    print(f"收到用户提问: {req.query}")

    # 1. 检索 (Retrieval)
    # 去 ChromaDB 找资料
    search_result = rag_service.search(req.query, top_k=3)
    retrieved_texts = search_result["results"]  # 获取搜到的文本列表

    print(f"检索到 {len(retrieved_texts)} 条相关知识")

    # 2. 生成 (Generation)
    # 把资料喂给 LLM (DeepSeek) 组织语言
    final_answer = llm_service.generate(
        query=req.query,
        context_chunks=retrieved_texts
    )

    return {
        "query": req.query,
        "answer": final_answer,
        "source_documents": retrieved_texts  # 为了可解释性，返回参考来源
    }

@app.post("/v1/agent/run")
async def run_agent(req: AgentRequest):
    """
    【Agent 入口】
    用户不需要知道是用 RAG 还是用优化器，Agent 自动判断。
    """
    try:
        # 调用工作流
        result = agent_workflow.run(req.query)
        return {"status": "success", "response": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}