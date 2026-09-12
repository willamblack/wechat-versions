#!/usr/bin/env python3
"""Generate a numerically sorted, directly linked index of GitHub releases."""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path


def fetch_releases(repo: str) -> list[dict]:
    releases = []
    page = 1
    while True:
        response = subprocess.check_output(
            ["gh", "api", f"repos/{repo}/releases?per_page=100&page={page}"],
            text=True,
        )
        batch = json.loads(response)
        releases.extend(item for item in batch if not item["draft"])
        if len(batch) < 100:
            return releases
        page += 1


def version_sort_key(tag: str) -> tuple:
    """Compare each version component and the final build as integers."""
    match = re.fullmatch(r"v?(\d+(?:\.\d+){1,3})(.*?)_(\d+)", tag)
    if not match:
        raise ValueError(f"Cannot sort release tag numerically: {tag}")
    version = tuple(int(part) for part in match.group(1).split("."))
    version += (0,) * (4 - len(version))
    date_match = re.search(r"_(\d{8})$", match.group(2))
    date_suffix = int(date_match.group(1)) if date_match else 0
    return (*version, int(match.group(3)), date_suffix, tag)


def render_index(releases: list[dict]) -> str:
    ordered = sorted(releases, key=lambda item: version_sort_key(item["tag_name"]), reverse=True)
    lines = [
        "# WeChat for Mac 版本索引",
        "",
        "按版本号各段数值倒序排列；同版本再按构建号倒序。原有 `v` 和日期后缀保留。",
        "GitHub 原生 Releases 页面有自己的排序规则，本页提供稳定的版本顺序。",
        "",
        f"共 {len(ordered)} 个版本。",
        "",
        "| 版本 | 构建号 | 发布说明 | 安装包 | 校验文件 |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for item in ordered:
        tag = item["tag_name"]
        version, build = tag.rsplit("_", 1)
        assets = {asset["name"]: asset["browser_download_url"] for asset in item["assets"]}
        dmg_name = f"WeChatMac-{tag}.dmg"
        checksum_name = f"{dmg_name}.sha256"
        if dmg_name not in assets or checksum_name not in assets:
            raise ValueError(f"Release {tag} is missing its DMG or checksum asset")
        lines.append(
            f"| {version} | {build} | [查看 Release]({item['html_url']}) "
            f"| [下载 DMG]({assets[dmg_name]}) | [SHA-256]({assets[checksum_name]}) |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"),
                        help="GitHub owner/repository (defaults to GITHUB_REPOSITORY)")
    parser.add_argument("--output", type=Path, default=Path("RELEASES.md"))
    args = parser.parse_args()
    if not args.repo or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        parser.error("--repo must be an owner/repository name")
    args.output.write_text(render_index(fetch_releases(args.repo)), encoding="utf-8")


if __name__ == "__main__":
    main()
