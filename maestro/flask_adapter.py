"""Flask 适配器 — 让现有路由处理函数在 Flask 上运行，零业务逻辑改动"""
from flask import request, Response, jsonify
import json


class FlaskHandlerAdapter:
    """模拟旧 handler 接口，适配 Flask request"""

    def __init__(self):
        self._status = 200
        self._response_data = None
        self._headers = {}

    @property
    def body(self):
        if request.is_json:
            return json.dumps(request.get_json(silent=True) or {})
        return request.get_data(as_text=True) or "{}"

    @property
    def path(self):
        return request.path

    @property
    def client_address(self):
        return (request.remote_addr or "127.0.0.1", 0)

    @property
    def headers(self):
        return request.headers

    def send_json(self, data, status=200):
        self._status = status
        self._response_data = data

    def send_response(self, code):
        self._status = code

    def send_header(self, key, value):
        self._headers[key] = value

    def end_headers(self):
        pass


def adapt_handler(old_handler_func):
    """将旧 (handler, parsed/body) 风格的处理函数包装为 Flask view"""

    def flask_view(**kwargs):
        adapter = FlaskHandlerAdapter()

        parsed = {
            "path": request.path,
            "path_parts": request.path.strip("/").split("/"),
            "query_params": dict(request.args),
        }

        try:
            if request.method in ("POST", "DELETE"):
                body_dict = request.get_json(silent=True) or {}
                old_handler_func(adapter, body_dict)
            else:
                old_handler_func(adapter, parsed)
        except TypeError:
            try:
                old_handler_func(adapter, parsed)
            except Exception as e:
                return jsonify({"ok": False, "error": str(e)}), 500
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

        if adapter._response_data is not None:
            # SSE 流式响应
            if hasattr(adapter._response_data, '__iter__') and not isinstance(
                adapter._response_data, (dict, list, str, bytes)
            ):
                def generate():
                    for chunk in adapter._response_data:
                        if isinstance(chunk, dict):
                            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                        elif isinstance(chunk, str):
                            yield chunk
                return Response(generate(), mimetype="text/event-stream")

            return jsonify(adapter._response_data), adapter._status

        return jsonify({"ok": True}), 200

    return flask_view
