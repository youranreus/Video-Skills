"""Read-only recovery from creative documents and existing production transactions."""

from pathlib import Path
import json
import hashlib
import re
import workspace as w
import production_tool as engine

STAGES = [
    ("剧本.md", "video-write"),
    ("视觉设定.md", "video-assets"),
    ("分镜.md", "video-storyboard"),
    ("图片提示词.md", "video-images"),
    ("配音单.md", "video-voice"),
    ("视频提示词.md", "video-motion"),
    ("剪辑单.md", "video-edit"),
]
MEDIA = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".wav", ".mp3"}


def review_digest(text):
    body = re.sub(r"```video-review\s*\n.*?\n```", "", text, flags=re.S).strip()
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def recover(project, episode=None):
    root = Path(project).expanduser().resolve()
    config = json.loads(w.safe(root, "short-drama.json").read_text())
    if config.get("video_skills_format") != w.FORMAT:
        raise ValueError("不是 Video-Skills v1 作品；不会自动初始化或迁移")
    if episode and not re.fullmatch(r"EP\d{3,}", episode):
        raise ValueError("非法集号")
    report = {
        "project": str(root),
        "title": config.get("title"),
        "scope": episode or "all",
        "read_only": True,
        "provider_state": "not_queried",
        "completed": [],
        "pending_review": [],
        "blockers": [],
        "episodes": [],
        "assets": [],
        "jobs": [],
        "in_flight": [],
        "next_actions": [],
    }

    def issue(path, message):
        skill = "video-workflow"
        if "资产" in message or "视觉设定" in str(path):
            skill = "video-assets"
        elif "job" in str(path) or "任务" in message or ".short-drama" in str(path):
            skill = "video-produce"
        elif "媒体" in message:
            skill = "video-review"
        report["blockers"].append(
            {"path": str(path), "reason": message, "skill": skill}
        )

    # Do not read files outside the requested project via symlinked directories.
    for top in ("资产库", "剧集", "项目开发", "规则", "经验"):
        w.safe(root, top)
    folders = sorted(p for p in (root / "剧集").glob("EP*") if p.is_dir())
    if episode:
        folders = [p for p in folders if p.name == episode]
        if not folders:
            raise ValueError("指定剧集不存在")
    for folder in folders:
        w.safe(root, folder.relative_to(root))
        entry = {"episode": folder.name, "documents": []}
        for name, skill in STAGES:
            rel = (folder / name).relative_to(root).as_posix()
            item = {"path": rel, "skill": skill, "state": "missing"}
            try:
                path = w.safe(root, rel)
                if path.is_file() and path.read_text().strip():
                    item["state"] = "present_acceptance_unknown"
                    review = w.block(path, "video-review", required=False)
                    if review:
                        if review.get("status") not in (
                            "accepted",
                            "revise",
                            "pending",
                        ) or not review.get("evidence"):
                            raise ValueError("验收声明缺少有效状态或依据")
                        if review.get("content_sha256") != review_digest(
                            path.read_text()
                        ):
                            item.update(
                                state="present_acceptance_unknown",
                                reason="验收记录未绑定当前正文或正文已修改",
                            )
                        else:
                            item.update(
                                state=review["status"], evidence=review["evidence"]
                            )
                    if item["state"] == "accepted":
                        report["completed"].append(item)
                    else:
                        report["pending_review"].append(item)
            except (ValueError, OSError, KeyError, TypeError) as e:
                item["state"] = "invalid"
                issue(rel, str(e))
            entry["documents"].append(item)
        visual = folder / "视觉设定.md"
        if visual.is_file():
            try:
                data = w.block(w.safe(root, visual.relative_to(root)), "video-episode")
                entry.update(
                    asset_refs=data["assets"],
                    entry_state=data.get("entry"),
                    exit_state=data.get("exit"),
                )
                for ref in data["assets"]:
                    try:
                        spec, files = w.asset(root, ref)
                        report["assets"].append(
                            {"ref": ref, "state": "accepted", "files": files}
                        )
                    except (ValueError, OSError, KeyError, TypeError) as e:
                        issue(visual.relative_to(root), str(e))
            except (ValueError, OSError, KeyError, TypeError) as e:
                issue(visual.relative_to(root), str(e))
        report["episodes"].append(entry)
    # Include unattached asset drafts, without turning them into required work.
    try:
        for key, (path, data) in w.catalog(root).items():
            for version, relative in data["versions"].items():
                if any(x["ref"] == key + "@" + version for x in report["assets"]):
                    continue
                spec, _ = w.asset(root, key + "@" + version, accepted=False)
                report["assets"].append(
                    {
                        "ref": key + "@" + version,
                        "state": spec["status"],
                        "path": relative,
                        "referenced": False,
                    }
                )
    except (ValueError, OSError, KeyError, TypeError) as e:
        issue("资产库", str(e))
    for base in [root / "资产库", *[p / "制作成果" for p in folders]]:
        for path in sorted(base.rglob("*")):
            if path.suffix.lower() not in MEDIA or not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            try:
                w.safe(root, rel)
                record = rel + ".md"
                metadata = w.safe(root, record)
                if not metadata.exists():
                    report["pending_review"].append(
                        {"path": rel, "state": "unregistered", "skill": "video-review"}
                    )
                    continue
                data = w.block(metadata, "video-media")
                if data.get("path") != rel or data.get("sha256") != w.digest(path):
                    raise ValueError("媒体已变化或登记路径不符")
                state = data.get("status")
                if state not in ("accepted", "candidate", "rejected"):
                    raise ValueError("未知媒体状态")
                item = {"path": rel, "state": state, "skill": "video-review"}
                if state == "accepted":
                    report["completed"].append(item)
                elif state == "candidate":
                    report["pending_review"].append(item)
            except (ValueError, OSError, KeyError, TypeError) as e:
                issue(rel, str(e))
    # Scan all jobs, even when a single episode was requested: another episode may still be billed.
    try:
        names = engine._metadata_json_names(root, ("jobs",))
    except (ValueError, OSError) as e:
        issue(".short-drama/production/jobs", str(e))
        names = []
    for name in names:
        try:
            doc = engine._metadata_read_json(
                root, ("jobs",), name, maximum=engine.MAX_JOB_BYTES
            )
            job = engine._validate_stored_job(root, doc)
            job_id = job["job_id"]
            if name != engine._job_key(job_id) + ".json":
                raise ValueError("任务文件名不匹配")
            history = engine._read_run_history(root, job_id)
            current = engine._inputs_current(root, job)
            expected = job.get("parameters", {}).get("config_sha256")
            if expected and expected != w.digest(root / "short-drama.json"):
                current = False
            state = "needs_confirmation"
            try:
                receipt = engine._metadata_read_json(
                    root,
                    ("confirmations",),
                    engine._job_key(job_id) + ".json",
                    maximum=engine.MAX_RUN_RECORD_BYTES,
                )
                if receipt.get("fingerprint") == job["fingerprint"] and not receipt.get(
                    "consumed_at"
                ):
                    state = "confirmed"
            except FileNotFoundError:
                pass
            if history:
                state = history[-1]["status"]
            item = {
                "job_id": job_id,
                "modality": job["modality"],
                "source": job.get("source"),
                "outputs": job["outputs"],
                "state": state,
                "inputs_current": current,
            }
            report["jobs"].append(item)
            has_unfinished = False
            for run in history:
                if run["status"] == "succeeded":
                    for output in run.get("outputs", []):
                        path = w.safe(root, output["path"])
                        if not path.is_file() or w.digest(path) != output["sha256"]:
                            issue(output["path"], "已完成任务的输出缺失或已变动")
                    continue
                handle = {}
                try:
                    handle = engine._metadata_read_json(
                        root,
                        ("handles", engine._job_key(job_id)),
                        run["run_id"] + ".json",
                        maximum=engine.MAX_RUN_RECORD_BYTES,
                    )
                except FileNotFoundError:
                    pass
                provider_id = run.get("provider_job_id") or handle.get(
                    "provider_job_id"
                )
                unknown = handle.get("submission_state") == "unknown"
                if provider_id or unknown or run["status"] == "running":
                    pending = {
                        "job_id": job_id,
                        "run_id": run["run_id"],
                        "inputs_current": current,
                        "state": "recoverable" if provider_id else "submission_unknown",
                        "action": "collect" if provider_id else "investigate",
                        "provider_status": "unknown_until_queried",
                    }
                    report["in_flight"].append(pending)
                    has_unfinished = True
            if state == "failed" and not has_unfinished:
                issue(job_id, "尝试失败且无可取回句柄；检查原因，新尝试需要明确授权")
            if not current:
                issue(job_id, "输入或配置已变化；旧任务仍需先核查，不能重投")
        except (ValueError, OSError, KeyError, TypeError) as e:
            issue(name, str(e))
    # Structural checks are advisory for partial projects; never confuse missing future stages with lost work.
    try:
        report["structural_check"] = w.check(root)
    except (ValueError, OSError, KeyError, TypeError) as e:
        report["structural_check"] = {"ok": False, "errors": [str(e)]}
    if folders and all(
        (p / "视觉设定.md").is_file() and (p / "分镜.md").is_file() for p in folders
    ):
        for error in report["structural_check"].get("errors", []):
            if any(token in error for token in ("状态", "起点", "终态", "对白超出")):
                report["blockers"].append(
                    {"path": "剧集", "reason": error, "skill": "video-storyboard"}
                )
    actions = report["next_actions"]
    for task in report["in_flight"]:
        actions.append(
            {
                "skill": "video-produce",
                "action": task["action"],
                "job_id": task["job_id"],
                "reason": "先恢复或核查已有付费尝试，禁止自动重新提交",
            }
        )
    if report["blockers"]:
        actions.append(
            {
                "skill": report["blockers"][0]["skill"],
                "action": "resolve_blockers",
                "path": report["blockers"][0]["path"],
                "reason": report["blockers"][0]["reason"],
            }
        )
    if not actions:
        prepared = next(
            (
                j
                for j in report["jobs"]
                if j["state"] in ("confirmed", "needs_confirmation")
            ),
            None,
        )
        if prepared:
            actions.append(
                {
                    "skill": "video-produce",
                    "action": "review_prepared_job",
                    "job_id": prepared["job_id"],
                    "reason": "读取既有预览和授权范围，不因恢复命令自动提交",
                }
            )
    if not actions:
        for ep in report["episodes"]:
            docs = ep["documents"]
            script = docs[0]
            if script["state"] == "missing":
                actions.append(
                    {
                        "skill": "video-write",
                        "action": "continue",
                        "episode": ep["episode"],
                        "reason": "本集尚无剧本",
                    }
                )
                break
            # Existing texts are reviewed before rewriting or claiming approval.
            pending = next(
                (
                    d
                    for d in reversed(docs)
                    if d["state"] in ("present_acceptance_unknown", "pending", "revise")
                ),
                None,
            )
            if pending:
                actions.append(
                    {
                        "skill": pending["skill"],
                        "action": "review_existing",
                        "path": pending["path"],
                        "reason": "先读已有成果与验收依据，确认后继续；不从头重做",
                    }
                )
                break
            missing = next(
                (
                    d
                    for d in docs
                    if d["state"] == "missing"
                    and d["path"].split("/")[-1] not in ("图片提示词.md", "配音单.md")
                ),
                None,
            )
            if missing:
                actions.append(
                    {
                        "skill": missing["skill"],
                        "action": "continue",
                        "path": missing["path"],
                        "reason": "进入下一个缺失的必要阶段",
                    }
                )
                break
        if not actions and report["pending_review"]:
            actions.append(
                {
                    "skill": "video-review",
                    "action": "review_media",
                    "reason": "审看已生成或未登记素材，不重新生成",
                }
            )
        if not actions and not folders:
            actions.append(
                {
                    "skill": "video-develop",
                    "action": "inspect_existing_development",
                    "reason": "先读取已有项目开发与输入材料，再建立所需剧集",
                }
            )
        if not actions:
            actions.append(
                {
                    "skill": "video-workflow",
                    "action": "verify_delivery_scope",
                    "reason": "已读资料无明显缺口；核对交付范围，不推断整片已验收",
                }
            )
    return report
