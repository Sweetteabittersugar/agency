# Agency

[English](README.en.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md)

[![Version](https://img.shields.io/badge/version-0.5.0-green)](VERSION)
[![CI](https://github.com/Sweetteabittersugar/agency/actions/workflows/ci.yml/badge.svg)](https://github.com/Sweetteabittersugar/agency/actions/workflows/ci.yml)
[![Source only](https://img.shields.io/badge/distribution-source--only-blue)](#安装)

Agency 是一个面向本地开发工作的 Web 工作台：把 Agent 路由、多阶段执行、成本记录和可恢复运行放在同一个界面中。v0.5.0 是 GitHub 源码发行版，不发布到 PyPI 或 npm。

当前产品注册表包含 **33 个 Agent、7 个 Skill**。这两个数字分别由 [agent.yaml](agent.yaml) 和 [skills/](skills/) 校验；运行时投影或 Markdown 文件数可能不同，不应混为同一指标。

## v0.5.0 的重点

- 本地 SQLite run ledger：保存追加事件、DAG checkpoint、action intent/result 和 runner fence。
- 可恢复编排：`POST /api/orchestrate` 接受可选 `run_id`；task 或 project 不匹配会返回 `RUN_RESUME_REJECTED`。
- 副作用保护：崩溃后若存在无结果的写操作意图，返回 `ACTION_RECONCILIATION_REQUIRED`，不会自动重放。
- 项目路径边界：只有通过可重复 `--project-root PATH` 声明的目录才能用于文件、终端、测试和 Agent 执行。
- 正式 CLI：帮助和版本查询不会启动服务；默认只监听 `127.0.0.1`。

## 安装

要求 Python 3.10–3.13。以下是本版本唯一支持的分发方式：

```bash
git clone https://github.com/Sweetteabittersugar/agency.git
cd agency
git checkout v0.5.0
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
agency --version
```

macOS / Linux：

```bash
source .venv/bin/activate
python -m pip install -e .
agency --version
```

输出应只有：

```text
0.5.0
```

## 启动

```bash
agency start --project-root /path/to/your/project
```

默认地址为 `http://127.0.0.1:8800`。多个允许目录可重复传参：

```bash
agency start \
  --project-root /path/to/project-a \
  --project-root /path/to/project-b
```

未声明任何 project root 时，界面仍可启动，但项目文件浏览、Agent 执行、终端和测试操作会被拒绝。所有请求路径都会重新规范化，并在跟随 symlink/junction 后检查是否仍位于 allowlist 内。

非本机监听必须先显式配置认证：

```bash
export AGENCY_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
agency start --host 0.0.0.0 --project-root /path/to/project
```

PowerShell 可用 `$env:AGENCY_TOKEN = & python -c "import secrets; print(secrets.token_urlsafe(32))"` 生成临时 token。没有 token 时，非 loopback 启动会直接失败。

## 模型服务与 API Key

Agency 支持由用户选择的模型服务商。为了完成请求，API key 和必要的提示内容会发送给该服务商；请同时阅读服务商自己的数据处理条款。

Web UI 可将 key 放在浏览器 `localStorage`。这便于本地使用，但如果页面发生 XSS，key 可能被读取。更稳妥的方式是使用环境变量，并只在可信的本机环境打开 UI。不要把 `.env`、真实 key 或凭据提交到仓库。

## 可恢复运行

新消息不会携带旧 `run_id`。只有用户点击界面里的“恢复运行”时，前端才会用原 task、project 和 `run_id` 发起恢复请求。

```json
{
  "task": "为当前项目增加测试",
  "proj_dir": "/allowed/project",
  "run_id": "optional-existing-run-id"
}
```

一个 `run_id` 同时只能被一个 runner 持有。若进程在可能产生副作用的动作后中断、但没有记录结果，Agency 会要求人工对账；确认文件、命令或外部状态之前，不应继续该运行。

## 安全边界

- 默认仅监听 loopback；非 loopback 必须认证。
- project root 是 allowlist，不是展示用提示。越界路径和 symlink/junction 绕过会被拒绝。
- 有 Docker 时，可由相关功能提供额外隔离；**没有 Docker 时，命令拥有启动 Agency 的当前操作系统用户权限**。
- 本项目不是多租户服务，也没有声称能把所有模型输入或秘密永久留在设备内。
- 漏洞请按 [SECURITY.md](SECURITY.md) 私下报告，不要把真实 secret 放进 Issue。

## Known Limitations

- v0.5.0 是 source-only release；没有 PyPI/npm 包、安装器二进制或托管 SaaS。
- 恢复机制不会自动判断外部副作用是否成功；出现 `ACTION_RECONCILIATION_REQUIRED` 时需要人工核对。
- Web UI 的凭据存储仍受浏览器/XSS 风险影响。
- Windows junction 测试依赖运行环境允许创建目录链接；不支持时测试会明确 skip。
- 单机 ledger 和 token 认证适合个人开发环境，不等价于企业多用户权限系统。

## 验证

发布 CI 的固定检查名为：

- `Quality`
- `Tests (Python 3.10)`
- `Tests (Python 3.11)`
- `Tests (Python 3.12)`
- `Tests (Python 3.13)`

本地可运行：

```bash
python -m pip install -e ".[dev]"
ruff check .
python -m compileall -q maestro scripts
python scripts/verify_release.py
python -m pytest -q
```

版本一致性、33/7 注册表计数、source-only 包设置和公开树禁用内容均由 `scripts/verify_release.py` 检查。

## 参与贡献

维护以 best effort 方式进行，不承诺固定响应 SLA。提交前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)，运行 Ruff、pytest 和发布校验。

许可证：[MIT](LICENSE)
