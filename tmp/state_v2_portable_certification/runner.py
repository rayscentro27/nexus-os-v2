"""Minimal runner for the isolated State v2 contract functions.

Implements only the tiny pytest surface used by the 25 existing tests. It does
not discover tests, load plugins, access provider credentials, or call providers.
"""
from __future__ import annotations

import importlib.util
import inspect
import os
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
scratch = tempfile.TemporaryDirectory(prefix="nexus-state-v2-cert-")
isolated_root = Path(scratch.name) / "research"
os.environ["NEXUS_CERTIFICATION_RESEARCH_STATE_ROOT"] = str(isolated_root)
os.environ["NEXUS_RESEARCH_STATE_ROOT"] = str(isolated_root)
os.environ["NEXUS_REPO_ROOT"] = str(ROOT)
os.environ.pop("NEXUS_PRODUCTION_RESEARCH_STATE_ROOT", None)
for secret_name in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ANON_KEY",
                    "VITE_SUPABASE_URL", "VITE_SUPABASE_ANON_KEY"):
    os.environ.pop(secret_name, None)


class _Raises:
    def __init__(self, expected): self.expected = expected
    def __enter__(self): return self
    def __exit__(self, kind, value, traceback):
        if kind is None: raise AssertionError(f"expected {self.expected.__name__}")
        if not issubclass(kind, self.expected): return False
        return True


class _PytestShim(types.ModuleType):
    @staticmethod
    def raises(expected): return _Raises(expected)
    @staticmethod
    def fail(message="pytest.fail"):
        raise AssertionError(message)


class _MonkeyPatch:
    def __init__(self): self.undo_actions = []
    def setattr(self, target, name, value=None):
        if value is None:
            target, name, value = target
        prior = getattr(target, name, None)
        existed = hasattr(target, name)
        self.undo_actions.append((target, name, prior, existed))
        setattr(target, name, value)
    def setenv(self, name, value):
        existed = name in __import__("os").environ
        prior = __import__("os").environ.get(name)
        self.undo_actions.append((__import__("os").environ, name, prior, existed))
        __import__("os").environ[name] = str(value)
    def delenv(self, name, raising=True):
        env = __import__("os").environ
        if raising and name not in env: raise KeyError(name)
        existed = name in env
        prior = env.get(name)
        self.undo_actions.append((env, name, prior, existed))
        env.pop(name, None)
    def undo(self):
        for target, name, prior, existed in reversed(self.undo_actions):
            is_mapping = hasattr(target, "__setitem__") and hasattr(target, "pop")
            if existed:
                if is_mapping: target[name] = prior
                else: setattr(target, name, prior)
            elif is_mapping: target.pop(name, None)
            else: delattr(target, name)
        self.undo_actions.clear()


sys.modules["pytest"] = _PytestShim("pytest")
test_path = ROOT / "scripts/research/tests/test_research_state_v2_persistence.py"
spec = importlib.util.spec_from_file_location("state_v2_contract_tests", test_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

passed = failed = 0
for name, fn in inspect.getmembers(module, inspect.isfunction):
    if not name.startswith("test_"):
        continue
    params = inspect.signature(fn).parameters
    patcher = _MonkeyPatch()
    with tempfile.TemporaryDirectory(prefix="state-v2-cert-") as directory:
        values = {"monkeypatch": patcher, "tmp_path": Path(directory)}
        try:
            fn(**{key: values[key] for key in params})
            passed += 1
            print(f"PASS {name}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
        finally:
            patcher.undo()
print(f"RESULT total={passed + failed} passed={passed} failed={failed}")
scratch.cleanup()
raise SystemExit(0 if passed == 25 and failed == 0 else 1)
