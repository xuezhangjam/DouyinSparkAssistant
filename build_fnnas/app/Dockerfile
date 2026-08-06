FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# 注入无头模式环境变量，防止 Playwright 尝试打开 UI
ENV DOUYIN_HEADLESS=true

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Web 服务器依赖
RUN pip install --no-cache-dir fastapi uvicorn websockets

COPY . .

# 暴露 FastAPI 服务端口
EXPOSE 8080

CMD ["uvicorn", "web_server:app", "--host", "0.0.0.0", "--port", "8080"]
