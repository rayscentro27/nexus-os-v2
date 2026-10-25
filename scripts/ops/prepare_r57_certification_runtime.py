#!/usr/bin/env python3
"""Stage inherited R56 contract suites against the exact downloaded R56 runtime."""
import json, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
contract = json.loads((ROOT / "certification/r57_source/contract.json").read_text())
runtime = Path(__import__('os').environ["R56_RELEASE_ROOT"])
for relative in contract["inherited_test_suites"]:
    source = ROOT / relative
    target = runtime / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
manifest = json.loads((ROOT / "config/r55_deployable_release_manifest.v1.json").read_text())
for relative, entry in manifest["test_support_files"].items():
    source = ROOT / entry["path"]
    import hashlib
    if hashlib.sha256(source.read_bytes()).hexdigest() != entry["sha256"]:
        raise SystemExit("R55_TEST_SUPPORT_HASH_MISMATCH:" + relative)
    target = runtime / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
support = runtime / "certification/r54_source/services/nexus_mcp/server.py"
support.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(ROOT / "certification/r54_source/services/nexus_mcp/server.py", support)
print(json.dumps({"result":"PASS", "runtime":str(runtime), "test_suites":len(contract["inherited_test_suites"])}))
