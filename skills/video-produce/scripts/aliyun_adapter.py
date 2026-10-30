#!/usr/bin/env python3
"""Official Wan/Qwen adapter for the existing confirmed-production engine."""

from __future__ import annotations
import base64
import json
import mimetypes
import os
import re
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, quote, urlparse
from urllib.request import Request, urlopen
from workspace import duration, safe


def request(url, method="GET", body=None, headers=None, binary=False):
    headers = dict(headers or {})
    if isinstance(body, dict):
        body = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    try:
        with urlopen(
            Request(url, data=body, headers=headers, method=method), timeout=60
        ) as response:
            data = response.read()
    except HTTPError as exc:
        # Do not echo signed URLs, credentials or provider response bodies.
        raise RuntimeError(
            f"provider HTTP {exc.code}; verify region/model/credentials"
        ) from None
    return data if binary else json.loads(data)


def save_handle(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with open(temporary, "w") as f:
        json.dump(value, f)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def endpoint(connection):
    region = connection["region"]
    explicit = connection.get("endpoint")
    if explicit:
        parsed = urlparse(explicit)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or not parsed.hostname.endswith(".aliyuncs.com")
            or region not in parsed.hostname
        ):
            raise ValueError(
                "endpoint must be official HTTPS and match configured region"
            )
        return explicit.rstrip("/")
    workspace = connection.get("workspace_id")
    if not workspace or not re.fullmatch(r"[A-Za-z0-9-]+", workspace):
        raise ValueError("configure production.workspace_id before execution")
    return f"https://{workspace}.{region}.maas.aliyuncs.com/api/v1"


def upload(path, model, region, headers, http=request):
    hosts = {
        "ap-southeast-1": "dashscope-intl.aliyuncs.com",
        "cn-beijing": "dashscope.aliyuncs.com",
    }
    if region not in hosts:
        raise ValueError(
            "temporary upload currently supports Singapore/Beijing; no region fallback"
        )
    policy = http(
        "https://"
        + hosts[region]
        + "/api/v1/uploads?"
        + urlencode({"action": "getPolicy", "model": model}),
        headers=headers,
    )["data"]
    key = policy["upload_dir"] + "/" + uuid.uuid4().hex + path.suffix
    fields = {
        "OSSAccessKeyId": policy["oss_access_key_id"],
        "policy": policy["policy"],
        "Signature": policy["signature"],
        "key": key,
        "x-oss-object-acl": policy["x_oss_object_acl"],
        "x-oss-forbid-overwrite": policy["x_oss_forbid_overwrite"],
        "success_action_status": "200",
    }
    boundary = uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        )
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="media{path.suffix}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
        + path.read_bytes()
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    http(
        policy["upload_host"],
        method="POST",
        body=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        binary=True,
    )
    return "oss://" + key


def execute(job, http=request, sleep=time.sleep):
    p = job["parameters"]
    model = p["model"]
    modality = job["modality"]
    if modality not in ("video", "tts"):
        raise ValueError("official adapter handles video and tts only")
    if model not in (
        ("wan3.0-video", "wan3.0-video-prime")
        if modality == "video"
        else ("qwen-audio-3.0-tts-plus",)
    ):
        raise ValueError("unsupported model; no silent fallback")
    if len(job["outputs"]) != 1:
        raise ValueError("one provider call produces one output")
    base = endpoint(p["connection"])
    key = os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        raise ValueError("DASHSCOPE_API_KEY is required")
    headers = {"Authorization": "Bearer " + key}
    collecting = job.get("collect_provider_job_id")
    handle_path = job.get("handle_path")
    if modality == "tts" and collecting:
        handle = json.loads(Path(handle_path).read_text())
        url = handle.get("audio_url")
        if not url:
            raise ValueError("TTS result unavailable; no automatic resynthesis")
        task = collecting
    elif modality == "tts":
        if not handle_path:
            raise ValueError("engine handle_path required")
        save_handle(handle_path, {"submission_state": "unknown", "modality": "tts"})
        payload = {
            "model": model,
            "input": {
                "text": job["prompt"],
                "voice": p["voice"],
                "format": "wav",
                "sample_rate": p.get("sample_rate", 24000),
            },
        }
        for field in ("instruction", "rate", "pitch", "language_hints", "hot_fix"):
            if field in p:
                payload["input"][field] = p[field]
        result = http(
            base + "/services/audio/tts/SpeechSynthesizer",
            method="POST",
            body=payload,
            headers=headers,
        )
        if result.get("code"):
            save_handle(handle_path, {"submission_state": "rejected"})
            raise RuntimeError(
                "TTS rejected; inspect model availability and parameters"
            )
        url = result["output"]["audio"]["url"]
        # Engine caps provider IDs: retain a short task ID and URL in the handle.
        task = "tts:" + str(result.get("request_id", uuid.uuid4().hex))
        save_handle(
            handle_path,
            {
                "provider_job_id": task,
                "audio_url": url,
                "submission_state": "submitted",
            },
        )
    else:
        task = collecting
        if not task:
            media = []
            for item in p.get("media", []):
                path = safe(Path(job["project_root"]), item["path"])
                if item["type"] in ("first_frame", "last_frame", "reference_image"):
                    url = (
                        "data:"
                        + str(mimetypes.guess_type(path.name)[0])
                        + ";base64,"
                        + base64.b64encode(path.read_bytes()).decode()
                    )
                else:
                    url = upload(path, model, p["connection"]["region"], headers, http)
                media.append({"type": item["type"], "url": url})
            parameters = {
                k: p[k]
                for k in (
                    "duration",
                    "resolution",
                    "ratio",
                    "audio",
                    "seed",
                    "prompt_extend",
                    "watermark",
                )
                if k in p
            }
            payload = {
                "model": model,
                "input": {"prompt": job["prompt"], "media": media},
                "parameters": parameters,
            }
            save_handle(
                handle_path, {"submission_state": "unknown", "modality": "video"}
            )
            result = http(
                base + "/services/aigc/video-generation/video-synthesis",
                method="POST",
                body=payload,
                headers={
                    **headers,
                    "X-DashScope-Async": "enable",
                    "X-DashScope-OssResourceResolve": "enable",
                },
            )
            if result.get("code"):
                save_handle(handle_path, {"submission_state": "rejected"})
                raise RuntimeError(
                    "Wan rejected; inspect model availability and parameters"
                )
            task = result["output"]["task_id"]
            save_handle(
                handle_path, {"provider_job_id": task, "submission_state": "submitted"}
            )
        for _ in range(40):
            result = http(base + "/tasks/" + quote(task, safe=""), headers=headers)[
                "output"
            ]
            status = result["task_status"]
            if status == "SUCCEEDED":
                url = result["video_url"]
                break
            if status in ("FAILED", "CANCELED", "UNKNOWN"):
                raise RuntimeError(f"provider task {status}; no automatic resubmission")
            sleep(15)
        else:
            raise TimeoutError("task still pending; use collect")
    dest = Path(job["output_root"]) / (
        "result.wav" if modality == "tts" else "result.mp4"
    )
    dest.write_bytes(http(url, binary=True))
    response = {
        "provider_job_id": task,
        "outputs": [{"target": job["outputs"][0], "source": str(dest)}],
    }
    if modality == "tts":
        response["duration_seconds"] = duration(dest)
    return response


def main():
    job = json.load(sys.stdin)
    result = execute(job)
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
