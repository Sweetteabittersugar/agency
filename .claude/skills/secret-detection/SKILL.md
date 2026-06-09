---
name: secret-detection
description: 扫描代码中硬编码的密钥、Token、密码
category: security
loading: on-demand
triggers:
  keywords: ["密钥","token","密码","硬编码","泄露"]
---

# 密钥检测

## 用途
扫描源代码中是否残留硬编码的密钥、Token、密码等敏感信息，防止泄露到版本控制。

## 核心规则
- 每次提交前运行自动扫描（gitleaks / truffleHog / detect-secrets）
- 密钥必须通过环境变量或 Secret Manager 注入，不写在代码中
- 发现密钥泄露后立即轮换旧密钥，并清理 git 历史
- `.env` 和含密钥的配置文件必须加入 `.gitignore`
- CI 管道中集成 Secret 扫描步骤，发现即阻断
