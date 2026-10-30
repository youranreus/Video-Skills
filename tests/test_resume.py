import json
from pathlib import Path
import tempfile
import unittest
from factory import fixture, w
import production_tool as engine
from resume import recover, review_digest


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "project"
        self.video, _, _ = fixture(self.root)

    def snapshot(self):
        return {
            str(p.relative_to(self.root)): p.read_bytes()
            for p in self.root.rglob("*")
            if p.is_file()
        }

    def test_readonly_and_acceptance_unknown(self):
        before = self.snapshot()
        r = recover(self.root)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(len(r["episodes"]), 2)
        self.assertTrue(
            any(x["state"] == "present_acceptance_unknown" for x in r["pending_review"])
        )
        self.assertEqual(r["next_actions"][0]["action"], "review_existing")

    def test_early_project_and_later_stage(self):
        fresh = Path(self.tmp.name) / "fresh"
        w.init(fresh, "New")
        r = recover(fresh)
        self.assertEqual(r["next_actions"][0]["skill"], "video-develop")
        # Explicit acceptance is attached to the owning documents, not a second progress database.
        for name in (
            "剧本.md",
            "视觉设定.md",
            "分镜.md",
            "图片提示词.md",
            "配音单.md",
            "视频提示词.md",
        ):
            p = self.root / "剧集/EP001" / name
            p.write_text(
                p.read_text()
                + "\n```video-review\n"
                + json.dumps(
                    {
                        "status": "accepted",
                        "evidence": "用户在本项目验收此版本",
                        "content_sha256": review_digest(p.read_text()),
                    }
                )
                + "\n```\n"
            )
        r = recover(self.root, "EP001")
        self.assertEqual(r["next_actions"][0]["skill"], "video-edit")

    def test_orphan_and_changed_inputs_take_priority(self):
        p = self.root / "输入/job.json"
        p.write_text(json.dumps(self.video))
        engine.prepare_job(self.root, p)
        job = engine._read_job(self.root, "ACTION-001")
        run = {
            "schema_version": engine.JOB_SCHEMA,
            "run_id": "20261030T010101-test",
            "job_id": "ACTION-001",
            "fingerprint": job["fingerprint"],
            "modality": "video",
            "adapter": "aliyun",
            "status": "failed",
            "started_at": "2026-10-30T01:01:01Z",
            "finished_at": "2026-10-30T01:01:02Z",
            "outputs": [],
            "provider_job_id": "fake-task",
        }
        engine._write_run(self.root, "ACTION-001", run)
        source = self.root / self.video["source"]
        source.write_text(source.read_text() + "\nchanged")
        r = recover(self.root, "EP002")
        self.assertEqual(r["next_actions"][0]["action"], "collect")
        self.assertFalse(r["in_flight"][0]["inputs_current"])
        self.assertNotIn("fake-task", json.dumps(r))

    def test_unknown_handle_and_corruption(self):
        p = self.root / "输入/job.json"
        p.write_text(json.dumps(self.video))
        engine.prepare_job(self.root, p)
        job = engine._read_job(self.root, "ACTION-001")
        run = {
            "schema_version": engine.JOB_SCHEMA,
            "run_id": "20261030T010101-test",
            "job_id": "ACTION-001",
            "fingerprint": job["fingerprint"],
            "modality": "video",
            "adapter": "aliyun",
            "status": "running",
            "started_at": "2026-10-30T01:01:01Z",
            "finished_at": None,
            "outputs": [],
        }
        engine._write_run(self.root, "ACTION-001", run)
        engine._metadata_atomic_json(
            self.root,
            ("handles", engine._job_key("ACTION-001")),
            run["run_id"] + ".json",
            {
                "submission_state": "unknown",
                "audio_url": "https://private.invalid/signed",
            },
        )
        r = recover(self.root)
        self.assertEqual(r["next_actions"][0]["action"], "investigate")
        self.assertNotIn("private.invalid", json.dumps(r))
        (self.root / "剧集/EP002/视觉设定.md").write_text("broken")
        self.assertTrue(recover(self.root)["blockers"])

    def test_unregistered_media_and_symlink(self):
        p = self.root / "剧集/EP001/制作成果/images/unregistered.png"
        p.write_bytes(b"test")
        r = recover(self.root)
        self.assertTrue(any(x["state"] == "unregistered" for x in r["pending_review"]))
        outside = Path(self.tmp.name) / "outside.png"
        outside.write_bytes(b"private")
        (p.parent / "link.png").symlink_to(outside)
        self.assertTrue(recover(self.root)["blockers"])


if __name__ == "__main__":
    unittest.main()


class ResumeRegressionTests(unittest.TestCase):
    def test_changed_text_invalidates_acceptance(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "project"
            fixture(root)
            p = root / "剧集/EP001/视频提示词.md"
            review = {
                "status": "accepted",
                "evidence": "测试确认",
                "content_sha256": review_digest(p.read_text()),
            }
            p.write_text(
                p.read_text() + "\n```video-review\n" + json.dumps(review) + "\n```\n"
            )
            p.write_text(p.read_text().replace("迅速转身", "慢慢转身"))
            r = recover(root, "EP001")
            item = next(
                x for x in r["pending_review"] if x["path"].endswith("视频提示词.md")
            )
            self.assertEqual(item["state"], "present_acceptance_unknown")

    def test_prepared_jobs_and_continuity_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "project"
            job, _, _ = fixture(root)
            p = root / "输入/job.json"
            p.write_text(json.dumps(job))
            engine.prepare_job(root, p)
            self.assertEqual(
                recover(root)["next_actions"][0]["action"], "review_prepared_job"
            )
            p = root / "剧集/EP002/分镜.md"
            shots = w.block(p, "video-shots")
            shots[0]["start"]["CHAR-LIN.sleeve"] = "intact"
            w.write_block(p, "冲突", "video-shots", shots)
            r = recover(root)
            self.assertTrue(
                any(x["skill"] == "video-storyboard" for x in r["blockers"])
            )
