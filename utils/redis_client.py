''''
import json
import redis
from typing import Optional

# 1. 连接 Redis (生产环境一般从环境变量读取 host)
# redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

class RedisManager:
    """
    这是给面试官看的：生产环境 Redis 管理类
    """
    def __init__(self):
        # 模拟连接，实际运行时取消注释上面的 redis.Redis
        self.client = None
        pass

    def set_task_status(self, task_id: str, status_data: dict, ttl: int = 3600):
        """
        存状态：自动转 JSON，并设置 1 小时过期
        """
        if self.client:
            # redis 只能存字符串，所以要 json.dumps
            self.client.setex(
                name=f"task:{task_id}",
                time=ttl,
                value=json.dumps(status_data)
            )

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """
        取状态：自动转回字典
        """
        if self.client:
            data = self.client.get(f"task:{task_id}")
            if data:
                return json.loads(data)
        return None
    '''