#!/usr/bin/env python3
"""Public CLI: project/asset/experience tools + upstream production transactions."""

from pathlib import Path
import argparse
import json
import sys
import workspace as w
import production_tool as engine


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "init",
            "resume",
            "check",
            "prepare",
            "confirm",
            "run",
            "collect",
            "status",
            "import",
            "accept-media",
            "add-version",
            "impact",
            "case",
            "promote",
            "supersede",
            "export",
            "adapter-config",
        ],
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--title", default="未命名作品")
    parser.add_argument("--job-id")
    parser.add_argument("--confirmation")
    parser.add_argument("--adapter-config", type=Path)
    parser.add_argument("--target")
    parser.add_argument("--origin")
    parser.add_argument("--purpose")
    parser.add_argument("--record")
    parser.add_argument("--review")
    parser.add_argument("--asset")
    parser.add_argument("--case")
    parser.add_argument("--old")
    parser.add_argument("--new")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--episode", action="append")
    a = parser.parse_args(argv)
    root = a.project.resolve()
    cmd = a.command
    if cmd == "init":
        result = w.init(root, a.title)
    elif cmd == "resume":
        from resume import recover

        if a.episode and len(a.episode) != 1:
            raise ValueError("resume 最多指定一个 --episode")
        result = recover(root, a.episode[0] if a.episode else None)
    elif cmd == "check":
        result = w.check(root)
        print(w.dump(result))
        return 0 if result["ok"] else 1
    elif cmd == "prepare":
        result = engine.prepare_job(root, a.file)
    elif cmd == "confirm":
        result = engine.confirm_job(root, job_id=a.job_id, confirmation=a.confirmation)
    elif cmd in ("run", "collect"):
        result = (engine.run_job if cmd == "run" else engine.collect_job)(
            root, job_id=a.job_id, adapter_config=a.adapter_config
        )
        job = engine._read_job(root, a.job_id)
        for target in job["outputs"]:
            media = w.safe(root, target)
            data = {
                "path": target,
                "sha256": w.digest(media),
                "origin": f"job:{a.job_id}",
                "purpose": job["modality"],
                "status": "candidate",
                "review": None,
            }
            if job["modality"] == "tts":
                data["duration_seconds"] = w.duration(media)
            w.write_block(
                w.safe(root, target + ".md"), "生成结果，待审", "video-media", data
            )
    elif cmd == "status":
        result = engine.job_status(root, job_id=a.job_id)
    elif cmd == "import":
        result = w.import_media(root, a.file, a.target, a.origin, a.purpose)
    elif cmd == "accept-media":
        result = w.accept_media(root, a.record, a.review)
    elif cmd == "add-version":
        result = w.add_version(root, a.file)
    elif cmd == "impact":
        result = w.impact(root, a.asset)
    elif cmd == "case":
        result = w.record_case(root, json.loads(a.file.read_text()))
    elif cmd == "promote":
        result = w.promote(root, a.case, json.loads(a.file.read_text()))
    elif cmd == "supersede":
        result = w.supersede(root, a.old, a.new)
    elif cmd == "export":
        result = w.export(
            root, a.out, a.episode or [p.parent.name for p in w.episodes(root)]
        )
    else:
        if a.out is None or a.out.resolve().is_relative_to(root):
            raise ValueError("adapter-config --out 必须在作品项目之外")
        if a.out.exists():
            raise FileExistsError(a.out)
        result = {
            "adapters": {
                "aliyun": {
                    "command": [
                        sys.executable,
                        str(Path(__file__).with_name("aliyun_adapter.py")),
                    ],
                    "timeout_seconds": 900,
                }
            }
        }
        a.out.write_text(w.dump(result))
    print(w.dump(result))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
