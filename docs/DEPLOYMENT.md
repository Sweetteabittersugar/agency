# Agency 部署指南

## 本地部署（推荐个人使用）

```bash
git clone https://github.com/Sweetteabittersugar/agency.git
cd agency
pip install -e .
agency start
```

## Docker 部署

```bash
docker-compose up -d
```

## 服务器部署

### 1. 使用 Gunicorn
```bash
pip install gunicorn
gunicorn -c gunicorn.conf.py maestro.flask_app:app
```

### 2. 使用 Nginx 反向代理
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8800;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }
}
```

### 3. 使用 systemd（Linux）
```ini
[Unit]
Description=Agency - Claude Code Web Panel
After=network.target

[Service]
Type=simple
User=agency
WorkingDirectory=/opt/agency
ExecStart=/opt/agency/.venv/bin/gunicorn -c gunicorn.conf.py maestro.flask_app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| AGENCY_HOST | 127.0.0.1 | 绑定地址 |
| AGENCY_PORT | 8800 | 端口 |
| AGENCY_AUTH_TOKEN | (空) | 远程访问密码 |
| AGENCY_RATE_LIMIT | 60 | 每分钟最大请求数 |
| AGENCY_NO_UPDATE_CHECK | (空) | 设为 1 关闭更新检查 |
| AGENCY_USE_LEGACY | (空) | 设为 1 使用旧 http.server |
| AGENCY_EXTRA_CORS_ORIGINS | (空) | 额外 CORS 来源，逗号分隔 |
