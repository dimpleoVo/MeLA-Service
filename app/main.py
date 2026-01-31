from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.core.workflow import agent_workflow

app = FastAPI(title="MeLA Service API", version="1.0")

# 增加 history 字段
class QueryRequest(BaseModel):
    query: str
    history: List[Dict[str, str]] = [] # 格式: [{"role": "user", "content": "..."}, ...]

@app.post("/v1/agent/run")
async def run_agent(request: QueryRequest):
    try:
        # 把 history 传给 workflow
        result = agent_workflow.run(request.query, request.history)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy"}