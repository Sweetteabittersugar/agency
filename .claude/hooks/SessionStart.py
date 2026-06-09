#!/usr/bin/env python3
"""SessionStart Hook — 启动环境检查"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATUS_FILE = PROJECT_ROOT / "maestro" / "env_status.json"


def check_mcp_servers():
    """检查 MCP 服务配置状态"""
    mcp_file = PROJECT_ROOT / ".mcp.json"
    servers = {}
    if mcp_file.exists():
        try:
            mcp = json.loads(mcp_file.read_text(encoding="utf-8"))
            for name in mcp.get("mcpServers", {}):
                srv = mcp["mcpServers"][name]
                # 检查必要配置是否存在
                if isinstance(srv, dict):
                    has_command = bool(srv.get("command") or srv.get("url"))
                    has_key = True
                    # 检查环境变量引用是否已配置
                    env = srv.get("env", {})
                    for _k, v in env.items():
                        if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                            env_key = v[2:-1]
                            if not os.environ.get(env_key):
                                has_key = False
                                break
                    servers[name] = has_command and has_key
                else:
                    servers[name] = False
        except Exception:
            servers = {"_error": False}
    return servers


def check_api_key():
    """检查 API Key 是否有效"""
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if deepseek_key:
        return True, "deepseek"
    elif anthropic_key:
        return True, "anthropic"
    elif openai_key:
        return True, "openai"
    else:
        # 检查 .env 文件
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            try:
                content = env_file.read_text(encoding="utf-8")
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("DEEPSEEK_API_KEY") and "=" in line:
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and not val.startswith("your-"):
                            return True, "deepseek"
                    if line.startswith("ANTHROPIC_API_KEY") and "=" in line:
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and not val.startswith("your-"):
                            return True, "anthropic"
            except Exception:
                pass
        return False, "none"


def main():
    api_valid, api_provider = check_api_key()
    mcp_servers = check_mcp_servers()

    status = {
        "api_key_valid": api_valid,
        "api_provider": api_provider,
        "mcp_servers": mcp_servers,
        "project_dir": str(PROJECT_ROOT),
        "checked_at": datetime.now().isoformat(),
    }

    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(status))  # 输出到 stdout 供 Claude Code 日志


if __name__ == "__main__":
    main()
