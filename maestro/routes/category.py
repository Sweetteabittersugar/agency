"""8 领域分类器 — 在路由前先判断任务领域"""
import re

CATEGORIES = {
    "代码开发": ["代码", "写", "改", "重构", "实现", "开发", "bug", "fix", "函数", "类", "模块", "接口"],
    "代码审查": ["审查", "review", "检查代码", "code review", "安全检查"],
    "测试质量": ["测试", "test", "单元测试", "集成测试", "e2e", "覆盖率"],
    "文档写作": ["文档", "readme", "注释", "api文档", "写作", "小说", "文章"],
    "数据分析": ["分析", "数据", "统计", "报表", "图表", "可视化"],
    "运维部署": ["部署", "docker", "k8s", "ci", "cd", "容器", "镜像", "配置"],
    "搜索探索": ["查找", "搜索", "grep", "定位", "探索", "梳理"],
    "通用任务": ["整理", "清理", "杂务", "文件", "格式"],
}


def classify(task: str) -> str:
    """返回最匹配的领域名"""
    tl = task.lower()
    best, best_score = "通用任务", 0
    for cat, keywords in CATEGORIES.items():
        score = sum(2 for kw in keywords if kw.lower() in tl)
        if score > best_score:
            best, best_score = cat, score
    return best
