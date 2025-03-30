# 使用官方Python運行時作為基礎鏡像
FROM python:3.10-slim

# 設置工作目錄
WORKDIR /app

# 設置環境變量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件
COPY requirements.txt .

# 安裝Python依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製項目文件
COPY . .

# 創建必要的目錄
RUN mkdir -p /app/logs

# 暴露端口
EXPOSE 8000

# 啟動命令
CMD ["uvicorn", "optimized_api:app", "--host", "0.0.0.0", "--port", "8000"]
