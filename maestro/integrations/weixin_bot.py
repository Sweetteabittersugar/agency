"""微信 iLink Bot 客户端 — 基于 @tencent-weixin/openclaw-weixin v2.4.4 协议"""
import json
import time
import uuid
import base64
import random
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Callable

ILINK_BASE = "https://ilinkai.weixin.qq.com"
ILINK_APP_ID = "bot"
ILINK_APP_CLIENT_VERSION = "65547"  # 0x0001000B
BOT_AGENT = "Agency/0.4.0"
LONG_POLL_TIMEOUT = 35
API_TIMEOUT = 15

CREDENTIALS_DIR = Path(__file__).resolve().parent.parent.parent / "credentials"


def _random_uin() -> str:
    uin = random.randint(0, 0xFFFFFFFF)
    return base64.b64encode(str(uin).encode()).decode()


def _build_headers(token: str = None) -> dict:
    h = {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "X-WECHAT-UIN": _random_uin(),
        "iLink-App-Id": ILINK_APP_ID,
        "iLink-App-ClientVersion": ILINK_APP_CLIENT_VERSION,
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _build_base_info() -> dict:
    return {"channel_version": "0.4.0", "bot_agent": BOT_AGENT}


def _api_post(endpoint: str, body: dict, token: str = None, timeout: int = API_TIMEOUT) -> dict:
    """POST 请求到 iLink API"""
    body["base_info"] = _build_base_info()
    data = json.dumps(body, ensure_ascii=False).encode()

    req = urllib.request.Request(
        f"{ILINK_BASE}/{endpoint}",
        data=data,
        headers=_build_headers(token),
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"_error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"_error": str(e)}


def _api_get(endpoint: str, timeout: int = LONG_POLL_TIMEOUT) -> dict:
    """GET 请求到 iLink API"""
    req = urllib.request.Request(
        f"{ILINK_BASE}/{endpoint}",
        headers=_build_headers(),
        method="GET"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        if "timeout" in str(e).lower() or "timed out" in str(e).lower():
            return {"status": "wait"}
        return {"_error": str(e)}


class WeixinBot:
    """微信 iLink Bot 客户端"""

    def __init__(self):
        self.token: Optional[str] = None
        self.bot_id: Optional[str] = None
        self.get_updates_buf: str = ""
        self._running: bool = False
        self._message_handler: Optional[Callable] = None
        self._account_id: Optional[str] = None

    # ============ 登录 ============

    def get_qrcode(self) -> dict:
        """获取登录二维码，返回 {qrcode, qrcode_img_content}"""
        body = {"local_token_list": [self.token] if self.token else []}
        return _api_post(f"ilink/bot/get_bot_qrcode?bot_type=3", body)

    def poll_login(self, qrcode: str, timeout: int = 480) -> dict:
        """轮询扫码状态直到完成或超时
        返回 {connected: bool, token?: str, bot_id?: str, message?: str}
        """
        deadline = time.time() + timeout
        scanned = False

        while time.time() < deadline:
            result = _api_get(
                f"ilink/bot/get_qrcode_status?qrcode={qrcode}",
                timeout=LONG_POLL_TIMEOUT
            )

            status = result.get("status", "wait")

            if status == "wait":
                continue
            elif status == "scaned":
                if not scanned:
                    print("\n📱 已扫码，正在确认...")
                    scanned = True
            elif status == "verified":
                self.token = result.get("bot_token")
                self.bot_id = result.get("ilink_bot_id")
                self._save_credentials()
                return {"connected": True, "token": self.token, "bot_id": self.bot_id}
            elif status == "expired":
                return {"connected": False, "message": "二维码已过期"}
            elif status == "need_verifycode":
                return {"connected": False, "message": "需要输入验证码（暂不支持交互模式）"}
            elif "error" in result:
                return {"connected": False, "message": result.get("_error", "未知错误")}

            time.sleep(1)

        return {"connected": False, "message": "登录超时"}

    def _save_credentials(self):
        """保存登录凭证"""
        CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        cred_file = CREDENTIALS_DIR / f"weixin_{self.bot_id or 'bot'}.json"
        cred_file.write_text(json.dumps({
            "token": self.token,
            "bot_id": self.bot_id,
            "updated": time.time()
        }, ensure_ascii=False))
        print(f"✅ 凭证已保存: {cred_file}")

    def load_credentials(self, bot_id: str = None) -> bool:
        """加载已保存的凭证"""
        if bot_id:
            cred_file = CREDENTIALS_DIR / f"weixin_{bot_id}.json"
            if cred_file.exists():
                data = json.loads(cred_file.read_text())
                self.token = data["token"]
                self.bot_id = data["bot_id"]
                return True

        # 自动加载第一个找到的凭证
        if CREDENTIALS_DIR.exists():
            for f in CREDENTIALS_DIR.glob("weixin_*.json"):
                data = json.loads(f.read_text())
                self.token = data["token"]
                self.bot_id = data["bot_id"]
                return True

        return False

    # ============ 消息收发 ============

    def get_updates(self) -> list:
        """长轮询获取新消息"""
        body = {"get_updates_buf": self.get_updates_buf}
        result = _api_post("ilink/bot/getupdates", body, self.token, LONG_POLL_TIMEOUT)

        if "_error" in result:
            return []

        self.get_updates_buf = result.get("get_updates_buf", self.get_updates_buf)
        return result.get("msgs", [])

    def send_message(self, to_user_id: str, text: str, context_token: str = "") -> dict:
        """发送文本消息"""
        body = {
            "to_user_id": to_user_id,
            "context_token": context_token,
            "content": {"text": text},
            "client_msg_id": str(uuid.uuid4())
        }
        return _api_post("ilink/bot/sendmessage", body, self.token, API_TIMEOUT)

    def send_typing(self, to_user_id: str, action: str = "start") -> dict:
        """发送"正在输入"状态。action: start/stop"""
        config_body = {"ilink_user_id": to_user_id, "context_token": ""}
        config = _api_post("ilink/bot/getconfig", config_body, self.token, 10)

        typing_ticket = config.get("typing_ticket", "")
        if not typing_ticket:
            return {"_error": "无法获取 typing_ticket"}

        body = {
            "to_user_id": to_user_id,
            "typing_ticket": typing_ticket,
            "action": action
        }
        return _api_post("ilink/bot/sendtyping", body, self.token, 10)

    # ============ 运行循环 ============

    def run(self, message_handler: Callable, verbose: bool = True):
        """启动消息循环
        message_handler(from_user_id, text, context_token) -> reply_text
        """
        if not self.token:
            print("❌ 未登录，请先 login()")
            return

        self._running = True
        self._message_handler = message_handler

        print(f"🤖 微信 Bot 已启动 (bot_id: {self.bot_id})")

        while self._running:
            try:
                msgs = self.get_updates()
                for msg in msgs:
                    if msg.get("type") == 1:  # 文本消息
                        from_user = msg.get("from_user_id", "")
                        text = msg.get("content", {}).get("text", "")
                        ctx_token = msg.get("context_token", "")

                        if verbose:
                            print(f"\n📩 [{from_user[:20]}...]: {text[:100]}")

                        # 显示"正在输入"
                        self.send_typing(from_user, "start")

                        try:
                            reply = message_handler(from_user, text, ctx_token)
                        except Exception as e:
                            reply = f"处理消息时出错: {e}"

                        # 发送回复（可能超长，分段）
                        max_len = 2000
                        if len(reply) > max_len:
                            chunks = [reply[i:i+max_len] for i in range(0, len(reply), max_len)]
                            for chunk in chunks:
                                self.send_message(from_user, chunk, ctx_token)
                                time.sleep(0.5)
                        else:
                            self.send_message(from_user, reply, ctx_token)

                        if verbose:
                            print(f"📤 已回复 ({len(reply)}字)")

                        # 停止"正在输入"
                        self.send_typing(from_user, "stop")

            except KeyboardInterrupt:
                print("\n⏹️ 停止...")
                break
            except Exception as e:
                print(f"⚠️ 消息循环错误: {e}")
                time.sleep(5)

    def stop(self):
        self._running = False


# ============ CLI 入口 ============

def cmd_login():
    """命令行: 扫码登录微信"""
    bot = WeixinBot()

    # 先尝试加载已有凭证
    if bot.load_credentials():
        print(f"✅ 已有有效凭证 (bot_id: {bot.bot_id})")
        return bot

    print("📱 正在获取登录二维码...")
    qr = bot.get_qrcode()

    if "_error" in qr:
        print(f"❌ 获取二维码失败: {qr['_error']}")
        return None

    qrcode = qr.get("qrcode")
    qrcode_url = qr.get("qrcode_img_content")

    print(f"\n{'='*40}")
    print(f"请用微信扫描以下二维码:")
    print(f"{qrcode_url}")
    print(f"{'='*40}\n")

    result = bot.poll_login(qrcode)

    if result["connected"]:
        print(f"✅ 登录成功! bot_id: {result['bot_id']}")
        return bot
    else:
        print(f"❌ 登录失败: {result.get('message', '未知')}")
        return None
