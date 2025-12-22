import os
import logging
import subprocess
import uuid
import json

class SimpleConfig:
    def __init__(self, dictionary):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                value = SimpleConfig(value)
            setattr(self, key, value)

class ELE_Service:
    def __init__(self, task_config: dict, llm_client, base_temp_dir: str = "./temp_mela_tasks"):
        # 修改：默认目录改成相对路径 ./temp_mela_tasks，防止 Windows 权限问题
        self.cfg = SimpleConfig(task_config)
        self.llm = llm_client

        self.task_id = str(uuid.uuid4())
        self.root_dir = os.path.join(base_temp_dir, self.task_id)
        os.makedirs(self.root_dir, exist_ok=True)

        # 初始化日志
        logging.basicConfig(filename=os.path.join(self.root_dir, 'run.log'), level=logging.INFO)

    def _prepare_code_file(self, code_content: str):
        file_path = os.path.join(self.root_dir, "generated_code.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code_content)
        return file_path


    def _run_code_in_docker(self, code_path: str):
        abs_dir = os.path.abspath(self.root_dir)
        cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--cpus", "1.0",
            "--memory", "512m",
            "-v", f"{abs_dir}:/app",
            "python:3.9-slim",
            "python", "/app/generated_code.py"
        ]
        logging.info(f"Sandbox Execution: {' '.join(cmd)}")

        try:
            # 这里的 subprocess.run 可能会抛出 FileNotFoundError (如果没装Docker)
            # 或者 TimeoutExpired
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return {"status": "success", "output": result.stdout}
            else:
                return {"status": "error", "error": result.stderr}
        except FileNotFoundError:
             # 专门捕获没装 Docker 的情况
             raise FileNotFoundError("Docker executable not found")
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "Code execution timed out"}
        except Exception as e:
            return {"status": "system_error", "error": str(e)}

    def run(self):
        logging.info(f"Task {self.task_id} started.")
        generated_code = """
def solve_tsp(points):
    return "Optimized Path Found"
print(solve_tsp([]))
"""
        try:
            code_path = self._prepare_code_file(generated_code)
        except Exception as e:
            logging.error(f"File system error: {e}")
            return {"status": "failed", "error": "File write failed"}

        try:
            # 尝试调用真实 Docker
            execution_result = self._run_code_in_docker(code_path)
        except Exception as e:
            # --- MOCK 触发点 ---
            # 只要上面报错 (没装 Docker)，就进这里
            # print 是为了让你在控制台看到效果
            print(f" [Mock Triggered] Docker 环境未就绪: {e}")
            execution_result = {
                "status": "success",
                "output": "【MOCK MODE】: Docker not found. Simulated Optimization Completed."
            }

        logging.info(f"Task finished. Result: {execution_result}")
        return execution_result