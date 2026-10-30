#!/usr/bin/env python3
"""Render explicit audio tracks, preserving the input video and audio files."""

import argparse
import json
import subprocess
from pathlib import Path
from workspace import safe


def command(root, plan, ffmpeg="ffmpeg"):
    video = safe(root, plan["video"])
    out = safe(root, plan["output"])
    if out.exists():
        raise FileExistsError(out)
    if "/制作成果/" not in plan["output"]:
        raise ValueError("混音输出须在制作成果内")
    args = [ffmpeg, "-nostdin", "-n", "-i", str(video)]
    filters = []
    labels = []
    if plan.get("original_audio") == "keep":
        filters.append("[0:a]volume=1[a0]")
        labels.append("[a0]")
    elif plan.get("original_audio") != "replace":
        raise ValueError("明确选择 keep 或 replace，避免重复对白")
    for i, track in enumerate(plan["tracks"], 1):
        audio = safe(root, track["path"])
        if track["start"] < 0 or track.get("gain", 1) < 0:
            raise ValueError("时间或增益无效")
        args += ["-i", str(audio)]
        filters.append(
            f"[{i}:a]volume={track.get('gain', 1)},adelay={round(track['start'] * 1000)}:all=1[a{i}]"
        )
        labels.append(f"[a{i}]")
    if not labels:
        raise ValueError("至少一个音轨")
    filters.append(
        "".join(labels)
        + f"amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.95[mix]"
    )
    args += [
        "-filter_complex",
        ";".join(filters),
        "-map",
        "0:v:0",
        "-map",
        "[mix]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-t",
        str(plan["duration"]),
        str(out),
    ]
    return args


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("project", type=Path)
    p.add_argument("plan", type=Path)
    p.add_argument("--ffmpeg", default="ffmpeg")
    p.add_argument("--run", action="store_true")
    a = p.parse_args()
    plan = json.loads(a.plan.read_text())
    args = command(a.project, plan, a.ffmpeg)
    if a.run:
        safe(a.project, plan["output"]).parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(args, check=True)
    else:
        print(json.dumps(args, ensure_ascii=False))
