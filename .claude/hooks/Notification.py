#!/usr/bin/env python3
"""Notification Hook — 系统通知：飞书 webhook + 错误告警"""
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ALERTS_FILE = PROJECT_ROOT / "maestro" / "alerts.log"
FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "")


def get_notification_data():
    """从 stdin 或环境变量读取通知信息"""
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read().strip()
            if raw:
                return json.loads(raw)
    except Exception:
        pass
    return {
        "type": os.environ.get("CLAUDE_NOTIFICATION_TYPE", "info"),
        "message": os.environ.get("CLAUDE_NOTIFICATION_MSG", ""),
    }


def send_feishu(title, content, level="info"):
    """发送飞书 webhook 通知"""
    if not FEISHU_WEBHOOK_URL:
        return False

    color_map = {"error": "red", "warn": "yellow", "info": "green"}
    color = color_map.get(level, "green")

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"Agency — {title}"},
                "template": color,
            },
            "elements": [
                {"tag": "div", "text": {"tag": "plain_text", "content": content[:2000]}},
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    ],
                },
            ],
        },
    }

    try:
        req = urllib.request.Request(
            FEISHU_WEBHOOK_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False


def write_alert(data):
    """写入告警日志"""
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": data.get("type", "unknown"),
        "message": data.get("message", ""),
        "source": data.get("source", "notification_hook"),
    }
    with open(ALERTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    data = get_notification_data()
    ntype = data.get("type", "info")
    message = data.get("message", "")

    if ntype in ("error", "timeout", "danger"):
        write_alert(data)
        send_feishu(f"告警: {ntype}", message, level="error")
        print(f"ALERT_LOGGED: {ntype}")

    elif ntype in ("long_task_complete", "task_complete", "complete"):
        title = data.get("task_name", data.get("agent", "任务"))
        send_feishu(f"长任务完成: {title}", message, level="info")
        print(f"FEISHU_SENT: {title}")

    else:
        # 普通信息通知，只记录
        print(f"NOTIFICATION: {ntype}")


if __name__ == "__main__":
    main()
