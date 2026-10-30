"""Video-Skills project contracts. Markdown owns creative data; engine owns jobs."""

from __future__ import annotations
import hashlib
import json
import re
import shutil
import subprocess
import wave
from pathlib import Path

FORMAT = "video-skills/1"


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe(root, value):
    root = Path(root).resolve()
    p = Path(value)
    if p.is_absolute() or ".." in p.parts or not p.parts or p.parts[0].startswith("."):
        raise ValueError(f"非法项目路径：{value}")
    target = root / p
    if not target.resolve().is_relative_to(root):
        raise ValueError(f"路径越界：{value}")
    for item in [target, *target.parents]:
        if item == root:
            break
        if item.is_symlink():
            raise ValueError(f"不接受符号链接：{value}")
    return target


def block(path, kind, required=True):
    text = path.read_text(encoding="utf-8")
    found = re.findall(r"```" + re.escape(kind) + r"\s*\n(.*?)\n```", text, re.S)
    if len(found) != 1:
        if not found and not required:
            return None
        raise ValueError(f"{path.name} 需要唯一 {kind} 数据块")
    return json.loads(found[0])


def write_block(path, title, kind, data, prose=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# {title}\n\n{prose}\n\n```{kind}\n{dump(data)}\n```\n", encoding="utf-8"
    )


def init(root, title):
    root = Path(root).resolve()
    if (root / "short-drama.json").exists():
        raise FileExistsError("项目已存在")
    root.mkdir(parents=True, exist_ok=True)
    for name in [
        "输入",
        "项目开发",
        "资产库/角色",
        "资产库/场景",
        "资产库/道具",
        "剧集",
        "规则",
        "经验/案例",
        "交付",
    ]:
        (root / name).mkdir(parents=True, exist_ok=True)
    config = {
        "schema_version": "1.0.0-draft",
        "video_skills_format": FORMAT,
        "title": title,
        "language": "zh-CN",
        "format": {"aspect_ratio": "16:9", "prompt_language": "zh-CN"},
        "production": {
            "region": "cn-beijing",
            "workspace_id": None,
            "endpoint": None,
            "video_model": "wan3.0-video",
            "tts_model": "qwen-audio-3.0-tts-plus",
            "image_mode": "builtin-or-import",
        },
    }
    (root / "short-drama.json").write_text(dump(config) + "\n")
    (root / "AGENTS.md").write_text(
        "# 作品执行约定\n\n使用 video-* 技能。先读当前任务涉及的资产版本和单集状态，再匹配规则。\n每次生成用 video-produce 的 workflow.py prepare，预览包括规则落实方式。\n复盘保存到经验/案例；已验证经验才晋升规则。创作文件只保留一份事实来源。\n采用版本不可原地覆盖；镜头续接使用已采用素材的实际尾帧。\n只有明确任务或批次获授权才执行外部生成；恢复原任务不重新提交。\n"
    )
    (root / "资产库/索引.md").write_text(
        "# 资产库\n\n尚无资产。通过 add-version 登记角色、场景或道具版本。\n"
    )
    (root / "规则/索引.md").write_text(
        "# 项目规则\n\n按阶段、模型与模式匹配 active 规则；候选经验留在经验目录。\n"
    )
    (root / "经验/索引.md").write_text(
        "# 经验\n\n案例保存到案例目录；verified 才能晋升规则，历史转述标 historical。\n"
    )
    return config


def catalog(root):
    result = {}
    for path in sorted((root / "资产库").rglob("设定.md")):
        data = block(path, "video-asset")
        key = data["id"]
        if key in result:
            raise ValueError(f"重复资产 {key}")
        if not re.fullmatch(r"(CHAR|LOC|PROP)-[A-Z0-9-]+", key):
            raise ValueError(f"非法资产 ID {key}")
        result[key] = (path, data)
    return result


def asset(root, ref, accepted=True):
    entries = catalog(root)
    key, version = ref.split("@")
    if key not in entries:
        raise ValueError(f"缺失资产 {key}")
    path, data = entries[key]
    if version not in data["versions"]:
        raise ValueError(f"缺失资产版本 {ref}")
    relative = data["versions"][version]
    spec = safe(root, relative)
    if data.get("seals", {}).get(version) != digest(spec):
        raise ValueError(f"资产版本文件被改写 {ref}")
    item = block(spec, "video-version")
    if item["id"] != key or item["version"] != version:
        raise ValueError(f"版本身份不匹配 {ref}")
    if accepted and item["status"] != "accepted":
        raise ValueError(f"资产版本未采用 {ref}")
    files = item.get("files", [])
    for f in files:
        media = safe(root, f["path"])
        if not media.is_file() or digest(media) != f["sha256"]:
            raise ValueError(f"资产媒体缺失或已变动 {f['path']}")
        if accepted:
            verify_media(
                root, {"path": f["path"], "record": f.get("record", f["path"] + ".md")}
            )
    if item.get("voice") and accepted:
        voice = item["voice"]
        if not voice.get("id") or voice.get("audition") not in [
            f["path"] for f in files
        ]:
            raise ValueError(f"声线缺少采用试听或音色 ID {ref}")
    return item, [path.relative_to(root).as_posix(), relative] + [
        entry
        for f in files
        for entry in (f["path"], f.get("record", f["path"] + ".md"))
    ]


def duration(path):
    if path.suffix.lower() == ".wav":
        with wave.open(str(path), "rb") as f:
            return f.getnframes() / f.getframerate()
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ]
    )
    return float(json.loads(out)["format"]["duration"])


def episodes(root):
    return sorted((root / "剧集").glob("EP*/视觉设定.md"))


def check(root):
    root = Path(root).resolve()
    errors, state, dependencies = [], {}, set()
    try:
        catalog(root)
        for visual in episodes(root):
            ep = block(visual, "video-episode")
            for ref in ep["assets"]:
                _, files = asset(root, ref)
                dependencies.update(files)
            for key, before in ep.get("entry", {}).items():
                if key in state and state[key] != before:
                    if key not in ep.get("entry_changes", {}):
                        errors.append(f"{visual.parent.name} 无来源状态复位：{key}")
                    else:
                        safe(root, ep["entry_changes"][key]).read_text()
                state[key] = before
            for key in ep.get("entry", {}):
                if key.split(".")[0] not in [ref.split("@")[0] for ref in ep["assets"]]:
                    errors.append(f"{visual.parent.name} 状态资产未列入引用：{key}")
            declared_entry = set(ep.get("entry", {}))
            if set(state) - declared_entry:
                errors.append(
                    f"{visual.parent.name} 未明确继承前集状态：{sorted(set(state) - declared_entry)}"
                )
            storyboard = block(visual.parent / "分镜.md", "video-shots")
            for shot in storyboard:
                if set(shot.get("start", {})) != set(state) or set(
                    shot.get("end", {})
                ) != set(state):
                    errors.append(f"{shot['id']} 起止状态覆盖不完整")
                for key, value in shot.get("start", {}).items():
                    if key in state and state[key] != value:
                        errors.append(f"{shot['id']} 起点与前态冲突：{key}")
                for key, change in shot.get("changes", {}).items():
                    if not change.get("cause") or state.get(key) != change["before"]:
                        errors.append(f"{shot['id']} 状态变化缺少来源或前态错误：{key}")
                    state[key] = change["after"]
                for key, value in shot.get("end", {}).items():
                    if key in state and state[key] != value:
                        errors.append(f"{shot['id']} 无依据终态：{key}")
                    state[key] = value
                for media in shot.get("media", []):
                    verify_media(root, media)
                if shot.get("dialogue_audio"):
                    if duration(safe(root, shot["dialogue_audio"])) > shot["duration"]:
                        errors.append(f"{shot['id']} 对白超出镜长")
            if ep.get("exit", {}) != state:
                errors.append(f"{visual.parent.name} 结束状态不完整或不一致")
    except (ValueError, KeyError, OSError) as exc:
        errors.append(str(exc))
    return {"ok": not errors, "errors": errors, "dependencies": sorted(dependencies)}


def verify_media(root, media):
    path = safe(root, media["path"])
    if not path.is_file():
        raise ValueError(f"缺少媒体 {media['path']}")
    record = block(safe(root, media["record"]), "video-media")
    if (
        record["path"] != media["path"]
        or record["status"] != "accepted"
        or record["sha256"] != digest(path)
    ):
        raise ValueError(f"参考未采用或发生变动：{media['path']}")
    return [media["path"], media["record"]]


def matching_rules(root, stage, model, mode):
    matches = []
    for path in sorted((root / "规则").glob("*.md")):
        rule = block(path, "video-rule", required=False)
        if not rule or rule["status"] != "active":
            continue
        if rule["kind"] not in ("user_constraint", "verified_experience"):
            continue
        if all(
            not rule.get(k) or value in rule[k]
            for k, value in [("stages", stage), ("models", model), ("modes", mode)]
        ):
            if not rule.get("evidence"):
                raise ValueError(f"规则缺少依据 {rule['id']}")
            for evidence in rule["evidence"]:
                safe(root, evidence).read_text()
            matches.append((path, rule))
    return matches


def prepare_parameters(root, raw):
    """Enrich before upstream fingerprinting; include every contract file in snapshots."""
    p = dict(raw.get("parameters", {}))
    config = json.loads((root / "short-drama.json").read_text())
    if config.get("video_skills_format") != FORMAT:
        return raw
    if raw.get("overwrite"):
        raise ValueError("整合版采用新输出版本，不覆盖旧素材")
    if not raw.get("source"):
        raise ValueError("生成必须绑定正式来源文档")
    modality = raw["modality"]
    if modality not in ("video", "tts", "image"):
        raise ValueError("首版只接入 image/video/tts")
    p["model"] = p.get(
        "model",
        "builtin-image"
        if modality == "image"
        else config["production"].get(
            "tts_model" if modality == "tts" else "video_model"
        ),
    )
    p["connection"] = dict(config["production"])
    refs = list(raw.get("references", []))
    # Config cannot be a normal reference in upstream; a digest is checked again on run.
    p["config_sha256"] = digest(root / "short-drama.json")
    if modality == "video":
        p.setdefault("ratio", config["format"]["aspect_ratio"])
    for ref in p.get("assets", []):
        item, files = asset(root, ref)
        refs.extend(files)
        if modality == "tts" and item.get("voice"):
            voice = item["voice"]
            if voice["model"] != p["model"]:
                raise ValueError("声线与 TTS 模型不一致")
            if p.get("voice") and p["voice"] != voice["id"]:
                raise ValueError("不得静默更换角色音色")
            p["voice"] = voice["id"]
    source_path = safe(root, raw["source"])
    if modality == "tts":
        lines = block(source_path, "video-lines")
        line = next((x for x in lines if x["id"] == p.get("line_id")), None)
        if (
            not line
            or line["text"] != raw["prompt"]
            or (
                not p.get("audition") and line["voice_asset"] not in p.get("assets", [])
            )
        ):
            raise ValueError("TTS 必须对应配音单中的台词和声线版本")
        if p.get("audition") and (
            not line.get("audition") or p.get("assets") or not p.get("voice")
        ):
            raise ValueError("TTS 必须对应配音单中的台词和声线版本")
        script = safe(root, line["script"])
        if line["text"] not in script.read_text():
            raise ValueError("配音台词不在正式剧本中")
        if p.get("instruction", "") != line.get("instruction", ""):
            raise ValueError("TTS 表演要求与配音单不一致")
        refs.append(line["script"])
    if modality == "video":
        checked = check(root)
        if not checked["ok"]:
            raise ValueError(checked["errors"])
        for ep_path in episodes(root):
            refs.extend(
                [
                    ep_path.relative_to(root).as_posix(),
                    (ep_path.parent / "分镜.md").relative_to(root).as_posix(),
                ]
            )
        specifications = block(source_path, "video-inputs")
        declared = specifications.get(raw.get("source_entry"))
        if (
            not declared
            or declared["media"] != p.get("media", [])
            or declared["assets"] != p.get("assets", [])
            or declared["duration"] != p.get("duration")
        ):
            raise ValueError("视频任务与正式来源中的输入契约不一致")
    if modality == "tts" and not p.get("voice"):
        raise ValueError("尚未选择试听音色")
    media = p.get("media", [])
    for m in media:
        refs.extend(verify_media(root, m))
    if modality == "video":
        types = [m["type"] for m in media]
        mode = p.get("mode")
        if mode == "first_last_frame" and sorted(types) != [
            "first_frame",
            "last_frame",
        ]:
            raise ValueError("首尾帧模式只允许一张首帧和一张尾帧")
        if mode == "first_frame" and types != ["first_frame"]:
            raise ValueError("首帧模式只允许一张首帧")
        if mode == "reference" and (
            not types
            or any(
                t not in ("reference_image", "reference_audio", "reference_video")
                for t in types
            )
        ):
            raise ValueError("多模态参考不可冒充严格首尾帧")
        if mode not in ("first_frame", "first_last_frame", "reference", "text") or (
            mode == "text" and types
        ):
            raise ValueError("无效生成模式")
        if not isinstance(p.get("duration"), int) or not 2 <= p["duration"] <= 30:
            raise ValueError("镜长需要 2–30 秒整数")
        for t, limit in [
            ("reference_image", 10),
            ("reference_audio", 5),
            ("reference_video", 5),
        ]:
            selected = [m for m in media if m["type"] == t]
            if len(selected) > limit:
                raise ValueError(f"{t} 数量超限")
            if t != "reference_image":
                lengths = [duration(safe(root, m["path"])) for m in selected]
                if any(n < 1 or n > 15 for n in lengths) or sum(lengths) > 15:
                    raise ValueError(f"{t} 时长超限")
                if t == "reference_video" and sum(lengths) + p["duration"] > 30:
                    raise ValueError("参考视频与输出总长超过30秒")
        if p.get("dialogue_audio"):
            audio = safe(root, p["dialogue_audio"])
            refs.append(p["dialogue_audio"])
            if duration(audio) > p["duration"]:
                raise ValueError("对白超出镜长，需要修改分镜")
    rule_report = []
    for path, rule in matching_rules(
        root, modality, p["model"], p.get("mode", modality)
    ):
        action = p.get("rule_actions", {}).get(rule["id"])
        if not action:
            raise ValueError(f"需说明规则落实方式：{rule['id']}")
        refs.append(path.relative_to(root).as_posix())
        refs.extend(rule["evidence"])
        rule_report.append(
            {"id": rule["id"], "action": action, "verification": "pending_review"}
        )
    p["applied_rules"] = rule_report
    p["contract_files"] = list(
        dict.fromkeys(
            r
            for r in refs
            if r not in raw.get("references", []) and r != raw.get("source")
        )
    )
    p["contract_files"] = list(dict.fromkeys(p["contract_files"]))
    return dict(raw, parameters=p)


def import_media(root, source, target, origin, purpose):
    dest = safe(root, target)
    if dest.exists():
        raise FileExistsError(target)
    if not (target.startswith("资产库/") or "/制作成果/" in target):
        raise ValueError("媒体应进入资产库或单集制作成果")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    record = str(Path(target).with_suffix(Path(target).suffix + ".md"))
    write_block(
        safe(root, record),
        "媒体登记",
        "video-media",
        {
            "path": target,
            "sha256": digest(dest),
            "origin": origin,
            "purpose": purpose,
            "status": "candidate",
            "review": None,
        },
    )
    return {"path": target, "record": record}


def accept_media(root, record, review):
    path = safe(root, record)
    data = block(path, "video-media")
    if digest(safe(root, data["path"])) != data["sha256"]:
        raise ValueError("媒体已变更")
    if not review.strip():
        raise ValueError("需要实际验收说明")
    data.update(status="accepted", review=review)
    write_block(path, "媒体登记", "video-media", data)


def impact(root, ref):
    return [
        p.relative_to(root).as_posix()
        for p in (root / "剧集").rglob("*.md")
        if ref in p.read_text()
    ]


def export(root, out, selected):
    root, out = root.resolve(), out.resolve()
    if out.is_relative_to(root) or out.exists():
        raise ValueError("导出目标须为项目外不存在的目录")
    checked = check(root)
    if not checked["ok"]:
        raise ValueError(checked["errors"])
    files = set()
    for name in selected:
        if not re.fullmatch(r"EP\d{3,}", name):
            raise ValueError("非法集号")
        ep = root / "剧集" / name
        if not ep.is_dir():
            raise ValueError(f"缺少剧集 {name}")
        visual = block(ep / "视觉设定.md", "video-episode")
        for ref in visual["assets"]:
            _, deps = asset(root, ref)
            files.update(deps)
        for p in ep.glob("*.md"):
            files.add(p.relative_to(root).as_posix())
        for shot in block(ep / "分镜.md", "video-shots"):
            for m in shot.get("media", []):
                files.update(verify_media(root, m))
            if shot.get("dialogue_audio"):
                files.add(shot["dialogue_audio"])
        # Only explicitly selected outputs, never the complete candidates directory.
        for media in visual.get("deliverables", []):
            files.update(verify_media(root, media))
    out.mkdir(parents=True)
    for name in sorted(files):
        src = safe(root, name)
        if (
            name.startswith("输入/")
            or name.startswith(".")
            or src.suffix in (".env", ".json")
        ):
            raise ValueError(f"禁止导出私有或运行文件 {name}")
        dest = out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    # Asset index is projected onto selected versions, avoiding dangling candidate links.
    for name in files:
        if name.startswith("资产库/") and name.endswith("/设定.md"):
            data = block(out / name, "video-asset")
            data["versions"] = {k: v for k, v in data["versions"].items() if v in files}
            write_block(out / name, data["id"], "video-asset", data)
    (out / "manifest.json").write_text(
        dump(
            {
                "format": FORMAT,
                "episodes": selected,
                "asserts_approval": False,
                "files": {name: digest(out / name) for name in sorted(files)},
            }
        )
    )
    return {"files": len(files), "output": str(out)}


def add_version(root, spec_file):
    data = block(Path(spec_file), "video-version")
    key, version = data["id"], data["version"]
    if not re.fullmatch(r"(CHAR|LOC|PROP)-[A-Z0-9-]+", key) or not re.fullmatch(
        r"v\d{3,}", version
    ):
        raise ValueError("需要稳定资产 ID 和 v001 格式版本")
    kind = {"CHAR": "角色", "LOC": "场景", "PROP": "道具"}[key.split("-")[0]]
    folder = root / "资产库" / kind / key
    index = folder / "设定.md"
    current = (
        block(index, "video-asset")
        if index.exists()
        else {"id": key, "versions": {}, "seals": {}}
    )
    if version in current["versions"]:
        raise FileExistsError("版本不可覆盖")
    for f in data.get("files", []):
        if digest(safe(root, f["path"])) != f["sha256"]:
            raise ValueError("资产媒体摘要不匹配")
    path = folder / "版本" / version / "版本.md"
    write_block(path, key + " " + version, "video-version", data)
    current["versions"][version] = path.relative_to(root).as_posix()
    current.setdefault("seals", {})[version] = digest(path)
    write_block(index, key, "video-asset", current)
    indexes = sorted((root / "资产库").rglob("设定.md"))
    (root / "资产库/索引.md").write_text(
        "# 资产库\n\n"
        + "".join(
            f"- [{block(p, 'video-asset')['id']}]({p.relative_to(root / '资产库').as_posix()})\n"
            for p in indexes
        )
    )
    return {"asset": key + "@" + version, "impact": impact(root, key + "@")}


def record_case(root, data):
    for required in (
        "id",
        "job_id",
        "inputs",
        "observation",
        "observer",
        "change_set",
        "preserve_set",
        "conclusion",
        "status",
    ):
        if required not in data:
            raise ValueError(f"案例缺少 {required}")
    if not re.fullmatch(r"[A-Z0-9-]+", data["id"]):
        raise ValueError("非法案例 ID")
    if data["status"] not in ("hypothesis", "verified", "historical", "failed"):
        raise ValueError("非法案例状态")
    path = root / "经验/案例" / f"{data['id']}.md"
    if path.exists():
        raise FileExistsError(path)
    write_block(path, data["id"], "video-case", data)
    return path.relative_to(root).as_posix()


def promote(root, case, rule):
    evidence = block(safe(root, case), "video-case")
    if evidence["status"] != "verified":
        raise ValueError("只有已验证案例可晋升规则")
    if not re.fullmatch(r"[A-Z0-9-]+", rule["id"]):
        raise ValueError("非法规则 ID")
    for k in ("stages", "models", "modes", "instruction"):
        if k not in rule:
            raise ValueError(f"规则缺少适用条件 {k}")
    path = root / "规则" / f"{rule['id']}.md"
    if path.exists():
        raise FileExistsError("新规则使用新 ID，旧规则通过 supersede 退出")
    rule = dict(rule, status="active", kind="verified_experience", evidence=[case])
    write_block(path, rule["id"], "video-rule", rule)
    return path.relative_to(root).as_posix()


def supersede(root, old, new):
    target = safe(root, new)
    replacement = block(target, "video-rule")
    if replacement["status"] != "active":
        raise ValueError("替代规则必须有效")
    path = safe(root, old)
    data = block(path, "video-rule")
    data.update(status="superseded", replaced_by=new)
    write_block(path, data["id"], "video-rule", data)
