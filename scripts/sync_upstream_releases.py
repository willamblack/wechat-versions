#!/usr/bin/env python3
"""Copy upstream DMG releases to this fork, adding the DMG's build number.

Each release is downloaded, verified, mounted read-only, uploaded, and removed
before the next one. A successful source release is recorded in the new body,
so rerunning this command skips releases already copied.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from destVersionForMac import compute_sha256, get_tag_from_plist, parse_release_body

UPSTREAM = "zsbai/wechat-versions"
TARGET = os.environ.get("TARGET_REPO", "willamblack/wechat-versions")


def run(*args: str, check: bool = True) -> str:
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    if check and result.returncode:
        raise RuntimeError(f"{' '.join(args)} failed: {result.stdout.strip()}")
    return result.stdout


def releases(repo: str) -> list[dict]:
    result = []
    page = 1
    while True:
        batch = json.loads(run("gh", "api", f"repos/{repo}/releases?per_page=100&page={page}"))
        result.extend(batch)
        if len(batch) < 100:
            return result
        page += 1


def update_dest_version(content: str, tag: str) -> str:
    pattern = r"(?m)^(-\s*)?DestVersion:\s*.*$"
    if re.search(pattern, content):
        return re.sub(pattern, lambda m: f"{m.group(1) or ''}DestVersion: {tag}",
                      content, count=1)
    return f"DestVersion: {tag}\n" + content


def source_url(source_tag: str) -> str:
    return f"https://github.com/{UPSTREAM}/releases/tag/{source_tag}"


def copied_source(release: dict) -> str:
    return parse_release_body(release.get("body") or "").get("UpstreamRelease", "")


def sync_one(source: dict, target_by_source: dict[str, dict], latest_source_tag: str) -> str:
    source_tag = source["tag_name"]
    url = source_url(source_tag)
    old = target_by_source.get(url)
    if old:
        names = {asset["name"] for asset in old["assets"]}
        tag = old["tag_name"]
        if {f"WeChatMac-{tag}.dmg", f"WeChatMac-{tag}.dmg.sha256"} <= names:
            print(f"SKIP {source_tag}: already copied as {tag}", flush=True)
            return "skipped"
        raise RuntimeError(f"Existing copied release {tag} has missing assets; inspect it before retrying")

    dmg_asset = next((a for a in source["assets"] if a["name"].endswith(".dmg")), None)
    if not dmg_asset:
        raise RuntimeError(f"No DMG asset in {source_tag}")
    expected_body_sha = parse_release_body(source.get("body") or "").get("Sha256", "").lower()
    expected_asset_sha = (dmg_asset.get("digest") or "").removeprefix("sha256:").lower()
    if expected_body_sha and expected_asset_sha and expected_body_sha != expected_asset_sha:
        raise RuntimeError(f"Upstream body and asset checksum disagree for {source_tag}")
    expected_sha = expected_asset_sha or expected_body_sha
    if not expected_sha:
        raise RuntimeError(f"No upstream checksum for {source_tag}")

    with tempfile.TemporaryDirectory(prefix="wechat-release-") as temp:
        tmp = Path(temp)
        print(f"DOWNLOAD {source_tag} ({dmg_asset['size']} bytes)", flush=True)
        run("gh", "release", "download", source_tag, "-R", UPSTREAM,
            "-p", dmg_asset["name"], "-D", temp)
        dmg = tmp / dmg_asset["name"]
        actual_sha = compute_sha256(dmg)
        if actual_sha.lower() != expected_sha:
            raise RuntimeError(f"SHA-256 mismatch for {source_tag}: {actual_sha} != {expected_sha}")

        mount = tmp / "mounted"
        mounted = False
        try:
            run("hdiutil", "attach", "-quiet", "-readonly", "-nobrowse",
                "-mountpoint", str(mount), str(dmg))
            mounted = True
            inspected_tag = get_tag_from_plist(str(mount))
        finally:
            if mounted:
                run("hdiutil", "detach", "-quiet", str(mount))
        build = inspected_tag.rsplit("_", 1)[-1]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+_-]*", source_tag):
            raise RuntimeError(f"Unsafe upstream tag: {source_tag!r}")
        tag = f"{source_tag}_{build}"

        existing_result = subprocess.run(
            ["gh", "release", "view", tag, "-R", TARGET, "--json", "body,assets"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if existing_result.returncode == 0:
            existing = json.loads(existing_result.stdout)
            existing_sha = parse_release_body(existing.get("body") or "").get("Sha256", "").lower()
            if existing_sha != actual_sha:
                raise RuntimeError(f"Target tag {tag} exists with a different SHA-256")
            names = {a["name"] for a in existing["assets"]}
            if {f"WeChatMac-{tag}.dmg", f"WeChatMac-{tag}.dmg.sha256"} <= names:
                print(f"SKIP {source_tag}: matching target tag {tag} exists", flush=True)
                return "skipped"
            raise RuntimeError(f"Target tag {tag} exists but has missing assets; inspect it before retrying")
        if "release not found" not in existing_result.stderr.lower():
            raise RuntimeError(f"Could not check target tag {tag}: {existing_result.stderr.strip()}")

        notes = update_dest_version(source.get("body") or "", tag).rstrip()
        notes += f"\n\nUpstreamRelease: {url}\n"
        notes_path = tmp / "notes.txt"
        notes_path.write_text(notes, encoding="utf-8")

        checksum_asset = next((a for a in source["assets"] if a["name"].endswith(".dmg.sha256")), None)
        if checksum_asset:
            run("gh", "release", "download", source_tag, "-R", UPSTREAM,
                "-p", checksum_asset["name"], "-D", temp)
            checksum_content = (tmp / checksum_asset["name"]).read_text(encoding="utf-8")
            checksum_content = update_dest_version(checksum_content, tag)
        else:
            info = parse_release_body(source.get("body") or "")
            checksum_content = f"DestVersion: {tag}\nSha256: {actual_sha}\n"
            for field in ("UpdateTime", "DownloadFrom"):
                if info.get(field):
                    checksum_content += f"{field}: {info[field]}\n"

        new_dmg = tmp / f"WeChatMac-{tag}.dmg"
        dmg.rename(new_dmg)
        checksum = tmp / f"WeChatMac-{tag}.dmg.sha256"
        checksum.write_text(checksum_content, encoding="utf-8")
        print(f"PUBLISH {tag} sha256={actual_sha}", flush=True)
        run("gh", "release", "create", tag, str(new_dmg), str(checksum),
            "-R", TARGET, "--title", f"Wechat For Mac {tag}",
            "--notes-file", str(notes_path),
            "--latest" if source_tag == latest_source_tag else "--latest=false")
        return "published"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="Sync one upstream release tag")
    parser.add_argument("--offset", type=int, default=0, help="Start at this upstream release index")
    parser.add_argument("--limit", type=int, help="Process at most this many upstream releases")
    parser.add_argument("--dry-run", action="store_true", help="List selected releases without downloading")
    args = parser.parse_args()
    if args.offset < 0 or (args.limit is not None and args.limit < 1):
        parser.error("--offset must be nonnegative and --limit must be positive")
    source = releases(UPSTREAM)
    selected = [s for s in source if s["tag_name"] == args.tag] if args.tag else source[args.offset:]
    if args.tag and not selected:
        parser.error(f"upstream tag not found: {args.tag}")
    if args.limit is not None:
        selected = selected[:args.limit]
    print(f"Selected {len(selected)} of {len(source)} upstream releases", flush=True)
    if args.dry_run:
        for item in selected:
            print(item["tag_name"])
        return 0
    target = releases(TARGET)
    latest_source_tag = json.loads(run("gh", "api", f"repos/{UPSTREAM}/releases/latest"))["tag_name"]
    target_by_source = {copied_source(r): r for r in target if copied_source(r)}
    counts = {"published": 0, "skipped": 0, "failed": 0}
    for item in selected:
        try:
            counts[sync_one(item, target_by_source, latest_source_tag)] += 1
        except Exception as exc:
            counts["failed"] += 1
            print(f"FAILED {item['tag_name']}: {exc}", file=sys.stderr, flush=True)
    print(f"RESULT {counts}", flush=True)
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
