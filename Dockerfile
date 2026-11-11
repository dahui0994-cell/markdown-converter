# Markdown 转换工具 - 容器镜像
# 构建:  docker build -t md-converter .
# 运行:  docker run -d --name md-converter -p 8000:8000 md-converter
# 访问:  http://localhost:8000

FROM python:3.12-slim

# 容器内无 Edge, 渲染走 Playwright Chromium 回退路径:
# 1) 系统依赖 (playwright install --with-deps 会装好库, 但 Noto CJK 需单独装)
# 2) 中文字体: 没有的话中文渲染成豆腐块 □□□ (PDF/PNG/JPG/mermaid 图全部受影响)
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依赖先行, 利用构建缓存 (requirements.txt 不变则不重装)
# 浏览器装到全局可读目录(而非 /root/.cache), 否则下方非 root 用户无法访问
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

# 应用代码 (含 assets/js/mermaid.min.js 离线渲染库)
COPY main.py renderer.py web/ assets/ ./

# Chromium 在非 root / 无特权容器里需禁用沙箱 (renderer.py 读取该变量)
ENV BROWSER_EXTRA_ARGS="--no-sandbox"

# 非 root 用户运行 (工作目录 /app 对 1000 只读, 禁写字节码缓存避免告警)
ENV PYTHONDONTWRITEBYTECODE=1
USER 1000:1000

EXPOSE 8000

# 健康检查: 容器就绪后才算 "running"
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
