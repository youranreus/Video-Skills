from pathlib import Path
import json
import struct
import sys
import wave
import zlib

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "skills/video-produce/scripts")
)
import workspace as w


def fixture(root):
    w.init(root, "离线夹具：巡检员林澄")
    config = json.loads((root / "short-drama.json").read_text())
    config["production"]["workspace_id"] = "offline-fixture"
    (root / "short-drama.json").write_text(w.dump(config))
    raw = root / "输入/synthetic.png"

    def chunk(t, b):
        return (
            struct.pack("!I", len(b))
            + t
            + b
            + struct.pack("!I", zlib.crc32(t + b) & 0xFFFFFFFF)
        )

    raw.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!2I5B", 256, 256, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((b"\0" + b"\x80\x80\x80" * 256) * 256))
        + chunk(b"IEND", b"")
    )
    media = []
    for name in ("start", "end"):
        m = w.import_media(
            root,
            raw,
            f"剧集/EP001/制作成果/images/{name}.png",
            "synthetic-test",
            "模拟帧，仅测试",
        )
        w.accept_media(root, m["record"], "离线夹具，非创作验收")
        media.append(m)
    audio = root / "输入/silence.wav"
    with wave.open(str(audio), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(8000)
        f.writeframes(b"\0\0" * 16000)
    voice = w.import_media(
        root,
        audio,
        "资产库/角色/CHAR-LIN/声音/试听/synthetic.wav",
        "synthetic-test",
        "仅测试音轨",
    )
    w.accept_media(root, voice["record"], "离线夹具，非真实声线验收")
    for key in ("CHAR-LIN", "LOC-ROOM"):
        spec = root / "输入" / f"{key}.md"
        data = {
            "id": key,
            "version": "v001",
            "status": "accepted",
            "description": "合成测试资产，不代表实际角色已验收",
            "files": [],
        }
        if key == "CHAR-LIN":
            data["voice"] = {
                "model": "qwen-audio-3.0-tts-plus",
                "id": "fixture-voice",
                "audition": voice["path"],
                "pronunciation": {"林澄": "lin2 cheng2"},
            }
            data["files"] = [
                {"path": voice["path"], "sha256": w.digest(w.safe(root, voice["path"]))}
            ]
        w.write_block(spec, key, "video-version", data)
        w.add_version(root, spec)
    for ep in ("EP001", "EP002"):
        folder = root / "剧集" / ep
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "剧本.md").write_text(
            f"# {ep} 巡检\n\n## {ep}-SC001 内 · 控制室 · 日\n林澄：区域已经确认。\n第一集最后一次碰撞损坏右袖，后续保持。\n"
        )
        before = "intact" if ep == "EP001" else "torn"
        epdata = {
            "assets": ["CHAR-LIN@v001", "LOC-ROOM@v001"],
            "entry": {"CHAR-LIN.sleeve": before},
            "exit": {"CHAR-LIN.sleeve": "torn"},
            "deliverables": [],
        }
        w.write_block(
            folder / "视觉设定.md", ep + " 资产与状态", "video-episode", epdata
        )
        shot = {
            "id": f"SHOT-{ep}-001",
            "duration": 5,
            "start": {"CHAR-LIN.sleeve": before},
            "end": {"CHAR-LIN.sleeve": "torn"},
            "media": media if ep == "EP001" else [],
        }
        if ep == "EP001":
            shot["changes"] = {
                "CHAR-LIN.sleeve": {
                    "before": "intact",
                    "after": "torn",
                    "cause": f"{ep}-SC001 碰撞",
                }
            }
        w.write_block(folder / "分镜.md", ep + " 分镜", "video-shots", [shot])
        (folder / "图片提示词.md").write_text(
            f"# {ep} 图片提示词\n\n已有参考，夹具不调用生成。\n"
        )
        lines = [
            {
                "id": f"LINE-{ep}-001",
                "script": f"剧集/{ep}/剧本.md",
                "text": "区域已经确认。",
                "voice_asset": "CHAR-LIN@v001",
                "instruction": "平静、清晰",
                "audio": None,
            }
        ]
        w.write_block(folder / "配音单.md", ep + " 配音单", "video-lines", lines)
        (folder / "视频提示词.md").write_text(f"# {ep} 视频提示词\n")
    typed = [dict(media[0], type="first_frame"), dict(media[1], type="last_frame")]
    motion = "MOTION-EP001-001"
    inputs = {
        motion: {
            "media": typed,
            "assets": ["CHAR-LIN@v001", "LOC-ROOM@v001"],
            "duration": 5,
        }
    }
    source = root / "剧集/EP001/视频提示词.md"
    source.write_text(
        "# EP001 视频提示词\n\n```video-inputs\n"
        + w.dump(inputs)
        + "\n```\n\n## "
        + motion
        + " · 快速转身\n\n### 可复制提示词\n> 林澄迅速转身，右袖擦碰门框后破损，保持动作连贯。\n"
    )
    video = {
        "job_id": "ACTION-001",
        "modality": "video",
        "adapter": "aliyun",
        "prompt": "林澄迅速转身，右袖擦碰门框后破损，保持动作连贯。",
        "source": "剧集/EP001/视频提示词.md",
        "source_entry": motion,
        "outputs": ["剧集/EP001/制作成果/videos/action-v001.mp4"],
        "parameters": {
            "mode": "first_last_frame",
            "duration": 5,
            "resolution": "720P",
            "audio": False,
            "assets": inputs[motion]["assets"],
            "media": typed,
        },
    }
    tts = {
        "job_id": "TTS-001",
        "modality": "tts",
        "adapter": "aliyun",
        "prompt": "区域已经确认。",
        "source": "剧集/EP001/配音单.md",
        "outputs": ["剧集/EP001/制作成果/audio/line-v001.wav"],
        "parameters": {
            "assets": ["CHAR-LIN@v001"],
            "line_id": "LINE-EP001-001",
            "instruction": "平静、清晰",
        },
    }
    return video, tts, media
