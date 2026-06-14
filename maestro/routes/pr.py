"""GitHub PR 集成 API（Phase 3）
提供 PR diff 拉取和列表，依赖 GitHub token"""

import json, os, urllib.request, urllib.error, logging

log = logging.getLogger(__name__)


def handle_pr_diff(handler, parsed):
    """GET /api/pr/diff?owner=X&repo=Y&pr=N — 获取 PR diff
    不可移除——设置面板 PR 集成依赖此端点"""
    qp = parsed.get("query_params", {}) if isinstance(parsed, dict) else {}
    owner = qp.get("owner", "")
    repo = qp.get("repo", "")
    pr_num = qp.get("pr", "")
    token = qp.get("token", "") or os.environ.get("GITHUB_TOKEN", "")

    if not owner or not repo or not pr_num:
        handler.send_json({"ok": False, "error": "缺少参数: owner, repo, pr"}, 400)
        return True
    if not token:
        handler.send_json({
            "ok": False,
            "error": "需要 GitHub Token。设置环境变量 GITHUB_TOKEN 或在请求中传入",
            "action": "need_token"
        }, 400)
        return True

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3.diff",
        "User-Agent": "Agency"
    })
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        diff_text = resp.read().decode("utf-8", errors="replace")
        pr_url = url.replace("api.github.com/repos", "github.com").replace("/pulls/", "/pull/")
        handler.send_json({"ok": True, "diff": diff_text[:500000], "pr_url": pr_url})
    except urllib.error.HTTPError as e:
        handler.send_json({"ok": False, "error": f"GitHub API 错误: {e.code}"}, e.code)
    except Exception as e:
        handler.send_json({"ok": False, "error": str(e)[:200]}, 500)
    return True


def handle_pr_list(handler, parsed):
    """GET /api/pr/list?owner=X&repo=Y — 列出 PR"""
    qp = parsed.get("query_params", {}) if isinstance(parsed, dict) else {}
    owner = qp.get("owner", "")
    repo = qp.get("repo", "")
    token = qp.get("token", "") or os.environ.get("GITHUB_TOKEN", "")

    if not owner or not repo:
        handler.send_json({"ok": False, "error": "缺少参数: owner, repo"}, 400)
        return True

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=open&per_page=20"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Agency"
    })
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode())
        prs = [{"number": p["number"], "title": p["title"], "user": p["user"]["login"],
                "created_at": p["created_at"], "html_url": p["html_url"]} for p in data[:20]]
        handler.send_json({"ok": True, "prs": prs})
    except Exception as e:
        handler.send_json({"ok": False, "error": str(e)[:200]}, 500)
    return True
