# 1. 选择基础镜像 (Base Image)
# 使用官方 Python 3.9 轻量版，体积小，安全漏洞少
FROM python:3.9-slim

# 2. 设置工作目录 (Working Directory)
# 容器里的所有操作都在 /app 下进行
WORKDIR /app

# 3. 复制依赖清单并安装 (Install Dependencies)
# 技巧：先复制 requirements.txt 再 pip install，利用 Docker 缓存层加速构建
COPY requirements.txt .
# --no-cache-dir 减小镜像体积
# -i https://pypi.tuna.tsinghua.edu.cn/simple 是为了国内下载快一点
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 复制项目代码 (Copy Code)
COPY . .

# 5. 暴露端口 (Expose Port)
# 告诉外部，我们服务运行在 8000 端口
EXPOSE 8000

# 6. 启动命令 (Startup Command)
# 容器启动时自动执行这行命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]