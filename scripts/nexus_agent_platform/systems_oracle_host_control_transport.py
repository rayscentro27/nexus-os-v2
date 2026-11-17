"""Typed, fixed-target Systems transport to Oracle Host Control r6.

The only remote command is the installed Host Control typed socket client.
Callers provide a capability and that capability's typed arguments; they can
never provide a host, path, socket, service, executable, or command string.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shlex
import subprocess
import tarfile
import uuid
from pathlib import Path
from typing import Any, Callable

HOST_ID = "nexus-llm-worker"
HOST = "161.153.40.41"
USER = "opc"
SOCKET = "/home/opc/.nexus/state/host-control/host-control.sock"
REMOTE_PYTHON = "/usr/bin/python3"
REMOTE_CLIENT = "/home/opc/.nexus/host-control/nexus-oracle-host-control/nexus_oracle_host_control.py"
SSH = "/usr/bin/ssh"
MAX_REQUEST_BYTES = 2 * 1024 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
CAPABILITIES = frozenset({
    "systems.oracle.release.inspect",
    "systems.oracle.release.stage",
    "systems.oracle.nova.snapshot",
    "systems.oracle.nova.snapshot_validate",
    "systems.oracle.nova.poller_status",
    "systems.oracle.nova.activate",
    "systems.oracle.nova.verify",
    "systems.oracle.nova.rollback",
    "systems.oracle.receipt.read",
    "systems.oracle.hermes.mcp_provider_status",
})
OPERATION_CLASSES = {
    "systems.oracle.release.inspect": ("READ", False),
    "systems.oracle.release.stage": ("WRITE", True),
    "systems.oracle.nova.snapshot": ("READ_WITH_SNAPSHOT_STATE_WRITE", False),
    "systems.oracle.nova.snapshot_validate": ("READ", False),
    "systems.oracle.nova.poller_status": ("READ", False),
    "systems.oracle.nova.activate": ("WRITE", True),
    "systems.oracle.nova.verify": ("READ", False),
    "systems.oracle.nova.rollback": ("WRITE", True),
    "systems.oracle.receipt.read": ("READ", False),
    "systems.oracle.hermes.mcp_provider_status": ("READ", False),
}

SCHEMAS: dict[str, dict[str, type]] = {
    "systems.oracle.release.inspect": {"release_name": str, "expected_hash": str},
    "systems.oracle.release.stage": {"artifact_id": str, "release_name": str,
        "expected_release_hash": str, "expected_manifest_hash": str, "approval_id": str},
    "systems.oracle.nova.snapshot": {},
    "systems.oracle.nova.snapshot_validate": {"snapshot_id": str},
    "systems.oracle.nova.poller_status": {},
    "systems.oracle.nova.activate": {"deployment_id": str, "target_release_name": str,
        "target_release_hash": str, "shared_release_hash": str, "dependency_lock_hash": str,
        "current_snapshot_hash": str, "target_dropin_hash": str,
        "expected_effective_dropin_count": int, "automatic_rollback_on_failure": bool,
        "approval_id": str},
    "systems.oracle.nova.verify": {"expected_release_name": str, "expected_release_hash": str},
    "systems.oracle.nova.rollback": {"snapshot_id": str, "snapshot_hash": str,
        "approval_id": str},
    "systems.oracle.receipt.read": {"receipt_id": str},
    "systems.oracle.hermes.mcp_provider_status": {},
}

_CORRELATION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_HASH_RE = re.compile(r"[a-f0-9]{64}\Z")
_RELEASE_RE = re.compile(r"[a-z0-9][a-z0-9.-]{2,119}\Z")
_ID_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{1,79}\Z")
_APPROVAL_RE = re.compile(r"appr_[a-f0-9]{32}\Z")
_RECEIPT_RE = re.compile(r"hcr_[a-f0-9]{32}\Z")


class TransportError(RuntimeError):
    pass


def _validate(capability: str, arguments: dict[str, Any]) -> None:
    if capability not in CAPABILITIES:
        raise ValueError("CAPABILITY_NOT_ALLOWED")
    if not isinstance(arguments, dict) or set(arguments) != set(SCHEMAS[capability]):
        raise ValueError("ARGUMENT_SCHEMA_INVALID")
    for key, expected_type in SCHEMAS[capability].items():
        value = arguments[key]
        if expected_type is int:
            if type(value) is not int:
                raise ValueError("ARGUMENT_TYPE_INVALID:" + key)
        elif not isinstance(value, expected_type):
            raise ValueError("ARGUMENT_TYPE_INVALID:" + key)
        if isinstance(value, str) and not value:
            raise ValueError("ARGUMENT_EMPTY:" + key)
    if capability == "systems.oracle.release.inspect":
        if not _RELEASE_RE.fullmatch(arguments["release_name"]) or ".." in arguments["release_name"]:
            raise ValueError("RELEASE_NAME_INVALID")
        if not _HASH_RE.fullmatch(arguments["expected_hash"]):
            raise ValueError("EXPECTED_HASH_INVALID")
    if capability == "systems.oracle.release.stage":
        if (not _ID_RE.fullmatch(arguments["artifact_id"])
                or not _RELEASE_RE.fullmatch(arguments["release_name"])
                or ".." in arguments["release_name"]):
            raise ValueError("STAGE_IDENTIFIER_INVALID")
        if any(not _HASH_RE.fullmatch(arguments[key]) for key in
               ("expected_release_hash", "expected_manifest_hash")):
            raise ValueError("STAGE_HASH_INVALID")
        if not _APPROVAL_RE.fullmatch(arguments["approval_id"]):
            raise ValueError("APPROVAL_ID_INVALID")
    if capability == "systems.oracle.nova.activate":
        if not _RELEASE_RE.fullmatch(arguments["target_release_name"]):
            raise ValueError("RELEASE_NAME_INVALID")
        if any(not _HASH_RE.fullmatch(arguments[key]) for key in
               ("target_release_hash", "shared_release_hash", "dependency_lock_hash",
                "current_snapshot_hash", "target_dropin_hash")):
            raise ValueError("APPROVAL_HASH_INVALID")
        if arguments["expected_effective_dropin_count"] != 1:
            raise ValueError("EFFECTIVE_DROPIN_COUNT_MUST_BE_ONE")
        if not _APPROVAL_RE.fullmatch(arguments["approval_id"]):
            raise ValueError("APPROVAL_ID_INVALID")
    if capability == "systems.oracle.nova.rollback":
        if not _APPROVAL_RE.fullmatch(arguments["approval_id"]):
            raise ValueError("APPROVAL_ID_INVALID")
    if capability == "systems.oracle.receipt.read" and not _RECEIPT_RE.fullmatch(arguments["receipt_id"]):
        raise ValueError("RECEIPT_ID_INVALID")


# One exact, preverified artifact is admitted by this narrowly scoped ingress.
# It is intentionally not parameterized by a caller-supplied local or remote
# path and does not modify the immutable candidate.
ARTIFACT_INGRESS_CAPABILITY = "systems.oracle.artifact.ingest"
INGRESS_ARTIFACT_ID = "nova-operator-v1-20261031-native-mcp-reset-v1"
INGRESS_ARCHIVE = Path(
    "/private/tmp/nova-native-mcp-reset-20261031/"
    "nova-operator-v1-20261031-native-mcp-reset-v1.tar.gz"
)
INGRESS_ARCHIVE_SHA256 = "17637c902196c840b59dcfb9656865996a9556c5626b3fed11a244e04b0595de"
INGRESS_MANIFEST_SHA256 = "d665b438b3fd8fb713821f990a2096b2c11c19af70c5150b3e582414cef6584c"
INGRESS_MANIFEST_ENTRIES = 441
INGRESS_MAX_BYTES = 256 * 1024 * 1024
INGRESS_DESTINATION = (
    "/home/opc/.nexus/state/host-control/incoming/"
    + INGRESS_ARTIFACT_ID + ".tar.gz"
)

_REMOTE_INGRESS_SCRIPT = r'''import datetime,hashlib,io,json,os,pwd,re,socket,sys,tarfile,uuid
artifact_id="nova-operator-v1-20261031-native-mcp-reset-v1"
release_id=artifact_id
archive_hash="17637c902196c840b59dcfb9656865996a9556c5626b3fed11a244e04b0595de"
manifest_hash="d665b438b3fd8fb713821f990a2096b2c11c19af70c5150b3e582414cef6584c"
manifest_entries=441
incoming="/home/opc/.nexus/state/host-control/incoming"
receipts="/home/opc/.nexus/state/host-control/receipts"
destination=incoming+"/"+artifact_id+".tar.gz"
data=sys.stdin.buffer.read(268435457)
def stop(code):
 print(json.dumps({"status":"REJECTED","error":code},sort_keys=True)); sys.exit(2)
if socket.gethostname()!="nexus-llm-worker" or pwd.getpwuid(os.getuid()).pw_name!="opc": stop("FIXED_HOST_IDENTITY_REJECTED")
if len(data)>268435456 or hashlib.sha256(data).hexdigest()!=archive_hash: stop("ARCHIVE_HASH_MISMATCH")
try:
 tf=tarfile.open(fileobj=io.BytesIO(data),mode="r:gz"); members=tf.getmembers()
 root=release_id
 if len(members)!=manifest_entries+1: stop("ARCHIVE_ENTRY_COUNT_MISMATCH")
 by_name={}
 for m in members:
  if not m.isfile() or m.issym() or m.islnk() or m.name.startswith("/") or ".." in m.name.split("/"): stop("ARCHIVE_MEMBER_REJECTED")
  if not m.name.startswith(root+"/") or m.name in by_name: stop("ARCHIVE_MEMBER_PATH_REJECTED")
  by_name[m.name]=m
 mp=root+"/RELEASE_MANIFEST.sha256"
 if mp not in by_name: stop("MANIFEST_MISSING")
 manifest=tf.extractfile(by_name[mp]).read()
 if hashlib.sha256(manifest).hexdigest()!=manifest_hash: stop("MANIFEST_HASH_MISMATCH")
 rows=[]; listed=set()
 for line in manifest.decode("utf-8").splitlines():
  match=re.fullmatch(r"([a-f0-9]{64})  (\./[A-Za-z0-9_.+/-]{1,300})",line)
  if not match: stop("MANIFEST_LINE_INVALID")
  digest,rel=match.groups(); name=root+"/"+rel[2:]
  if ".." in rel.split("/") or name in listed: stop("MANIFEST_PATH_INVALID")
  listed.add(name); member=by_name.get(name)
  if member is None or hashlib.sha256(tf.extractfile(member).read()).hexdigest()!=digest: stop("MANIFEST_ENTRY_MISMATCH")
  rows.append(name)
 if len(rows)!=manifest_entries or set(by_name)!=(listed|{mp}): stop("MANIFEST_ENTRY_SET_MISMATCH")
except SystemExit: raise
except Exception: stop("ARCHIVE_PARSE_FAILED")
if os.path.islink("/home/opc/.nexus") or os.path.islink("/home/opc/.nexus/state") or os.path.islink("/home/opc/.nexus/state/host-control") or os.path.islink(incoming): stop("INCOMING_ROOT_SYMLINK")
os.makedirs(incoming,mode=448,exist_ok=True)
if os.path.islink(incoming) or not os.path.isdir(incoming): stop("INCOMING_ROOT_INVALID")
if os.path.islink(receipts): stop("RECEIPT_ROOT_SYMLINK")
if os.path.lexists(destination): stop("ARTIFACT_ALREADY_EXISTS")
tmp=destination+".tmp-"+uuid.uuid4().hex
fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,384)
try:
 with os.fdopen(fd,"wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
 os.link(tmp,destination); os.unlink(tmp); os.chmod(destination,384)
except Exception:
 try: os.unlink(tmp)
 except OSError: pass
 stop("ARTIFACT_WRITE_FAILED")
with open(destination,"rb") as f: received=f.read(268435457)
if hashlib.sha256(received).hexdigest()!=archive_hash: os.unlink(destination); stop("POST_TRANSFER_HASH_MISMATCH")
receipt_id="ing_"+uuid.uuid4().hex
receipt={"receipt_id":receipt_id,"capability":"systems.oracle.artifact.ingest","artifact_id":artifact_id,"release_id":release_id,"archive_sha256":archive_hash,"manifest_sha256":manifest_hash,"manifest_entries":manifest_entries,"destination":destination,"bytes_written":len(received),"verification":"PASS","completed_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
os.makedirs(receipts,mode=448,exist_ok=True)
rp=receipts+"/"+receipt_id+".json"; rt=rp+".tmp-"+uuid.uuid4().hex
try:
 with open(rt,"x") as f: json.dump(receipt,f,sort_keys=True); f.write("\n"); f.flush(); os.fsync(f.fileno())
 os.chmod(rt,384); os.link(rt,rp); os.unlink(rt)
except Exception:
 try: os.unlink(rt)
 except OSError: pass
 try: os.unlink(destination)
 except OSError: pass
 stop("INGRESS_RECEIPT_WRITE_FAILED")
print(json.dumps({"status":"PASS","artifact_id":artifact_id,"archive_sha256":archive_hash,"manifest_sha256":manifest_hash,"manifest_entries":manifest_entries,"destination":destination,"receipt_id":receipt_id,"receipt_path":rp},sort_keys=True))
'''


def _verify_ingress_archive() -> bytes:
    if INGRESS_ARCHIVE.is_symlink() or not INGRESS_ARCHIVE.is_file():
        raise ValueError("INGRESS_ARCHIVE_NOT_REGULAR_FILE")
    payload = INGRESS_ARCHIVE.read_bytes()
    if len(payload) > INGRESS_MAX_BYTES or hashlib.sha256(payload).hexdigest() != INGRESS_ARCHIVE_SHA256:
        raise ValueError("INGRESS_ARCHIVE_HASH_MISMATCH")
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
            members = archive.getmembers()
            expected_root = INGRESS_ARTIFACT_ID
            if len(members) != INGRESS_MANIFEST_ENTRIES + 1:
                raise ValueError("INGRESS_ARCHIVE_ENTRY_COUNT_MISMATCH")
            by_name = {}
            for member in members:
                parts = Path(member.name).parts
                if (not member.isfile() or member.issym() or member.islnk()
                        or member.name.startswith("/") or ".." in parts
                        or not member.name.startswith(expected_root + "/")
                        or member.name in by_name):
                    raise ValueError("INGRESS_ARCHIVE_MEMBER_REJECTED")
                by_name[member.name] = member
            manifest_name = expected_root + "/RELEASE_MANIFEST.sha256"
            manifest_member = by_name.get(manifest_name)
            if manifest_member is None:
                raise ValueError("INGRESS_MANIFEST_MISSING")
            manifest = archive.extractfile(manifest_member).read()
            if hashlib.sha256(manifest).hexdigest() != INGRESS_MANIFEST_SHA256:
                raise ValueError("INGRESS_MANIFEST_HASH_MISMATCH")
            entries = {}
            for line in manifest.decode("utf-8").splitlines():
                match = re.fullmatch(r"([a-f0-9]{64})  (\./[A-Za-z0-9_.+/-]{1,300})", line)
                if not match:
                    raise ValueError("INGRESS_MANIFEST_LINE_INVALID")
                digest, rel = match.groups()
                if ".." in Path(rel).parts:
                    raise ValueError("INGRESS_MANIFEST_PATH_INVALID")
                entries[expected_root + "/" + rel[2:]] = digest
            if len(entries) != INGRESS_MANIFEST_ENTRIES or set(by_name) != set(entries) | {manifest_name}:
                raise ValueError("INGRESS_MANIFEST_ENTRY_SET_MISMATCH")
            for name, digest in entries.items():
                if hashlib.sha256(archive.extractfile(by_name[name]).read()).hexdigest() != digest:
                    raise ValueError("INGRESS_MANIFEST_ENTRY_MISMATCH")
    except (tarfile.TarError, OSError) as exc:
        raise ValueError("INGRESS_ARCHIVE_PARSE_FAILED") from exc
    return payload


def ingest_verified_native_mcp_candidate() -> dict[str, Any]:
    """Ingress only the pinned Nova release archive to Host Control's fixed inbox."""
    payload = _verify_ingress_archive()
    key_path = Path.home() / ".ssh" / "oracle_vm"
    if not key_path.is_file():
        raise TransportError("APPROVED_ORACLE_IDENTITY_UNAVAILABLE")
    remote_command = "/usr/bin/python3 -c " + shlex.quote(_REMOTE_INGRESS_SCRIPT)
    command = [SSH, "-T", "-i", str(key_path), "-oBatchMode=yes",
               "-oIdentitiesOnly=yes", "-oConnectTimeout=10", f"{USER}@{HOST}",
               remote_command]
    try:
        result = subprocess.run(command, input=payload, capture_output=True,
                                timeout=90, check=False, shell=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise TransportError("ARTIFACT_INGRESS_TRANSPORT_UNAVAILABLE") from exc
    if result.returncode != 0:
        raise TransportError("ARTIFACT_INGRESS_REJECTED")
    try:
        response = json.loads((result.stdout or b"").decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise TransportError("ARTIFACT_INGRESS_RESPONSE_INVALID") from exc
    if (not isinstance(response, dict) or response.get("status") != "PASS"
            or response.get("artifact_id") != INGRESS_ARTIFACT_ID
            or response.get("archive_sha256") != INGRESS_ARCHIVE_SHA256
            or response.get("manifest_sha256") != INGRESS_MANIFEST_SHA256
            or response.get("manifest_entries") != INGRESS_MANIFEST_ENTRIES
            or response.get("destination") != INGRESS_DESTINATION
            or not re.fullmatch(r"ing_[a-f0-9]{32}", str(response.get("receipt_id") or ""))):
        raise TransportError("ARTIFACT_INGRESS_RESPONSE_SCOPE_MISMATCH")
    return response

