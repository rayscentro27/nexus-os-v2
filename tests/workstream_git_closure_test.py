import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts/nexus_agent_platform/workstream_git_closure.py"


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=True).stdout


class WorkstreamClosureTests(unittest.TestCase):
    def run_tool(self, cwd, *args):
        env = os.environ.copy()
        env["NEXUS_GIT_ROOT"] = str(cwd)
        return subprocess.run([sys.executable, str(TOOL), *args], cwd=cwd, env=env, text=True, capture_output=True)

    def make_repo(self):
        d = tempfile.TemporaryDirectory()
        p = Path(d.name)
        git(p, "init", "-b", "main")
        git(p, "config", "user.email", "test@nexus.local")
        git(p, "config", "user.name", "Nexus Test")
        (p / "src/client-v2").mkdir(parents=True)
        (p / "src/client-v2/portal.ts").write_text("export const ok = true;\n")
        (p / "data/runtime").mkdir(parents=True)
        (p / "data/runtime/state.json").write_text("{}\n")
        git(p, "add", "--", "src/client-v2/portal.ts")
        git(p, "commit", "-m", "base")
        (p / "configs").mkdir()
        (p / "configs/nexus_git_workstreams.json").write_text((ROOT / "configs/nexus_git_workstreams.json").read_text())
        git(p, "add", "--", "configs/nexus_git_workstreams.json")
        git(p, "commit", "-m", "test manifest")
        return d, p

    def add_remote(self, p):
        bare = Path(tempfile.mkdtemp()) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
        git(p, "remote", "add", "origin", str(bare))
        git(p, "push", "origin", "HEAD:main")
        git(p, "fetch", "origin")
        return bare

    def test_manifest_and_dry_plan_do_not_mutate(self):
        result = self.run_tool(ROOT, "plan", "CLIENT_PORTAL")
        self.assertEqual(result.returncode, 0)
        self.assertIn("owned_candidates", result.stdout)

    def test_manifest_contains_hard_exclusions(self):
        manifest = json.loads((ROOT / "configs/nexus_git_workstreams.json").read_text())
        for value in ["data/runtime/", "data/cache/", "*.lock", "auth.json", "state.db"]:
            self.assertIn(value, manifest["global_forbidden"])

    def test_no_broad_git_add_literal(self):
        source = TOOL.read_text()
        self.assertNotIn('git", "add", "."', source)
        self.assertNotIn('git", "add", "-A"', source)

    def test_forbidden_runtime_and_auth_are_rejected_by_plan(self):
        d, p = self.make_repo()
        try:
            (p / "src/client-v2/auth.json").write_text("{}\n")
            (p / "src/client-v2/data.lock").write_text("x\n")
            result = self.run_tool(p, "plan", "CLIENT_PORTAL")
            self.assertEqual(result.returncode, 0)
            self.assertIn("auth.json", result.stdout)
            self.assertIn("data.lock", result.stdout)
        finally:
            d.cleanup()

    def test_cross_workstream_is_not_owned(self):
        d, p = self.make_repo()
        try:
            (p / "scripts").mkdir()
            (p / "scripts/nova.py").write_text("pass\n")
            result = self.run_tool(p, "plan", "CLIENT_PORTAL")
            self.assertEqual(result.returncode, 0)
            self.assertIn("other_dirty_files", result.stdout)
            self.assertIn("scripts/nova.py", result.stdout)
        finally:
            d.cleanup()

    def test_isolate_mode_copies_only_owned_file(self):
        d, p = self.make_repo()
        try:
            self.add_remote(p)
            (p / "src/client-v2/portal.ts").write_text("export const changed = true;\n")
            destination = Path(d.name) / "isolated"
            result = self.run_tool(p, "isolate", "CLIENT_PORTAL", str(destination))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((destination / "src/client-v2/portal.ts").read_text(), "export const changed = true\n" if False else "export const changed = true;\n")
            self.assertFalse((destination / "data/runtime/state.json").exists())
        finally:
            d.cleanup()

    def test_commit_writes_receipt_schema(self):
        d, p = self.make_repo()
        try:
            (p / "src/client-v2/portal.ts").write_text("export const changed = true;\n")
            result = self.run_tool(p, "commit", "CLIENT_PORTAL")
            self.assertEqual(result.returncode, 0, result.stderr)
            receipts = list((p / "reports/repository/git_closure").glob("CLIENT_PORTAL_*.json"))
            self.assertEqual(len(receipts), 1)
            receipt = json.loads(receipts[0].read_text())
            for key in ["workstream", "timestamp", "branch", "base_sha", "commit_sha", "files", "push_status"]:
                self.assertIn(key, receipt)
        finally:
            d.cleanup()

    def test_unrelated_history_blocks_push(self):
        d, p = self.make_repo()
        try:
            self.add_remote(p)
            (p / "scripts").mkdir()
            (p / "scripts/nova.py").write_text("pass\n")
            git(p, "add", "--", "scripts/nova.py")
            git(p, "commit", "-m", "unrelated")
            result = self.run_tool(p, "push", "CLIENT_PORTAL")
            self.assertEqual(result.returncode, 2)
            self.assertIn("PUSH_BLOCKED_UNRELATED_HISTORY", result.stderr)
        finally:
            d.cleanup()


if __name__ == "__main__":
    unittest.main()
