#!/usr/bin/env python3
"""Install/uninstall the complete video-* bundle without overwriting user files."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def hashes(folder):
    return {
        p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in folder.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    }


def install(target):
    folders = sorted((ROOT / "skills").glob("video-*"))
    if target.is_symlink():
        raise ValueError("installation root may not be a symlink")
    for source in folders:
        if (target / source.name).exists():
            raise FileExistsError(target / source.name)
    target.mkdir(parents=True, exist_ok=True)
    installed = []
    try:
        for source in folders:
            dest = target / source.name
            shutil.copytree(
                source, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
            )
            installed.append(dest)
            (dest / ".video-skills-install.json").write_text(json.dumps(hashes(dest)))
    except Exception:
        for dest in installed:
            shutil.rmtree(dest)
        raise
    return len(installed)


def uninstall(target):
    owned = []
    for folder in sorted(target.glob("video-*")):
        marker = folder / ".video-skills-install.json"
        if not marker.is_file() or folder.is_symlink():
            continue
        expected = json.loads(marker.read_text())
        actual = hashes(folder)
        actual.pop(marker.name, None)
        if expected != actual:
            raise ValueError(f"安装后已修改，保留：{folder}")
        owned.append(folder)
    for folder in owned:
        shutil.rmtree(folder)
    return len(owned)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["install", "uninstall"])
    p.add_argument("--target", type=Path, required=True)
    a = p.parse_args()
    print((install if a.action == "install" else uninstall)(a.target))
