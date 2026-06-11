FROM python:3.12-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm git \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir -e . && pip install gunicorn

# 安装 Claude CLI
RUN npm install -g @anthropic-ai/claude-code

# 复制应用
COPY . .

# 创建数据目录
RUN mkdir -p maestro/sessions maestro/worktrees credentials

EXPOSE 8800

ENV AGENCY_HOST=0.0.0.0
ENV AGENCY_PORT=8800

CMD ["gunicorn", "-c", "gunicorn.conf.py", "maestro.flask_app:app"]
