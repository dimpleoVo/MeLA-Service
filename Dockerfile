# 1. 基础镜像
FROM python:3.9-slim

# 2. 设置工作目录
WORKDIR /app

# --- 🔥 核心修复：安装最新版 Docker CLI (解决 API version 1.41 报错) ---
# 1. 安装 curl (为了下载文件)
# 2. 从 Docker 官网下载最新的静态二进制文件 (v26.1.3)
# 3. 解压并把 docker 命令移动到系统目录
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y curl && \
    curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-26.1.3.tgz -o docker.tgz && \
    tar xzvf docker.tgz && \
    mv docker/docker /usr/local/bin/ && \
    rm -rf docker docker.tgz /var/lib/apt/lists/*
# --- 🔥 修复结束 ---

# 4. 复制依赖并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 5. 复制所有代码
COPY . .

# 6. 暴露端口
EXPOSE 8000

# 7. 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]