# 使用官方 Python 运行时作为父镜像
FROM python:3.12

# 设置工作目录
WORKDIR /app

# 将当前目录内容复制到容器的 /app 中
COPY . /app

# 安装项目依赖
RUN pip install typer pycryptodomex flask

# 暴露端口（如果你的应用需要的话）
# EXPOSE 5000

# 运行应用
CMD ["python", "server.py"]