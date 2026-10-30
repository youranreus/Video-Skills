import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import wave
from unittest.mock import patch
from factory import fixture, w
import production_tool as engine
import aliyun_adapter as adapter


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.video, self.tts, self.media = fixture(self.root)

    def prepare(self, job):
        path = self.root / "输入/job.json"
        path.write_text(json.dumps(job))
        return engine.prepare_job(self.root, path)

    def test_cross_episode_and_version_immutability(self):
        self.assertTrue(w.check(self.root)["ok"])
        _, old = w.asset(self.root, "CHAR-LIN@v001")
        spec = self.root / "输入/CHAR-LIN.md"
        data = w.block(spec, "video-version")
        data["version"] = "v002"
        w.write_block(spec, "new", "video-version", data)
        w.add_version(self.root, spec)
        self.assertEqual(w.asset(self.root, "CHAR-LIN@v001")[1], old)
        with self.assertRaises(FileExistsError):
            w.add_version(self.root, spec)
        version = w.safe(self.root, old[1])
        version.write_text(version.read_text() + "changed")
        self.assertFalse(w.check(self.root)["ok"])

    def test_state_reset_and_missing_asset(self):
        path = self.root / "剧集/EP002/视觉设定.md"
        data = w.block(path, "video-episode")
        data["entry"]["CHAR-LIN.sleeve"] = "intact"
        w.write_block(path, "bad", "video-episode", data)
        self.assertFalse(w.check(self.root)["ok"])
        with self.assertRaises(ValueError):
            w.asset(self.root, "CHAR-LIN@v009")

    def test_prepare_pins_dependencies_and_config(self):
        preview = self.prepare(self.video)
        self.assertIn("config_sha256", preview["parameters"])
        stored = engine._read_job(self.root, self.video["job_id"])
        self.assertGreater(len(stored["inputs"]), 5)
        self.assertEqual(preview["parameters"]["model"], "wan3.0-video")
        self.prepare(self.tts)

    def test_mixed_audio_rejected_and_candidate_rejected(self):
        bad = copy.deepcopy(self.video)
        bad["parameters"]["media"].append(dict(self.media[0], type="reference_audio"))
        with self.assertRaises(ValueError):
            self.prepare(bad)
        path = w.safe(self.root, self.media[0]["record"])
        data = w.block(path, "video-media")
        data["status"] = "candidate"
        w.write_block(path, "candidate", "video-media", data)
        with self.assertRaises(ValueError):
            self.prepare(self.video)

    def test_dialogue_overrun_and_tampered_text(self):
        bad = copy.deepcopy(self.video)
        bad["parameters"]["dialogue_audio"] = (
            "资产库/角色/CHAR-LIN/声音/试听/synthetic.wav"
        )
        # Replace fixture audio with six seconds; preflight rejects altered pinned voice too.
        audio = w.safe(self.root, bad["parameters"]["dialogue_audio"])
        with wave.open(str(audio), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(8000)
            f.writeframes(b"\0\0" * 48000)
        with self.assertRaises(ValueError):
            self.prepare(bad)
        bad = copy.deepcopy(self.tts)
        bad["prompt"] = "不在剧本中"
        with self.assertRaises(ValueError):
            self.prepare(bad)

    def test_rules_promotion_and_retirement(self):
        data = {
            "id": "CASE-001",
            "job_id": "ACTION-001",
            "inputs": [],
            "observation": "合成观察",
            "observer": "offline-fixture",
            "change_set": ["减少同时动作"],
            "preserve_set": ["速度"],
            "conclusion": "仅测试",
            "status": "hypothesis",
        }
        case = w.record_case(self.root, data)
        rule = {
            "id": "RULE-001",
            "stages": ["video"],
            "models": ["wan3.0-video"],
            "modes": ["first_last_frame"],
            "instruction": "保留速度",
        }
        with self.assertRaises(ValueError):
            w.promote(self.root, case, rule)
        data["id"] = "CASE-002"
        data["status"] = "verified"
        case = w.record_case(self.root, data)
        r = w.promote(self.root, case, rule)
        with self.assertRaises(ValueError):
            self.prepare(self.video)
        self.video["parameters"]["rule_actions"] = {
            "RULE-001": "本轮维持5秒连续动作，待审"
        }
        self.assertEqual(
            len(self.prepare(self.video)["parameters"]["applied_rules"]), 1
        )
        new = dict(rule, id="RULE-002")
        r2 = w.promote(self.root, case, new)
        w.supersede(self.root, r, r2)
        self.assertEqual(
            [
                x[1]["id"]
                for x in w.matching_rules(
                    self.root, "video", "wan3.0-video", "first_last_frame"
                )
            ],
            ["RULE-002"],
        )

    def test_export_dependency_closure(self):
        (self.root / "输入/secret.env").write_text("private")
        (self.root / "剧集/EP001/制作成果/images/rejected.png").write_bytes(b"not used")
        out = Path(self.temp.name) / "export"
        w.export(self.root, out, ["EP001"])
        self.assertFalse((out / "输入").exists())
        self.assertFalse((out / "剧集/EP001/制作成果/images/rejected.png").exists())
        for p in (out / "资产库").rglob("设定.md"):
            for v in w.block(p, "video-asset")["versions"].values():
                self.assertTrue((out / v).exists())

    def test_engine_failure_collect_no_resubmit(self):
        script = Path(engine.__file__).with_name("fixture_adapter.py")
        conf = Path(self.temp.name) / "adapters.json"
        conf.write_text(
            json.dumps(
                {
                    "adapters": {
                        "aliyun": {
                            "command": [
                                sys.executable,
                                str(script),
                                "--submit-then-fail",
                            ],
                            "timeout_seconds": 10,
                        }
                    }
                }
            )
        )
        preview = self.prepare(self.video)
        engine.confirm_job(
            self.root, job_id="ACTION-001", confirmation=preview["confirmation"]
        )
        with self.assertRaises(Exception):
            engine.run_job(self.root, job_id="ACTION-001", adapter_config=conf)
        with self.assertRaises(RuntimeError):
            engine.run_job(self.root, job_id="ACTION-001", adapter_config=conf)
        result = engine.collect_job(self.root, job_id="ACTION-001", adapter_config=conf)
        self.assertTrue(result["collected"])
        self.assertTrue(w.safe(self.root, self.video["outputs"][0]).exists())

    def test_installer_preserves_changed_files(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        import install

        dest = Path(self.temp.name) / "skills"
        count = install.install(dest)
        self.assertGreater(count, 10)
        with self.assertRaises(FileExistsError):
            install.install(dest)
        p = dest / "video-voice/SKILL.md"
        old = p.read_text()
        p.write_text(old + "local")
        with self.assertRaises(ValueError):
            install.uninstall(dest)
        p.write_text(old)
        self.assertEqual(install.uninstall(dest), count)

    def test_wan_http_contract_and_recovery(self):
        self.prepare(self.video)
        job = engine._read_job(self.root, "ACTION-001")
        job.update(
            project_root=str(self.root),
            output_root=self.temp.name,
            handle_path=str(Path(self.temp.name) / "handle.json"),
        )
        calls = []

        def http(url, **kw):
            calls.append((url, kw))
            if kw.get("method") == "POST":
                self.assertEqual(kw["body"]["model"], "wan3.0-video")
                self.assertEqual(kw["body"]["input"]["media"][0]["type"], "first_frame")
                return {"output": {"task_id": "test-task"}}
            if "/tasks/" in url:
                return {
                    "output": {
                        "task_status": "SUCCEEDED",
                        "video_url": "https://example.invalid/video",
                    }
                }
            raise OSError("download interruption")

        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "fake"}):
            with self.assertRaises(OSError):
                adapter.execute(job, http=http, sleep=lambda _: None)
            self.assertEqual(
                json.loads(Path(job["handle_path"]).read_text())["provider_job_id"],
                "test-task",
            )
            job["collect_provider_job_id"] = "test-task"

            def collect(url, **kw):
                self.assertNotEqual(kw.get("method"), "POST")
                return (
                    b"video-fixture"
                    if kw.get("binary")
                    else {
                        "output": {
                            "task_status": "SUCCEEDED",
                            "video_url": "https://example.invalid/video",
                        }
                    }
                )

            self.assertEqual(
                adapter.execute(job, http=collect)["provider_job_id"], "test-task"
            )

    def test_qwen_save_measure_and_download_recovery(self):
        self.prepare(self.tts)
        job = engine._read_job(self.root, "TTS-001")
        job.update(
            project_root=str(self.root),
            output_root=self.temp.name,
            handle_path=str(Path(self.temp.name) / "tts-handle.json"),
        )
        wav = (self.root / "输入/silence.wav").read_bytes()

        def http(url, **kw):
            if kw.get("method") == "POST":
                self.assertEqual(kw["body"]["input"]["voice"], "fixture-voice")
                return {
                    "request_id": "req1",
                    "output": {"audio": {"url": "https://example.invalid/a.wav"}},
                }
            return wav

        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "fake"}):
            result = adapter.execute(job, http=http)
            self.assertEqual(result["duration_seconds"], 2)
            job["collect_provider_job_id"] = "tts:req1"

            def collect(url, **kw):
                self.assertNotEqual(kw.get("method"), "POST")
                return wav

            self.assertEqual(adapter.execute(job, http=collect)["duration_seconds"], 2)
            job.pop("collect_provider_job_id")
            with self.assertRaises(RuntimeError):
                adapter.execute(job, http=lambda *a, **k: {"code": "ModelUnavailable"})

    def test_upload_contract(self):
        calls = []

        def http(url, **kw):
            calls.append((url, kw))
            if kw.get("method") == "POST":
                return b""
            return {
                "data": {
                    "upload_dir": "test",
                    "upload_host": "https://example.invalid/upload",
                    "policy": "fake",
                    "signature": "fake",
                    "oss_access_key_id": "fake",
                    "x_oss_object_acl": "private",
                    "x_oss_forbid_overwrite": "true",
                }
            }

        value = adapter.upload(
            self.root / "输入/silence.wav",
            "wan3.0-video",
            "ap-southeast-1",
            {"Authorization": "Bearer fake"},
            http,
        )
        self.assertTrue(value.startswith("oss://test/"))
        self.assertNotIn("Authorization", calls[1][1]["headers"])


if __name__ == "__main__":
    unittest.main()


class AdditionalAcceptanceTests(unittest.TestCase):
    def test_audition_does_not_require_existing_voice_master(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "project"
            _, job, _ = fixture(root)
            sheet = root / "剧集/EP001/配音单.md"
            lines = w.block(sheet, "video-lines")
            lines[0].update(audition=True, voice_asset=None)
            w.write_block(sheet, "试听", "video-lines", lines)
            job["parameters"].update(
                audition=True, voice="selected-test-voice", assets=[]
            )
            path = root / "输入/audition.json"
            path.write_text(json.dumps(job))
            preview = engine.prepare_job(root, path)
            self.assertEqual(preview["parameters"]["voice"], "selected-test-voice")

    def test_direct_first_last_audio_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "project"
            job, _, _ = fixture(root)
            wrong = dict(job["parameters"]["media"][0], type="reference_audio")
            job["parameters"]["media"].append(wrong)
            source = root / job["source"]
            text = source.read_text()
            data = w.block(source, "video-inputs")
            data[job["source_entry"]]["media"] = job["parameters"]["media"]
            begin = text.index("```video-inputs")
            end = text.index("```", begin + 3) + 3
            source.write_text(
                text[:begin] + "```video-inputs\n" + w.dump(data) + "\n```" + text[end:]
            )
            with self.assertRaisesRegex(ValueError, "首尾帧模式"):
                w.prepare_parameters(root, job)

    def test_dialogue_timing_checks_real_audio(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "project"
            fixture(root)
            audio = root / "输入/long.wav"
            with wave.open(str(audio), "wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(8000)
                f.writeframes(b"\0\0" * 48000)
            path = root / "剧集/EP001/分镜.md"
            shots = w.block(path, "video-shots")
            shots[0]["dialogue_audio"] = "输入/long.wav"
            w.write_block(path, "test", "video-shots", shots)
            self.assertTrue(any("对白超出镜长" in x for x in w.check(root)["errors"]))

    def test_unknown_submission_does_not_retry(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "project"
            _, job, _ = fixture(root)
            path = root / "输入/job.json"
            path.write_text(json.dumps(job))
            engine.prepare_job(root, path)
            stored = engine._read_job(root, "TTS-001")
            stored.update(
                handle_path=str(Path(d) / "handle.json"),
                output_root=d,
                project_root=str(root),
            )
            count = []

            def http(url, **kw):
                count.append(url)
                raise TimeoutError("connection lost")

            with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "fake"}):
                with self.assertRaises(TimeoutError):
                    adapter.execute(stored, http=http)
            self.assertEqual(len(count), 1)
            self.assertEqual(
                json.loads(Path(stored["handle_path"]).read_text())["submission_state"],
                "unknown",
            )

    @unittest.skipUnless(
        os.environ.get("VIDEO_SKILLS_TEST_FFMPEG"),
        "set VIDEO_SKILLS_TEST_FFMPEG for render validation",
    )
    def test_mix_preserves_video_and_source_files(self):
        from mix_audio import command

        ffmpeg = os.environ["VIDEO_SKILLS_TEST_FFMPEG"]
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            folder = root / "剧集/EP001/制作成果"
            folder.mkdir(parents=True)
            video = folder / "original.mp4"
            audio = folder / "voice.wav"
            subprocess.run(
                [
                    ffmpeg,
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=blue:s=256x256:r=25:d=1",
                    "-c:v",
                    "libx264",
                    str(video),
                ],
                check=True,
            )
            with wave.open(str(audio), "wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(8000)
                f.writeframes(b"\0\0" * 8000)
            before = w.digest(video)
            plan = {
                "video": video.relative_to(root).as_posix(),
                "output": "剧集/EP001/制作成果/mixed.mp4",
                "original_audio": "replace",
                "duration": 1,
                "tracks": [
                    {"path": audio.relative_to(root).as_posix(), "start": 0, "gain": 1}
                ],
            }
            subprocess.run(
                command(root, plan, ffmpeg),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=True,
            )
            self.assertEqual(before, w.digest(video))
            decoded = []
            for path in (video, root / plan["output"]):
                decoded.append(
                    subprocess.check_output(
                        [
                            ffmpeg,
                            "-v",
                            "error",
                            "-i",
                            str(path),
                            "-map",
                            "0:v:0",
                            "-f",
                            "framemd5",
                            "-",
                        ]
                    )
                )
            self.assertEqual(decoded[0], decoded[1])
