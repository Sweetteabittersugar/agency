bind = "127.0.0.1:8800"
workers = 2
threads = 4
timeout = 300
loglevel = "info"
accesslog = "-"
errorlog = "-"

# 优雅关闭
graceful_timeout = 30
worker_shutdown_timeout = 10

# 进程管理
preload_app = True
max_requests = 1000
max_requests_jitter = 100

# 钩子
def when_ready(server):
    print("🟢 Gunicorn 已就绪")

def on_exit(server):
    print("🔴 Gunicorn 已停止")
