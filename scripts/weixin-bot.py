#!/usr/bin/env python3
"""微信 Claude Code Bot — 独立运行脚本
用法:
  python scripts/weixin-bot.py login    # 扫码登录
  python scripts/weixin-bot.py run      # 启动消息循环
  python scripts/weixin-bot.py status   # 查看状态
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maestro.integrations.weixin_bot import WeixinBot, cmd_login
import subprocess


def handle_message(from_user_id: str, text: str, context_token: str) -> str:
    """消息处理 — 转发给 Claude Code"""
    try:
        import urllib.request, json
        req = urllib.request.Request(
            "http://127.0.0.1:8800/api/chat",
            data=json.dumps({"task": text, "session_id": f"wx_{from_user_id}"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            if isinstance(result, dict):
                return result.get("response") or result.get("message") or json.dumps(result, ensure_ascii=False)
            return str(result)
    except Exception as e:
        try:
            result = subprocess.run(
                ["claude", "-p", text],
                capture_output=True, text=True, timeout=120, cwd=os.path.expanduser("~")
            )
            return result.stdout.strip() or f"Claude 未返回内容: {result.stderr[:200]}"
        except Exception as e2:
            return f"处理失败 (Agency: {e}, Claude CLI: {e2})"


def main():
    if len(sys.argv) < 2:
        print("用法: weixin-bot.py login|run|status")
        return

    cmd = sys.argv[1]
    bot = WeixinBot()

    if cmd == "login":
        cmd_login()
    elif cmd == "run":
        if not bot.load_credentials():
            print("❌ 未找到有效凭证，请先 login")
            return
        bot.run(handle_message)
    elif cmd == "status":
        if bot.load_credentials():
            print(f"✅ 已登录: bot_id={bot.bot_id}")
        else:
            print("❌ 未登录")
    else:
        print(f"未知命令: {cmd}")


if __name__ == "__main__":
    main()
