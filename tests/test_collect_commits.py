"""Exercise real Git histories; no network or user repository changes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/git-work-summary/scripts/collect_commits.py"


class CommitContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "日本語 repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture Author")
        self.git("config", "user.email", "fixture@example.invalid")

    def git(self, *args, env=None):
        return subprocess.check_output(
            ["git", "-C", str(self.repo), *args], env=env,
            text=True, encoding="utf-8", stderr=subprocess.PIPE,
        ).strip()

    def commit(self, name, timestamp, authored=None):
        (self.repo / "譜面.txt").write_text(name, encoding="utf-8")
        self.git("add", "--", "譜面.txt")
        env = dict(os.environ, GIT_COMMITTER_DATE=timestamp,
                   GIT_AUTHOR_DATE=authored or timestamp)
        self.git("commit", "-qm", name, env=env)

    def collect(self, *extra):
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPT), "--repo", str(self.repo),
             "--date", "2026-11-19", "--utc-offset", "+09:00", *extra],
            text=True, encoding="utf-8", capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_day_boundaries_use_committer_date(self):
        self.commit("before", "2026-11-18T23:59:59+09:00")
        self.commit("start", "2026-11-19T00:00:00+09:00", "2026-11-17T12:00:00+09:00")
        self.commit("end", "2026-11-19T23:59:59+09:00")
        self.commit("after", "2026-11-20T00:00:00+09:00")
        result = self.collect()
        self.assertEqual([c["subject"] for c in result["commits"]], ["end", "start"])
        self.assertEqual(result["commit_count"], 2)
        self.assertEqual(result["commits"][0]["changed_files"], ["譜面.txt"])
        self.assertNotIn("working_tree", result)

    def test_other_branch_is_excluded_and_state_is_unchanged(self):
        self.commit("base", "2026-11-18T12:00:00+09:00")
        branch = self.git("branch", "--show-current")
        self.git("checkout", "-qb", "other")
        self.commit("unrelated", "2026-11-19T12:00:00+09:00")
        self.git("checkout", "-q", branch)
        (self.repo / "譜面.txt").write_text("staged", encoding="utf-8")
        self.git("add", "--", "譜面.txt")
        (self.repo / "譜面.txt").write_text("unstaged", encoding="utf-8")
        (self.repo / "未追跡.txt").write_text("draft", encoding="utf-8")
        before = self.git("status", "--porcelain=v1")
        result = self.collect("--include-working-tree")
        self.assertEqual(result["commit_count"], 0)
        self.assertEqual(result["working_tree"]["staged"], ["譜面.txt"])
        self.assertEqual(result["working_tree"]["unstaged"], ["譜面.txt"])
        self.assertEqual(result["working_tree"]["untracked"], ["未追跡.txt"])
        self.assertEqual(self.git("status", "--porcelain=v1"), before)

    def test_old_intermediate_commit_does_not_hide_today_ancestor(self):
        self.commit("today", "2026-11-19T10:00:00+09:00")
        self.commit("older_clock", "2026-11-17T10:00:00+09:00")
        self.assertEqual([c["subject"] for c in self.collect()["commits"]], ["today"])

    def test_unborn_repository_is_empty(self):
        self.assertEqual(self.collect()["commit_count"], 0)

    def test_detached_head_is_supported(self):
        self.commit("today", "2026-11-19T12:00:00+09:00")
        self.git("checkout", "-q", "--detach")
        result = self.collect()
        self.assertEqual(result["branch"], "detached HEAD")
        self.assertEqual(result["commit_count"], 1)

    def test_ref_is_resolved_without_checkout(self):
        self.commit("base", "2026-11-18T12:00:00+09:00")
        branch = self.git("branch", "--show-current")
        self.git("checkout", "-qb", "other")
        self.commit("other work", "2026-11-19T12:00:00+09:00")
        self.git("checkout", "-q", branch)
        result = self.collect("--ref", "other")
        self.assertEqual([c["subject"] for c in result["commits"]], ["other work"])
        self.assertEqual(self.git("branch", "--show-current"), branch)


if __name__ == "__main__":
    unittest.main()
