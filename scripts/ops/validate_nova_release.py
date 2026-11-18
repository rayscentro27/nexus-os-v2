#!/usr/bin/env python3
"""Fail-closed local dependency and import validator for a staged Nova release."""
from __future__ import annotations

import ast
import hashlib
import argparse
import os
import selectors
import subprocess
import sys
import time
from pathlib import Path

NOVA_ENTRYPOINTS = (
    "scripts/nova/nova_telegram_worker.py",
    "scripts/nova/operator_v1.py",
    "scripts/nova/context_authority.py",
    "scripts/nova/approved_mcp_registry.py",
    "scripts/nova/nexus_mcp_status.py",
)
PACKAGE_ROOTS = ("scripts/nova", "scripts/nexus_agent_platform", "scripts/research", "services")
GLOBAL_TIMEOUT_SECONDS = 300


def run_bounded_worker() -> int:
    """Supervise the scanner itself so even filesystem stalls are bounded."""
    command = [sys.executable, "-u", str(Path(__file__).resolve()), *sys.argv[1:], "--_worker"]
    print(f"VALIDATOR_START=YES GLOBAL_TIMEOUT_SECONDS={GLOBAL_TIMEOUT_SECONDS} COMMAND={command}", flush=True)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
    print(f"VALIDATOR_WORKER_PID={process.pid}", flush=True)
    selector = selectors.DefaultSelector()
    assert process.stdout is not None
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + GLOBAL_TIMEOUT_SECONDS
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            process.terminate()
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
            print(f"VALIDATOR_GLOBAL_TIMEOUT=YES SECONDS={GLOBAL_TIMEOUT_SECONDS} PROCESS_TERMINATED=YES", flush=True)
            return 124
        for key, _ in selector.select(min(1.0, remaining)):
            chunk = os.read(key.fd, 4096)
            if chunk:
                sys.stdout.write(chunk.decode(errors="replace")); sys.stdout.flush()
            else:
                selector.unregister(key.fileobj)
        result = process.poll()
        if result is not None:
            if selector.get_map():
                for key in list(selector.get_map().values()):
                    chunk = os.read(key.fd, 65536)
                    if chunk: sys.stdout.write(chunk.decode(errors="replace")); sys.stdout.flush()
                    selector.unregister(key.fileobj)
            return result


def packaged_modules(root: Path) -> set[str]:
    modules: set[str] = set()
    for package in PACKAGE_ROOTS:
        base = root / package
        if not base.exists():
            continue
        started = time.monotonic()
        print(f"SCAN_START={package}", flush=True)
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            relative = path.relative_to(root).with_suffix("")
            modules.add(".".join(relative.parts[1:]))
        print(f"SCAN_END={package} ELAPSED_MS={int((time.monotonic()-started)*1000)}", flush=True)
    return modules


def local_imports(root: Path, entry: Path, modules: set[str]) -> set[str]:
    tree = ast.parse(entry.read_text(encoding="utf-8"), filename=str(entry))
    missing: set[str] = set()
    prefixes = {".".join(candidate.split(".")[:i]) for candidate in modules
                for i in range(1, len(candidate.split(".")))}
    relative = entry.relative_to(root).with_suffix("")
    module_parts = relative.parts[1:]  # drop the top-level source directory (scripts/services)
    current_module = ".".join(module_parts)
    current_package = current_module.rpartition(".")[0]
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                if node.level:
                    package_parts = current_package.split(".") if current_package else []
                    if node.level > len(package_parts) + 1:
                        missing.add("." * node.level + node.module)
                    else:
                        base = package_parts[:len(package_parts) - node.level + 1]
                        names.append(".".join(base + node.module.split(".")))
                else:
                    names.append(node.module)
            elif node.level:
                package_parts = current_package.split(".") if current_package else []
                base = package_parts[:max(0, len(package_parts) - node.level + 1)]
                for alias in node.names:
                    names.append(".".join(base + alias.name.split(".")))
        for name in names:
            top = name.split(".", 1)[0]
            if top in {"nova", "nexus_agent_platform", "research"} and name not in modules:
                # Parent packages are allowed when one or more children exist.
                if name not in prefixes:
                    missing.add(name)
    return missing


def release_local_imports(root: Path, modules: set[str]) -> set[str]:
    """Check local imports from every packaged module, not just chosen entrypoints."""
    missing: set[str] = set()
    child_prefixes = {".".join(module.split(".")[:i]) for module in modules
                      for i in range(1, len(module.split(".")))}
    paths = {module: (root / ("services" if module.split(".", 1)[0] == "services" else "scripts") /
                      Path(*module.split("."))).with_suffix(".py") for module in modules}
    for index, module in enumerate(sorted(modules), 1):
        top = module.split(".", 1)[0]
        relative = (Path("services") if top == "services" else Path("scripts")) / Path(*module.split("."))
        entry = paths[module]
        if not entry.is_file(): entry = root / relative / "__init__.py"
        if entry.is_file():
            for name in local_imports(root, entry, modules):
                top_name = name.split(".", 1)[0]
                if top_name in {"nova", "nexus_agent_platform", "research"} and name not in modules and name not in child_prefixes:
                    missing.add(f"{entry.relative_to(root)}: {name}")
        if index % 25 == 0:
            print(f"CLOSURE_PROGRESS={index}/{len(modules)} MODULE={module}", flush=True)
    return missing


def module_file(root: Path, name: str) -> Path | None:
    """Resolve repository-local import names across the release's script roots."""
    parts = Path(*name.split("."))
    candidates = [root / "scripts" / parts.with_suffix(".py"), root / "scripts" / parts / "__init__.py",
                  root / "scripts" / "research" / parts.with_suffix(".py"),
                  root / "scripts" / "nexus_agent_platform" / parts.with_suffix(".py"),
                  root / "services" / parts.with_suffix(".py")]
    return next((path for path in candidates if path.is_file()), None)


def imported_local_names(entry: Path, root: Path, source_root: Path | None = None) -> set[str]:
    """Return imported names that resolve to local release modules or packages."""
    tree = ast.parse(entry.read_text(encoding="utf-8"), filename=str(entry))
    rel = entry.relative_to(root).with_suffix("")
    parts = list(rel.parts[1:])
    is_package_init = bool(parts and parts[-1] == "__init__")
    if is_package_init:
        parts.pop()
    package = parts if is_package_init else parts[:-1]
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names
                         if module_file(root, alias.name) or (source_root and module_file(source_root, alias.name)))
        elif isinstance(node, ast.ImportFrom):
            base_parts = package[:]
            if node.level:
                base_parts = base_parts[:max(0, len(base_parts) - node.level + 1)]
            if node.module:
                target = ".".join(base_parts + node.module.split(".")) if node.level else node.module
            else:
                target = ".".join(base_parts)
            if target and (module_file(root, target) or (source_root and module_file(source_root, target))): found.add(target)
            if target:
                for alias in node.names:
                    child = f"{target}.{alias.name}"
                    if module_file(root, child) or (source_root and module_file(source_root, child)): found.add(child)
    return found


def reachable_missing_imports(root: Path, entrypoints: list[str], source_root: Path | None) -> set[str]:
    """Walk imports reachable from release entrypoints and report absent modules."""
    pending: list[tuple[str, Path]] = []
    for relative in entrypoints:
        entry = root / relative
        module = ".".join(Path(relative).with_suffix("").parts[1:])
        pending.append((module, entry))
    visited: set[str] = set()
    missing: set[str] = set()
    while pending:
        current, path = pending.pop()
        if current in visited: continue
        visited.add(current)
        for imported in imported_local_names(path, root, source_root):
            resolved = module_file(root, imported)
            if resolved is None:
                missing.add(f"{path.relative_to(root)}: {imported}")
                continue
            if imported not in visited: pending.append((imported, resolved))
    return missing


def import_probe(root: Path, module: str, timeout: float, forbidden: list[Path], required_symbol: str | None = None) -> tuple[str, str, int]:
    """Import one module in a killable, isolated interpreter and audit origins."""
    probe = r'''import importlib, json, os, pathlib, sys, time
root=pathlib.Path(sys.argv[1]).resolve(); mod=sys.argv[2]
required_symbol=os.environ.get("NEXUS_REQUIRED_SYMBOL","")
sys.dont_write_bytecode=True
blocked=[pathlib.Path(x).resolve() for x in json.loads(os.environ["NEXUS_BLOCKED_IMPORT_ROOTS"])]
def under(path, base):
    try: pathlib.Path(path).resolve().relative_to(base); return True
    except (ValueError, OSError, RuntimeError): return False
kept=[]
for item in sys.path:
    if not item: continue
    resolved=pathlib.Path(item).resolve()
    is_approved_environment=any(part in {"site-packages","dist-packages"} for part in resolved.parts)
    if not is_approved_environment and any(under(resolved, b) for b in blocked): continue
    kept.append(item)
sys.path[:]=[str(root), str(root/"scripts"), *kept]
t=time.monotonic(); print("MODULE_IMPORT_START="+mod, flush=True)
print("CANDIDATE_RELEASE_ROOT="+str(root), flush=True)
print("ISOLATED_SYS_PATH="+json.dumps(sys.path), flush=True)
side_effects=[]
def deny_import_side_effect(event,args):
    if event in {"socket.connect","socket.getaddrinfo","subprocess.Popen","os.system","os.fork","os.posix_spawn","sqlite3.connect"}:
        side_effects.append(event)
        raise PermissionError("import-time side effect blocked: "+event)
    if event=="open" and len(args)>2 and isinstance(args[2],int) and args[2] & (os.O_CREAT|os.O_TRUNC|os.O_APPEND):
        side_effects.append("file-write")
        raise PermissionError("import-time file write blocked")
sys.addaudithook(deny_import_side_effect)
try:
    loaded=importlib.import_module(mod)
    symbol_exists=not required_symbol or hasattr(loaded,required_symbol)
    origins={name:getattr(value,"__file__",None) for name,value in sys.modules.items() if getattr(value,"__file__",None)}
    escapes={name:path for name,path in origins.items()
             if any(under(path,b) for b in blocked)
             and not any(part in {"site-packages","dist-packages"} for part in pathlib.Path(path).parts)}
    resolved=getattr(loaded,"__file__",None)
    if resolved and not under(resolved,root) and not escapes:
        escapes[mod]=resolved
    print("MODULE_IMPORT_END="+mod, flush=True)
    print("MODULE_RESULT="+json.dumps({"ok":True,"resolved":resolved,"escapes":escapes,"sys_path":sys.path,"side_effects":side_effects,"symbol_exists":symbol_exists},default=str))
except BaseException as exc:
    print("MODULE_IMPORT_END="+mod, flush=True)
    print("MODULE_RESULT="+json.dumps({"ok":False,"error":type(exc).__name__+":"+str(exc)[:240],"sys_path":sys.path,"side_effects":side_effects}))
'''
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["NEXUS_BLOCKED_IMPORT_ROOTS"] = __import__("json").dumps([str(p) for p in forbidden])
    env["NEXUS_REQUIRED_SYMBOL"] = required_symbol or ""
    started = time.monotonic()
    print(f"MODULE_START={module}", flush=True)
    command = [sys.executable, "-u", "-c", probe, str(root), module]
    process = subprocess.Popen(command, cwd=str(root), env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, bufsize=0)
    selector = selectors.DefaultSelector()
    assert process.stdout is not None and process.stderr is not None
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    chunks = {"stdout": [], "stderr": []}
    pending = {"stdout": "", "stderr": ""}
    deadline = started + timeout
    try:
        timed_out = False
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                process.terminate()
                try: process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait()
                break
            for key, _ in selector.select(min(0.25, remaining)):
                tag = key.data
                data = os.read(key.fileobj.fileno(), 8192)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                text = data.decode(errors="replace")
                chunks[tag].append(text)
                pending[tag] += text
                while "\n" in pending[tag]:
                    line, pending[tag] = pending[tag].split("\n", 1)
                    print(line, flush=True) if tag == "stdout" else print(f"MODULE_STDERR={module} {line[-1000:]}", flush=True)
        for tag in ("stdout", "stderr"):
            if pending[tag]:
                print(pending[tag] if tag == "stdout" else f"MODULE_STDERR={module} {pending[tag][-1000:]}", flush=True)
        stdout = "".join(chunks["stdout"])
        if timed_out:
            duration = int((time.monotonic()-started)*1000)
            print(f"ELAPSED_MS={duration} RESULT=TIMEOUT MODULE={module} PROCESS_TERMINATED=YES", flush=True)
            return "TIMEOUT", "", duration
        return_code = process.wait()
        result_line = next((line.split("=",1)[1] for line in stdout.splitlines()
                            if line.startswith("MODULE_RESULT=")), "{}")
        duration = int((time.monotonic()-started)*1000)
        try:
            result = __import__("json").loads(result_line)
            ok = bool(result.get("ok")) and result.get("symbol_exists", True) and not result.get("escapes") and not result.get("side_effects") and return_code == 0
            print(f"ELAPSED_MS={duration} RESULT={'PASS' if ok else 'FAIL'} MODULE={module}", flush=True)
            if result.get("escapes"): print(f"IMPORT_ESCAPE={result['escapes']}", flush=True)
            print(f"SIDE_EFFECTS_OBSERVED={result.get('side_effects', [])}", flush=True)
            return ("PASS" if ok else "FAIL", str(result.get("resolved") or result.get("error") or ""), duration)
        except ValueError:
            print(f"ELAPSED_MS={duration} RESULT=FAIL MODULE={module} ERROR=NO_RESULT", flush=True)
            return "FAIL", "NO_RESULT", duration
    finally:
        selector.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_root", type=Path)
    parser.add_argument("--entrypoint", action="append", default=[],
                        help="additional packaged entrypoint, relative to release root")
    parser.add_argument("--all-packaged-imports", action="store_true",
                        help="check local import closure from every packaged Python module")
    parser.add_argument("--reachable-import-closure", action="store_true",
                        help="check the recursive import closure rooted at the supplied entrypoints")
    parser.add_argument("--static-only", action="store_true",
                        help="stop after entrypoint and local import closure checks")
    parser.add_argument("--import-only", action="store_true",
                        help="run isolated import probes without the static closure gate (diagnostics only)")
    parser.add_argument("--module", action="append", default=[], help="additional module to import in an isolated subprocess")
    parser.add_argument("--symbol", action="append", default=[], help="required symbol as module:symbol; imported in isolation")
    parser.add_argument("--no-entrypoint-import", action="store_true",
                        help="diagnostics mode: import only explicitly named --module values")
    parser.add_argument("--module-timeout", type=float, default=15.0,
                        help="maximum seconds allowed for each isolated module import")
    parser.add_argument("--canonical-source-root", type=Path, default=None,
                        help="forbid imports from this source root")
    parser.add_argument("--source-root", type=Path, default=None,
                        help="canonical source tree used to detect missing release modules")
    parser.add_argument("--active-release", type=Path, default=None,
                        help="forbid imports from this active release")
    parser.add_argument("--_worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = args.release_root.resolve()
    if not root.is_dir():
        print("RELEASE_ROOT=FAIL")
        return 1
    modules = packaged_modules(root)
    entrypoints = args.entrypoint or list(NOVA_ENTRYPOINTS)
    missing_files = [path for path in entrypoints if not (root / path).is_file()]
    missing_imports = set() if args.import_only else {
        f"{entry}: {name}"
        for relative in entrypoints if (entry := root / relative).is_file()
        for name in local_imports(root, entry, modules)
    }
    if args.all_packaged_imports and not args.import_only:
        missing_imports.update(release_local_imports(root, modules))
    if args.reachable_import_closure and not args.import_only:
        missing_imports.update(reachable_missing_imports(root, entrypoints, args.source_root.resolve() if args.source_root else None))
    print(f"PACKAGED_PYTHON_MODULES={len(modules)}")
    print(f"PRIMARY_ENTRYPOINTS={'PASS' if not missing_files else 'FAIL'}")
    print(f"LOCAL_IMPORT_CLOSURE={'PASS' if not missing_imports else 'FAIL'}")
    if missing_files or missing_imports:
        for item in missing_files:
            print(f"MISSING_ENTRYPOINT={item}")
        for item in sorted(missing_imports):
            print(f"MISSING_LOCAL_IMPORT={item}")
        print("INCOMPLETE_LOCAL_DEPENDENCY_RELEASE_CAN_PROMOTE=NO")
        return 1

    if args.static_only:
        print("STATIC_RELEASE_CHECK=PASS")
        return 0

    entry_modules = [
        ".".join(Path(relative).with_suffix("").parts[1:])
        for relative in entrypoints
    ]
    module_symbols = {}
    for spec in args.symbol:
        module, separator, symbol = spec.partition(":")
        if not separator or not module or not symbol:
            print(f"INVALID_SYMBOL_SPEC={spec}", flush=True)
            return 2
        module_symbols[module] = symbol
    modules_to_import = list(dict.fromkeys(([] if args.no_entrypoint_import else entry_modules) + args.module + list(module_symbols)))
    forbidden = [p.resolve() for p in (args.active_release, args.canonical_source_root) if p]
    for module in modules_to_import:
        status, _, _ = import_probe(root, module, args.module_timeout, forbidden, module_symbols.get(module))
        if status != "PASS":
            print(f"RELEASE_IMPORT=FAIL MODULE={module} RESULT={status}", flush=True)
            print("INCOMPLETE_LOCAL_DEPENDENCY_RELEASE_CAN_PROMOTE=NO", flush=True)
            return 1
    print("RELEASE_IMPORT=PASS")
    manifest = root / "RELEASE_MANIFEST.sha256"
    if manifest.exists():
        failed = []
        for line in manifest.read_text().splitlines():
            expected, rel = line.split(maxsplit=1)
            path = root / rel.lstrip("* ")
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                failed.append(rel)
        if failed:
            print("MANIFEST_HASH=FAIL")
            for path in failed:
                print(f"MANIFEST_MISMATCH={path}")
            return 1
        print("MANIFEST_HASH=PASS")
        source_hash_path = root / "RELEASE_SOURCE_HASH"
        if source_hash_path.exists():
            actual_source_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
            expected_source_hash = source_hash_path.read_text().strip()
            if actual_source_hash != expected_source_hash:
                print("RELEASE_SOURCE_HASH=FAIL")
                return 1
            print("RELEASE_SOURCE_HASH=PASS")
        else:
            print("RELEASE_SOURCE_HASH=NOT_PRESENT")
    else:
        print("MANIFEST_HASH=MISSING")
        return 1
    print("INCOMPLETE_LOCAL_DEPENDENCY_RELEASE_CAN_PROMOTE=NO")
    return 0


if __name__ == "__main__":
    if "--_worker" in sys.argv:
        raise SystemExit(main())
    raise SystemExit(run_bounded_worker())
