#!/usr/bin/env python3
"""Build a deterministic Nova R30 transport-only release from certified R29."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path


COMPONENT = Path(__file__).resolve().parent
REPOSITORY = COMPONENT.parents[1]
R29 = COMPONENT.parent / "nova-operator-v1-20261025-r29-research-control"
EVIDENCE = COMPONENT / "R29_BASE_EVIDENCE"
RELEASE_ID = "nova-operator-v1-20261025-r30-native-mcp"
DIST = Path(os.environ.get("NOVA_R30_DIST", REPOSITORY / "dist")).resolve()
RELEASE = DIST / RELEASE_ID
ARCHIVE = DIST / f"{RELEASE_ID}.tar.gz"
OVERLAY = COMPONENT / "overlay/scripts/nova/nexus_mcp_status.py"
TEST = COMPONENT / "certification/tests/test_native_mcp_transport.py"
PARENT_COMMIT = "6cdf01c9c768333fb7db2dee01aff2366a9b1413"
PARENT_ARTIFACT_SHA = "89612aec5540b2a50e40dc7895c6d7890d933beb38a1136fe63046a956621387"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_exact_r29_runtime(target: Path, manifest: dict) -> None:
    if manifest.get("release_id") != "nova-operator-v1-20261025-r29-research-control":
        raise SystemExit("R29_BASE_RELEASE_ID_MISMATCH")
    if manifest.get("source_commit") != PARENT_COMMIT or manifest.get("parent_commit") != "f99c1eb04dc4ba6017de6de5bdade72f0f3f1d75":
        raise SystemExit("R29_BASE_LINEAGE_MISMATCH")
    if manifest.get("certification", {}).get("result") != "PASS":
        raise SystemExit("R29_BASE_NOT_CERTIFIED")
    if manifest.get("payload_file_count") != 163:
        raise SystemExit("R29_BASE_PAYLOAD_COUNT_MISMATCH")
    raw = (EVIDENCE / "R29_MANIFEST.sha256").read_text().split()[0]
    if sha(EVIDENCE / "R29_MANIFEST.json") != raw:
        raise SystemExit("R29_BASE_MANIFEST_DIGEST_MISMATCH")

    hashes = manifest["payload_sha256"]
    for relative, expected in hashes.items():
        if relative.startswith("runtime/"):
            source = R29 / relative
        elif relative.startswith("certification/"):
            source = R29 / relative
        else:
            source = EVIDENCE / relative
        if not source.is_file() or sha(source) != expected:
            raise SystemExit("R29_BASE_FILE_MISMATCH:" + relative)

    shutil.copytree(R29 / "runtime", target)
    changed = target / "scripts/nova/nexus_mcp_status.py"
    shutil.copyfile(OVERLAY, changed)
    if (target / "scripts/nexus_agent_platform/research_only_execution.py").exists():
        raise SystemExit("R60_RESEARCH_RUNTIME_MUST_NOT_BE_INCLUDED")


def _run_candidate_tests(root: Path, runtime: Path) -> tuple[int, int, int]:
    cert = root / "certification"
    (cert / "tests").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEST, cert / "tests/test_native_mcp_transport.py")
    shutil.copyfile(EVIDENCE / "R29_MANIFEST.json", cert / "R29_BASE_MANIFEST.json")
    shutil.copyfile(COMPONENT / "BASELINE_SOURCE.json", cert / "R29_BASE_ARTIFACT.json")

    r29_env = os.environ.copy()
    r29_env["PYTHONPATH"] = str(R29 / "runtime/scripts") + os.pathsep + r29_env.get("PYTHONPATH", "")
    r29_result = subprocess.run(
        [os.environ.get("PYTHON", "python3"), "-B", "-m", "unittest", "discover",
         "-s", "certification/tests", "-v"], cwd=R29, env=r29_env,
        capture_output=True, text=True, check=False,
    )
    r29_output = r29_result.stdout + r29_result.stderr
    if r29_result.returncode or "Ran 44 tests" not in r29_output or "OK" not in r29_output:
        raise SystemExit("R29_CONTROL_REGRESSION_FAILED\n" + r29_output[-12000:])

    env = os.environ.copy()
    env["PYTHONPATH"] = str(runtime / "scripts") + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [os.environ.get("PYTHON", "python3"), "-B", "-m", "unittest", "discover",
         "-s", str(cert / "tests"), "-v"],
        cwd=root, env=env, capture_output=True, text=True, check=False,
    )
    output = result.stdout + result.stderr
    if result.returncode or "FAILED" in output or "OK" not in output:
        raise SystemExit("R30_CANDIDATE_TESTS_FAILED\n" + output[-12000:])
    if "Ran 14 tests" not in output:
        raise SystemExit("R30_EXPECTED_14_NATIVE_TESTS\n" + output[-3000:])
    return 58, 58, 0


def main() -> int:
    if RELEASE.exists() or ARCHIVE.exists():
        raise SystemExit("IMMUTABLE_RELEASE_OUTPUT_EXISTS")
    source = json.loads((COMPONENT / "BASELINE_SOURCE.json").read_text())
    if source.get("parent_commit") != PARENT_COMMIT or source.get("parent_artifact_sha256") != PARENT_ARTIFACT_SHA:
        raise SystemExit("R30_PARENT_IDENTITY_MISMATCH")
    manifest = json.loads((EVIDENCE / "R29_MANIFEST.json").read_text())
    DIST.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nova-r30-cert-") as temp:
        candidate = Path(temp) / "candidate"
        candidate.mkdir()
        runtime = candidate / "runtime"
        _copy_exact_r29_runtime(runtime, manifest)
        test_count, test_pass, test_fail = _run_candidate_tests(candidate, runtime)

        RELEASE.mkdir()
        shutil.copytree(runtime, RELEASE / "runtime")
        shutil.copytree(candidate / "certification", RELEASE / "certification")
        shutil.copyfile(R29 / "BASELINE_LINEAGE.json", RELEASE / "BASELINE_LINEAGE.json")
        shutil.copyfile(R29 / "R28_BASE_INPUT_MANIFEST.sha256", RELEASE / "R28_BASE_INPUT_MANIFEST.sha256")
        shutil.copytree(EVIDENCE, RELEASE / "parent_evidence")
        shutil.copytree(R29 / "certification/tests", RELEASE / "parent_evidence/certification/tests")
        payload: dict[str, str] = {}
        for path in sorted(p for p in RELEASE.rglob("*") if p.is_file()):
            payload[path.relative_to(RELEASE).as_posix()] = sha(path)

    commit = os.environ.get("GITHUB_SHA", "").strip() or subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY, text=True).strip()
    report = {
        "release_id": RELEASE_ID, "source_commit": commit, "parent_commit": PARENT_COMMIT,
        "parent_artifact_sha256": PARENT_ARTIFACT_SHA, "parent_release": source["parent_release"],
        "result": "PASS", "tests": test_count, "test_pass": test_pass, "test_fail": test_fail,
        "runtime_changed_files": ["scripts/nova/nexus_mcp_status.py"],
        "research_runtime_changed_files": [], "docker_required_for_nova_mcp": False,
        "direct_database_fallback": False, "production_research_jobs_created": False,
    }
    report_path = RELEASE / "CERTIFICATION_REPORT.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    payload["CERTIFICATION_REPORT.json"] = sha(report_path)
    metadata = {
        **source, "source_commit": commit, "certification": {"result": "PASS", "tests": test_count, "failures": test_fail},
        "runtime_file_count": sum(1 for _ in (RELEASE / "runtime").rglob("*") if _.is_file()),
        "payload_file_count": len(payload) + 1,
    }
    metadata_path = RELEASE / "BUILD_METADATA.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    payload["BUILD_METADATA.json"] = sha(metadata_path)
    release_manifest = {
        "release_id": RELEASE_ID, "source_commit": commit, "parent_commit": PARENT_COMMIT,
        "payload_file_count": len(payload), "payload_sha256": payload,
        "certification": {"result": "PASS", "tests": test_count, "failures": test_fail},
    }
    manifest_path = RELEASE / "R30_MANIFEST.json"
    manifest_path.write_text(json.dumps(release_manifest, indent=2, sort_keys=True) + "\n")
    (RELEASE / "R30_MANIFEST.sha256").write_text(f"{sha(manifest_path)}  R30_MANIFEST.json\n")
    for relative, expected in payload.items():
        if sha(RELEASE / relative) != expected:
            raise SystemExit("R30_PAYLOAD_MISMATCH:" + relative)

    with ARCHIVE.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, filename="", mode="wb", mtime=0, compresslevel=9) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as archive:
                for path in sorted(p for p in RELEASE.rglob("*") if p.is_file()):
                    relative = path.relative_to(RELEASE).as_posix()
                    info = tarfile.TarInfo(f"{RELEASE_ID}/{relative}")
                    info.size, info.mode, info.mtime = path.stat().st_size, path.stat().st_mode & 0o777, 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    with path.open("rb") as stream:
                        archive.addfile(info, stream)
    print(json.dumps({"release": RELEASE_ID, "artifact": str(ARCHIVE), "sha256": sha(ARCHIVE),
                      "source_commit": commit, "tests": test_count, "pass": test_pass, "fail": test_fail,
                      "runtime_changed_files": report["runtime_changed_files"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
