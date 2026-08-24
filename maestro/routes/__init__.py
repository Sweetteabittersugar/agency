"""路由注册中心 — 从 route_registry.py 统一路由表派生

兼容旧 web.py 的 register_all(Handler) 模式。
新增路由一律在 route_registry.py 的 ROUTES 表中添加。
"""


def register_all(Handler):
    """将统一路由表的路由函数注入 Handler 类（兼容旧 web.py）"""
    from maestro.route_registry import ROUTES

    Handler._get_routes = []
    Handler._post_routes = []
    Handler._delete_routes = []

    for method, path, handler, _endpoint in ROUTES:
        legacy_path = path.split("<", 1)[0] if "<" in path else path
        if method == "GET":
            Handler._get_routes.append((legacy_path, handler))
        elif method == "POST":
            Handler._post_routes.append((legacy_path, handler))
        elif method == "DELETE":
            Handler._delete_routes.append((legacy_path, handler))
