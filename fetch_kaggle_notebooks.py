#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 Kaggle 官方 API 获取最新的 Jupyter Notebook 列表，并生成纯文本摘要。

认证方式：
- 本地运行：读取 ~/.kaggle/kaggle.json（在 kaggle.com 的 Settings -> API 里生成）；
- CI 环境：读取环境变量 KAGGLE_USERNAME 与 KAGGLE_KEY（由 GitHub Secrets 注入）。
"""

import argparse
import logging
from datetime import datetime, timezone

from kaggle.api.kaggle_api_extended import KaggleApi

KAGGLE_CODE_BASE_URL = "https://www.kaggle.com/code/"


def fetch_latest_notebooks(page_size: int = 20) -> list[dict]:
    """获取最新的公开 Notebook 列表。

    返回按最近运行时间倒序排列的字典列表，每个字典包含：
    title（标题）、author（作者）、votes（投票数）、link（链接）、last_run（最近运行时间）。
    """
    api = KaggleApi()
    api.authenticate()

    kernels = (
        api.kernels_list(
            kernel_type="notebook",   # 只取 Notebook（Jupyter），排除 Script
            sort_by="dateCreated",    # 按创建时间排序
            page_size=page_size,
        )
        or []
    )

    notebooks = []
    for kernel in kernels:
        last_run = getattr(kernel, "last_run_time", None)
        notebooks.append(
            {
                "title": getattr(kernel, "title", None) or "(untitled)",
                "author": getattr(kernel, "author", None) or "unknown",
                # 注意：kaggle 1.8.x（kagglesdk）返回的字段是 snake_case
                "votes": int(getattr(kernel, "total_votes", 0) or 0),
                "link": f"{KAGGLE_CODE_BASE_URL}{kernel.ref}",
                # last_run_time 是 datetime 对象，转成 ISO 字符串便于排序
                "last_run": last_run.isoformat() if last_run else "",
            }
        )

    # 兜底排序：按最近运行时间从新到旧（ISO 时间字符串可按字典序直接比较）
    notebooks.sort(key=lambda nb: nb["last_run"], reverse=True)
    return notebooks


def render_summary(notebooks: list[dict]) -> str:
    """将 Notebook 列表渲染为纯文本摘要。"""
    fetched_at = datetime.now(timezone.utc)
    lines = [
        "Kaggle 最新 Jupyter Notebook 列表",
        f"抓取时间: {fetched_at.strftime('%Y-%m-%d %H:%M:%S')} (UTC)",
        "=" * 60,
        "",
    ]
    if not notebooks:
        lines.append("未找到任何 Notebook。")
        return "\n".join(lines)

    for index, nb in enumerate(notebooks, start=1):
        lines.append(f"{index}. {nb['title']}")
        lines.append(f"   作者: {nb['author']}")
        lines.append(f"   票数: {nb['votes']}")
        lines.append(f"   链接: {nb['link']}")
        lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="获取 Kaggle 最新 Notebook 并生成纯文本摘要。"
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=20,
        help="要抓取的 Notebook 数量（Kaggle API 单页上限为 100）。",
    )
    parser.add_argument(
        "--output",
        default="kaggle_notebooks_summary.txt",
        help="纯文本摘要的输出文件路径。",
    )
    parser.add_argument(
        "--print",
        dest="print_stdout",
        action="store_true",
        help="同时把摘要打印到标准输出（便于在 CI 日志中查看）。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    notebooks = fetch_latest_notebooks(page_size=args.page_size)
    summary = render_summary(notebooks)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(summary)
    logging.info("已把 %d 个 Notebook 的摘要写入 %s", len(notebooks), args.output)

    if args.print_stdout:
        print(summary)


if __name__ == "__main__":
    main()
