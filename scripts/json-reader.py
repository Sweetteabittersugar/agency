#!/usr/bin/env python3
"""JSON 文件读取器 — 支持格式化输出、键值提取、管道处理"""
import json
import sys
import os
from pathlib import Path
from typing import Any


# Windows 终端 UTF-8 编码修复
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def read_json(filepath: str) -> Any:
    """读取并解析 JSON 文件，返回 Python 对象"""
    path = Path(filepath)
    if not path.exists():
        print(f"错误: 文件不存在 — {filepath}", file=sys.stderr)
        sys.exit(1)
    if not path.is_file():
        print(f"错误: 路径不是文件 — {filepath}", file=sys.stderr)
        sys.exit(1)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"读取失败: {e}", file=sys.stderr)
        sys.exit(1)


def extract_key(data: Any, key_path: str) -> Any:
    """
    按点号分隔的路径提取嵌套键值。
    例: "user.name" → data["user"]["name"]
    支持数组索引: "items.0.title"
    """
    current = data
    for segment in key_path.split("."):
        if isinstance(current, list):
            try:
                idx = int(segment)
                current = current[idx]
            except (ValueError, IndexError) as e:
                print(
                    f"键值提取错误: 数组索引无效 '{segment}' — {e}",
                    file=sys.stderr,
                )
                sys.exit(1)
        elif isinstance(current, dict):
            if segment not in current:
                print(
                    f"键值提取错误: 键不存在 '{segment}' (路径: {key_path})",
                    file=sys.stderr,
                )
                sys.exit(1)
            current = current[segment]
        else:
            print(
                f"键值提取错误: 无法从 {type(current).__name__} 中提取 '{segment}'",
                file=sys.stderr,
            )
            sys.exit(1)
    return current


def format_output(data: Any, compact: bool = False) -> str:
    """格式化数据为 JSON 字符串"""
    indent = None if compact else 2
    ensure_ascii = False
    return json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)


def print_usage():
    """打印使用说明"""
    print(
        """
用法:
  python json-reader.py <filepath>           # 格式化输出整个 JSON
  python json-reader.py <filepath> <key>     # 提取指定键值 (点号分隔)
  python json-reader.py <filepath> --raw     # 紧凑输出 (无缩进)
  python json-reader.py <filepath> --keys    # 列出顶层键 (对象) 或长度 (数组)

示例:
  python json-reader.py data.json
  python json-reader.py package.json version
  python json-reader.py data.json user.addresses.0.city
  python json-reader.py response.json --raw | jq .
  """
    )


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print_usage()
        sys.exit(0)

    filepath = sys.argv[1]
    data = read_json(filepath)

    # --keys: 列出顶层键或数组信息
    if len(sys.argv) == 3 and sys.argv[2] == "--keys":
        if isinstance(data, dict):
            print(f"顶层键 ({len(data)} 个):")
            for key in data:
                value = data[key]
                type_name = type(value).__name__
                preview = (
                    f"({len(value)} 项)"
                    if isinstance(value, (list, dict))
                    else f"= {str(value)[:50]}"
                )
                print(f"  {key}: {type_name} {preview}")
        elif isinstance(data, list):
            print(f"数组 — {len(data)} 项")
        else:
            print(f"{type(data).__name__}: {str(data)[:100]}")
        return

    # --raw: 紧凑输出
    if len(sys.argv) == 3 and sys.argv[2] == "--raw":
        print(format_output(data, compact=True))
        return

    # 键值提取
    if len(sys.argv) >= 3:
        key_path = sys.argv[2]
        data = extract_key(data, key_path)

    print(format_output(data))


if __name__ == "__main__":
    main()
