"""微信 Bot API — Web 管理端点"""
import json
import threading
import urllib.request
from maestro.integrations.weixin_bot import WeixinBot

_bot = None
_bot_thread = None
_login_status = {"state": "idle", "qrcode_img_content": "", "qrcode": "", "message": ""}


def _get_bot():
    global _bot
    if _bot is None:
        _bot = WeixinBot()
        _bot.load_credentials()
    return _bot


def handle_status(handler, parsed):
    bot = _get_bot()
    handler.send_json({
        "ok": True,
        "logged_in": bool(bot.token),
        "bot_id": bot.bot_id,
        "running": bot._running,
        "login_state": _login_status["state"],
        "login_message": _login_status["message"],
        "qrcode_img_content": _login_status.get("qrcode_img_content", "")
    })


def handle_login_start(handler, body):
    global _login_status
    bot = _get_bot()

    _login_status = {"state": "fetching", "qrcode_img_content": "", "qrcode": "", "message": "正在获取二维码..."}

    try:
        qr = bot.get_qrcode()
        if "_error" in qr:
            _login_status = {"state": "error", "qrcode_img_content": "", "qrcode": "", "message": qr["_error"]}
            handler.send_json({"ok": False, "error": qr["_error"]})
            return

        qrcode_img = qr.get("qrcode_img_content", "")
        qrcode = qr.get("qrcode", "")

        _login_status = {
            "state": "waiting_scan",
            "qrcode_img_content": qrcode_img,
            "qrcode": qrcode,
            "message": "请用微信扫码"
        }

        def poll():
            global _login_status
            result = bot.poll_login(qrcode, timeout=300)
            if result.get("connected"):
                _login_status = {"state": "connected", "qrcode_img_content": "", "qrcode": "", "message": f"已连接: {result.get('bot_id', '')}"}
            else:
                _login_status = {"state": "error", "qrcode_img_content": "", "qrcode": "", "message": result.get("message", "登录失败")}

        t = threading.Thread(target=poll, daemon=True)
        t.start()

        handler.send_json({"ok": True, "qrcode_img_content": qrcode_img, "message": "请扫码"})
    except Exception as e:
        _login_status = {"state": "error", "qrcode_img_content": "", "qrcode": "", "message": str(e)}
        handler.send_json({"ok": False, "error": str(e)})


def handle_start(handler, body):
    global _bot_thread
    bot = _get_bot()

    if not bot.token:
        handler.send_json({"ok": False, "error": "未登录，请先扫码"})
        return

    if bot._running:
        handler.send_json({"ok": True, "message": "已在运行中"})
        return

    def handle_msg(from_user, text, ctx_token):
        try:
            data = json.dumps({"task": text, "session_id": f"wx_{from_user}"}).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:8800/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
                return result.get("response") or result.get("message") or str(result)
        except Exception as e:
            return f"处理失败: {e}"

    _bot_thread = threading.Thread(target=bot.run, args=(handle_msg,), kwargs={"verbose": False}, daemon=True)
    _bot_thread.start()

    handler.send_json({"ok": True, "message": "Bot 已启动"})


def handle_stop(handler, body):
    bot = _get_bot()
    if bot and bot._running:
        bot.stop()
        handler.send_json({"ok": True, "message": "Bot 已停止"})
    else:
        handler.send_json({"ok": True, "message": "未在运行"})


def handle_logout(handler, body):
    global _bot, _login_status
    if _bot:
        _bot.stop()
    _bot = None
    _login_status = {"state": "idle", "qrcode_img_content": "", "qrcode": "", "message": ""}
    handler.send_json({"ok": True, "message": "已退出"})
