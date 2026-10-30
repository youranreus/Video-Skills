#!/usr/bin/env python3
"""Create ungenerated two-episode trial materials, never fake accepted media."""

from pathlib import Path
import argparse
import sys

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "skills/video-produce/scripts")
)
import workspace as w


def create(root):
    w.init(root, "林澄：控制室巡检")
    (root / "项目开发/创作简报.md").write_text(
        "# 创作简报\n\n虚构巡检员林澄在控制室确认异常。对白镜头表现冷静汇报，动作镜头表现迅速转身擦碰门框；右袖破损跨集保持。16:9，中文对白，无自动质量重试。\n"
    )
    (root / "项目开发/人物与关系.md").write_text(
        "# 人物\n\n林澄是经验丰富的巡检员，目标是确认异常来源；保持冷静并不代表毫无压力。通过停顿和行动呈现，不让角色解释设定。\n"
    )
    for key, description in [
        ("CHAR-LIN", "成年巡检员，深灰工作服，外观和声线均待用户选定"),
        ("LOC-ROOM", "控制室，固定门框与操作台位置，场景参考待制作"),
    ]:
        spec = root / "输入" / f"{key}-候选.md"
        w.write_block(
            spec,
            key,
            "video-version",
            {
                "id": key,
                "version": "v001",
                "status": "candidate",
                "description": description,
                "files": [],
            },
        )
        w.add_version(root, spec)
    refs = ["CHAR-LIN@v001", "LOC-ROOM@v001"]
    action_media = [
        {
            "path": f"剧集/EP001/制作成果/images/action-{x}.png",
            "record": f"剧集/EP001/制作成果/images/action-{x}.png.md",
            "type": t,
        }
        for x, t in [("start", "first_frame"), ("end", "last_frame")]
    ]
    dialogue_media = [
        {
            "path": "剧集/EP001/制作成果/images/dialogue.png",
            "record": "剧集/EP001/制作成果/images/dialogue.png.md",
            "type": "reference_image",
        },
        {
            "path": "剧集/EP001/制作成果/audio/LINE-EP001-001-v001.wav",
            "record": "剧集/EP001/制作成果/audio/LINE-EP001-001-v001.wav.md",
            "type": "reference_audio",
        },
    ]
    prompts = {
        "MOTION-EP001-001": "林澄站在操作台前，面部身份与构图参考 Image 1。用 Audio 1 的音色平静说：“区域已经确认。”说话时口型同步，其他时间自然呼吸。固定中近景，无配乐和字幕。",
        "MOTION-EP001-002": "从首帧开始，林澄听见右侧门外声响，迅速转身，右袖擦碰门框撕开一道小口，重心稳定落到尾帧位置。动作连续、实时速度，无对白，无配乐。",
    }
    for ep in ("EP001", "EP002"):
        folder = root / "剧集" / ep
        folder.mkdir(parents=True)
        (folder / "剧本.md").write_text(
            f"# {ep} 控制室巡检\n\n## {ep}-SC001 内 · 控制室 · 日\n林澄：区域已经确认。\n"
            + (
                "林澄迅速转身，右袖擦碰门框后破损。\n"
                if ep == "EP001"
                else "林澄带着右袖破损的工作服继续检查。\n"
            )
        )
        before = "完好" if ep == "EP001" else "破损"
        w.write_block(
            folder / "视觉设定.md",
            ep + " 本集资产",
            "video-episode",
            {
                "assets": refs,
                "entry": {"CHAR-LIN.sleeve": before},
                "exit": {"CHAR-LIN.sleeve": "破损"},
                "deliverables": [],
            },
            "所有资产仍待选型，不能据此投产。",
        )
        shots = []
        if ep == "EP001":
            shots = [
                {
                    "id": "SHOT-EP001-001",
                    "duration": 6,
                    "start": {"CHAR-LIN.sleeve": "完好"},
                    "end": {"CHAR-LIN.sleeve": "完好"},
                    "media": dialogue_media,
                },
                {
                    "id": "SHOT-EP001-002",
                    "duration": 5,
                    "start": {"CHAR-LIN.sleeve": "完好"},
                    "changes": {
                        "CHAR-LIN.sleeve": {
                            "before": "完好",
                            "after": "破损",
                            "cause": "EP001-SC001 擦碰门框",
                        }
                    },
                    "end": {"CHAR-LIN.sleeve": "破损"},
                    "media": action_media,
                },
            ]
        else:
            shots = [
                {
                    "id": "SHOT-EP002-001",
                    "duration": 5,
                    "start": {"CHAR-LIN.sleeve": "破损"},
                    "end": {"CHAR-LIN.sleeve": "破损"},
                    "media": [],
                }
            ]
        w.write_block(
            folder / "分镜.md",
            ep + " 分镜",
            "video-shots",
            shots,
            "镜长为草案。先生成并试听对白，必要时更新镜长。",
        )
        (folder / "图片提示词.md").write_text(
            f"# {ep} 图片提示词\n\n## IMG-{ep}-ROOM · 控制室\n### 可复制提示词\n> 横屏16:9，写实控制室，操作台在左，唯一门框在右，柔和日光，空间布局清晰。\n"
        )
        w.write_block(
            folder / "配音单.md",
            ep + " 配音单",
            "video-lines",
            [
                {
                    "id": f"LINE-{ep}-001",
                    "script": f"剧集/{ep}/剧本.md",
                    "text": "区域已经确认。",
                    "voice_asset": "CHAR-LIN@v001",
                    "instruction": "普通话，平静清晰，句末自然收住。",
                    "audio": None,
                }
            ],
        )
        inputs = {}
        if ep == "EP001":
            inputs = {
                key: {
                    "assets": refs,
                    "duration": 6 if key.endswith("001") else 5,
                    "media": dialogue_media if key.endswith("001") else action_media,
                }
                for key in prompts
            }
        text = f"# {ep} 视频提示词\n\n```video-inputs\n" + w.dump(inputs) + "\n```\n"
        if ep == "EP001":
            for key, prompt in prompts.items():
                text += f"\n## {key} · 试片\n\n### 可复制提示词\n> {prompt}\n"
        (folder / "视频提示词.md").write_text(text)
    packs = root.parent / "试片"
    packs.mkdir()
    for name, key in [("对白", "MOTION-EP001-001"), ("动作", "MOTION-EP001-002")]:
        folder = packs / name
        folder.mkdir()
        data = {
            "job_id": name.replace("对白", "DIALOGUE").replace("动作", "ACTION")
            + "-001",
            "modality": "video",
            "adapter": "aliyun",
            "prompt": prompts[key],
            "source": "剧集/EP001/视频提示词.md",
            "source_entry": key,
            "outputs": [f"剧集/EP001/制作成果/videos/{key}-v001.mp4"],
            "parameters": {
                "mode": "reference" if name == "对白" else "first_last_frame",
                "duration": 6 if name == "对白" else 5,
                "resolution": "720P",
                "audio": name == "对白",
                "assets": refs,
                "media": dialogue_media if name == "对白" else action_media,
            },
        }
        (folder / "video-job.json").write_text(w.dump(data) + "\n")
        (folder / "预览.md").write_text(
            f"# {name}试片：尚未生成\n\n模型 wan3.0-video；{data['parameters']['duration']}秒，720P，16:9。\n\n提示词：{prompts[key]}\n\n缺口：采用的角色/场景资产版本、实际参考图及验收记录、同地域工作空间和凭据。"
            + (
                "还需选定声线，生成对白、回听、测时，并登记音频。"
                if name == "对白"
                else "需要完整首帧和尾帧，两者不得混入音频。"
            )
            + "\n\n验收：身份与场景连续、动作/口型符合意图；接口成功不代表质量通过。\n"
        )
    tts = {
        "job_id": "TTS-001",
        "modality": "tts",
        "adapter": "aliyun",
        "prompt": "区域已经确认。",
        "source": "剧集/EP001/配音单.md",
        "outputs": ["剧集/EP001/制作成果/audio/LINE-EP001-001-v001.wav"],
        "parameters": {
            "assets": ["CHAR-LIN@v001"],
            "line_id": "LINE-EP001-001",
            "instruction": "普通话，平静清晰，句末自然收住。",
        },
    }
    (packs / "对白/tts-job.json").write_text(w.dump(tts) + "\n")
    audition_line = {
        "id": "LINE-AUDITION-001",
        "script": "剧集/EP001/剧本.md",
        "text": "区域已经确认。",
        "voice_asset": None,
        "audition": True,
        "instruction": "普通话，平静清晰，句末自然收住。",
        "audio": None,
    }
    sheet = root / "剧集/EP001/配音单.md"
    lines = w.block(sheet, "video-lines")
    lines.append(audition_line)
    w.write_block(sheet, "EP001 配音与试听", "video-lines", lines)
    audition = dict(
        tts,
        job_id="AUDITION-001",
        outputs=["剧集/EP001/制作成果/audio/audition-v001.wav"],
        parameters={
            "audition": True,
            "voice": None,
            "line_id": "LINE-AUDITION-001",
            "instruction": audition_line["instruction"],
        },
    )
    (packs / "对白/audition-job.json").write_text(w.dump(audition) + "\n")
    return root


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("project", type=Path)
    a = p.parse_args()
    print(create(a.project.resolve()))
