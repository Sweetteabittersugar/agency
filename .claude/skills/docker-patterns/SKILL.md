---
name: docker-patterns
description: Docker 最佳实践 —— 多阶段构建、镜像层优化、安全运行、编排模式
category: devops
loading: on-demand
triggers:
  keywords: ["Docker", "容器", "docker-compose", "镜像", "Containerfile"]
---

# 这是什么

Docker 容器化是现代软件交付的标准方式。本 Skill 提供镜像构建优化、安全运行、服务编排的方法论和最佳实践。

# 何时使用

- 新项目容器化
- 现有 Dockerfile/镜像优化体积和构建速度
- 多服务项目的本地开发环境搭建
- 排查容器运行时问题
- 制定团队容器使用规范

# 核心规则

1. **一个容器一个职责**：每个容器只运行一个进程。不要在一个容器里同时跑应用服务器、数据库和消息队列。
2. **镜像不可变**：镜像构建完成后不修改。配置通过环境变量、挂载卷或 ConfigMap 注入。
3. **非 root 运行**：容器内应用不以 root 用户运行。即使容器被攻破，攻击者的权限也受限。
4. **最小基础镜像**：能选 alpine 不选 ubuntu，能选 scratch 不选 alpine。减少攻击面和镜像体积。
5. **层数最小化**：合并 RUN 命令，清理临时文件，利用构建缓存。

# 工作流程

1. **镜像设计**
   - 选择合适的基础镜像：官方镜像优先，固定版本号而非 latest 标签
   - 规划分层：变化频繁的放在后面，基础依赖放在前面利用缓存
   - 多阶段构建：构建依赖在第一个阶段，运行时只复制必要产物到最终镜像

2. **Dockerfile 编写**
   - 使用 `.dockerignore` 排除不需要的文件
   - COPY 优于 ADD，ADD 仅在需要自动解压 tar 时使用
   - 在单个 RUN 中合并多个命令以减少层数
   - 在 RUN 结束后清理包管理器缓存

3. **构建与缓存**
   - 利用构建缓存：将不常变的依赖安装放在前面
   - 使用 `--cache-from` 从注册表拉取缓存
   - CI 中使用 BuildKit 启用并行构建和高级缓存

4. **安全加固**
   - 设置 `USER` 为非 root 用户
   - 扫描镜像漏洞
   - 不在镜像中存储密钥
   - 使用签名镜像并验证完整性

5. **健康检查**
   - 为每个服务定义 HEALTHCHECK 指令
   - 健康检查应验证核心功能而非仅检查进程存在
   - 合理设置检查间隔、超时和重试次数

# 多阶段构建模式

```dockerfile
# 阶段 1：构建
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /app/server

# 阶段 2：运行
FROM alpine:3.19
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
COPY --from=builder /app/server /app/server
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1
CMD ["/app/server"]
```

# 镜像层优化

- **顺序规则**：将变化频率最低的指令放在最前面。COPY package.json → RUN npm install → COPY . .
- **合并 RUN**：`apt-get update && apt-get install -y pkg1 pkg2 && rm -rf /var/lib/apt/lists/*`
- **避免冗余文件**：`.dockerignore` 中排除 `.git`、`node_modules`、日志文件
- **层复用**：相同指令 + 相同上下文 = 缓存命中。任何变化导致该层及之后所有层重建

# Compose 编排

- **服务定义**：每个服务一个容器，通过服务名互相发现
- **网络隔离**：前端网络、后端网络分离，只有需要跨网络通信的服务加入多个网络
- **卷管理**：命名卷用于持久数据，绑定挂载仅用于开发环境
- **环境变量**：敏感值用 `.env` 文件（不提交），非敏感值直接写在 compose 文件中
- **依赖声明**：`depends_on` 控制启动顺序，但应用自身应实现重试逻辑等待依赖就绪

# 容器安全要点

- 禁止 `--privileged` 模式，除非确有必要
- 限制容器资源（CPU、内存），防止单容器耗尽宿主机资源
- 只读根文件系统 `--read-only`，写入路径显式挂载 tmpfs 或卷
- 使用 seccomp、AppArmor 或 SELinux 限制系统调用
- 定期更新基础镜像并重新构建

# 参考标准

- Docker 官方最佳实践文档
- OCI（Open Container Initiative）规范
- CIS Docker Benchmark —— 容器安全加固基准
- Google Distroless 镜像 —— 最小化生产镜像方案
- Docker BuildKit 文档 —— 高级构建特性
