"""统一的 .env 加载"""
import os
from pathlib import Path

def load_dotenv(project_root: Path = None):
    """加载 .env 文件中的环境变量（不覆盖已有值）"""
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent
    env_file = project_root / ".env"
    if not env_file.exists():
        return
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
