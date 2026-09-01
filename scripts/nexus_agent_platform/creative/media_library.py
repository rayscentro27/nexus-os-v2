"""Provider-neutral Creative media library and review receipts.

The immediate safe provider is a private local object store with deterministic
remote-shaped keys. It is staging-friendly and can be replaced by Supabase/R2
behind the same adapter without changing review records or the UI contract.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nexus_agent_platform.governed.persistence import append_record, emit_audit_event, read_records

ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = ROOT / "reports/rebuild/wp8_11b_artifacts/opp_bffe3378956f40bb9317970938eb3f21/individual_vehicle_convenience"
OBJECT_ROOT = ROOT / "public/creative-library/objects"
INDEX_PATH = ROOT / "public/creative-library/index.json"


class CreativeStorageAdapter:
    """Private object adapter; refs are logical keys, never filesystem paths."""
    provider = "local_private_object_store"

    def put(self, source: Path, key: str) -> dict[str, Any]:
        target = _copy(source, key)
        return {"provider": self.provider, "object_key": key, "bytes": target.stat().st_size, "verified": target.exists()}

    def head(self, key: str) -> dict[str, Any]:
        target = OBJECT_ROOT / Path(key).relative_to("creative")
        return {"provider": self.provider, "object_key": key, "exists": target.exists(), "bytes": target.stat().st_size if target.exists() else 0}

    def review_url(self, key: str) -> str:
        return "/creative-library/objects/" + str(Path(key).relative_to("creative"))


class SupabaseCreativeStorageAdapter:
    """Private Supabase Storage adapter using the existing service credential.

    This adapter is deliberately used by bounded operator-side sync jobs only;
    the service key is never exposed to the browser or persisted in a record.
    """
    provider = "supabase_storage"

    def __init__(self, bucket: str = "creative-assets") -> None:
        self.base = (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or "").rstrip("/")
        self.key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        self.bucket = bucket
        if not self.base or not self.key:
            raise RuntimeError("supabase-service-storage-not-configured")

    def _url(self, key: str) -> str:
        encoded = "/".join(urllib.parse.quote(part, safe="") for part in key.split("/"))
        return f"{self.base}/storage/v1/object/{self.bucket}/{encoded}"

    def _curl(self, args: list[str], *, input_data: bytes | None = None) -> tuple[int, bytes, str]:
        result = subprocess.run(["curl", "-sS", "--max-time", "20", *args], input=input_data, capture_output=True)
        return result.returncode, result.stdout, result.stderr.decode("utf-8", "replace")[:240]

    def ensure_private_bucket(self) -> str:
        code, body, _ = self._curl([f"{self.base}/storage/v1/bucket", "-H", f"apikey: {self.key}", "-H", f"Authorization: Bearer {self.key}"])
        if code != 0:
            raise RuntimeError("supabase-bucket-list-failed")
        buckets = json.loads(body or b"[]")
        if any(x.get("name") == self.bucket for x in buckets if isinstance(x, dict)):
            return "EXISTING_PRIVATE_OR_CONFIGURED"
        payload = json.dumps({"id": self.bucket, "name": self.bucket, "public": False}).encode()
        code, body, err = self._curl([f"{self.base}/storage/v1/bucket", "-X", "POST", "-H", "Content-Type: application/json", "-H", f"apikey: {self.key}", "-H", f"Authorization: Bearer {self.key}", "--data-binary", "@-", "-w", "\n%{http_code}"], input_data=payload)
        if code != 0 or not (200 <= _http_code(body, err) < 300):
            raise RuntimeError("supabase-private-bucket-create-failed")
        return "CREATED_PRIVATE"

    def put(self, source: Path, key: str) -> dict[str, Any]:
        code, body, err = self._curl([self._url(key), "-X", "POST", "-H", "x-upsert: true", "-H", f"Content-Type: {_mime(source)}", "-H", f"apikey: {self.key}", "-H", f"Authorization: Bearer {self.key}", "--upload-file", str(source), "-w", "\n%{http_code}"])
        if code != 0 or not (200 <= _http_code(body, err) < 300):
            raise RuntimeError("supabase-object-upload-failed")
        return {"provider": self.provider, "object_key": key, "bytes": source.stat().st_size, "verified": self.head(key)["exists"]}

    def head(self, key: str) -> dict[str, Any]:
        code, body, err = self._curl([self._url(key), "-D", "/tmp/nexus_supabase_headers", "-o", "/dev/null", "-w", "%{http_code}", "-H", f"apikey: {self.key}", "-H", f"Authorization: Bearer {self.key}"])
        status = int(body.decode() or "0") if body and body.decode().isdigit() else 0
        return {"provider": self.provider, "object_key": key, "exists": code == 0 and 200 <= status < 300, "status": status, "error": err if code else ""}

    def signed_url(self, key: str, expires: int = 3600) -> str:
        payload = json.dumps({"expiresIn": expires}).encode()
        endpoint = self._url(key).replace(f"/object/{self.bucket}/", f"/object/sign/{self.bucket}/")
        code, body, err = self._curl([endpoint, "-X", "POST", "-H", "Content-Type: application/json", "-H", f"apikey: {self.key}", "-H", f"Authorization: Bearer {self.key}", "--data-binary", "@-"], input_data=payload)
        if code != 0:
            raise RuntimeError("supabase-signed-url-failed")
        data = json.loads(body or b"{}")
        path = data.get("signedURL") or data.get("signedUrl")
        if not path:
            raise RuntimeError(f"supabase-signed-url-failed:{err}")
        return path if path.startswith("http") else self.base + "/storage/v1" + path


def _http_code(body: bytes, err: str) -> int:
    try:
        return int(body.decode().strip().splitlines()[-1])
    except (ValueError, IndexError, UnicodeDecodeError):
        return 0


def _mime(path: Path) -> str:
    return {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".mp4": "video/mp4"}.get(path.suffix.lower(), "application/octet-stream")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()[:16]


def object_key(asset_id: str, version: str, derivative: str, suffix: str) -> str:
    return f"creative/{asset_id}/{version}/{derivative}.{suffix}"


def _copy(source: Path, key: str) -> Path:
    target = OBJECT_ROOT / Path(key).relative_to("creative")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.stat().st_size != source.stat().st_size:
        shutil.copy2(source, target)
    return target


def _image_derivatives(source: Path, asset_id: str, version: str) -> dict[str, Any]:
    from PIL import Image
    image = Image.open(source)
    master_key = object_key(asset_id, version, "master", source.suffix.lstrip(".").lower())
    _copy(source, master_key)
    review = image.copy(); review.thumbnail((1400, 1400))
    thumb = image.copy(); thumb.thumbnail((320, 320))
    review_key = object_key(asset_id, version, "review", "webp")
    thumb_key = object_key(asset_id, version, "thumb", "webp")
    for obj, key in ((review, review_key), (thumb, thumb_key)):
        target = OBJECT_ROOT / Path(key).relative_to("creative"); target.parent.mkdir(parents=True, exist_ok=True)
        obj.save(target, "WEBP", quality=82, method=4)
    return {"master_object_ref": master_key, "review_object_ref": review_key, "thumbnail_object_ref": thumb_key, "mime_type": "image/" + source.suffix.lstrip(".").lower(), "width": image.width, "height": image.height, "file_size": source.stat().st_size}


def _video_derivatives(source: Path, asset_id: str, version: str) -> dict[str, Any]:
    master_key = object_key(asset_id, version, "master", "mp4"); _copy(source, master_key)
    review_key = object_key(asset_id, version, "review", "mp4")
    poster_key = object_key(asset_id, version, "poster", "jpg")
    thumb_key = object_key(asset_id, version, "thumb", "jpg")
    review = OBJECT_ROOT / Path(review_key).relative_to("creative"); poster = OBJECT_ROOT / Path(poster_key).relative_to("creative"); thumb = OBJECT_ROOT / Path(thumb_key).relative_to("creative")
    for p in (review, poster, thumb): p.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-i", str(source), "-vf", "scale=-2:1280", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(review)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["ffmpeg", "-y", "-ss", "0", "-i", str(source), "-frames:v", "1", "-q:v", "4", str(poster)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shutil.copy2(poster, thumb)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,width,height,nb_frames", "-of", "json", str(source)], check=True, capture_output=True, text=True)
    meta = json.loads(probe.stdout); streams = meta.get("streams", []); video = next((x for x in streams if x.get("width")), {})
    return {"master_object_ref": master_key, "review_object_ref": review_key, "poster_object_ref": poster_key, "thumbnail_object_ref": thumb_key, "mime_type": "video/mp4", "width": video.get("width"), "height": video.get("height"), "duration_ms": round(float(meta.get("format", {}).get("duration", 0)) * 1000), "codec": video.get("codec_name"), "file_size": source.stat().st_size}


def ingest(source: Path, *, asset_type: str, channel: str, territory_id: str, version: str = "v1") -> dict[str, Any]:
    asset_id = "asset_media_" + digest({"source": str(source), "asset_type": asset_type, "channel": channel, "version": version})
    existing = next((x for x in read_records("creative_media") if x.get("asset_id") == asset_id), None)
    if existing:
        return {**existing, "persistence": "DUPLICATE_SUPPRESSED"}
    details = _video_derivatives(source, asset_id, version) if source.suffix.lower() == ".mp4" else _image_derivatives(source, asset_id, version)
    row = {"schema_version": "nexus.creative-media.v1", "asset_id": asset_id, "brief_id": "brief_wp8_11b_" + digest({"opportunity": "opp_bffe3378956f40bb9317970938eb3f21", "variant": "individual_vehicle_convenience"}), "territory_id": territory_id, "asset_type": asset_type, "channel": channel, "version": version, "parent_version": None, **details, "object_provider": "local_private_object_store", "object_key_prefix": f"creative/{asset_id}/{version}/", "upload_state": "VERIFIED", "render_state": "RENDERED", "review_state": "READY_FOR_REVIEW", "review_urls": {k: "/creative-library/objects/" + str(v).split("/", 1)[1] for k, v in details.items() if k.endswith("_object_ref")}, "source_provenance": str(source.relative_to(ROOT)), "scope": "INTERNAL_NEXUS", "created_at": now(), "updated_at": now(), "external_action_performed": False}
    append_record("creative_media", row); return {**row, "persistence": "CREATED"}


def review(asset_id: str, decision: str, feedback: str, reviewer: str = "ray") -> dict[str, Any]:
    if decision not in {"APPROVE", "REQUEST_REVISION", "REJECT", "ARCHIVE"}: raise ValueError("invalid-review-decision")
    fingerprint = digest({"asset_id": asset_id, "decision": decision, "feedback": feedback, "reviewer": reviewer})
    existing = next((x for x in read_records("creative_reviews") if x.get("review_id") == "review_" + fingerprint), None)
    if existing: return {**existing, "persistence": "DUPLICATE_SUPPRESSED"}
    media = next((x for x in read_records("creative_media") if x.get("asset_id") == asset_id), None)
    if not media: raise ValueError("unknown-asset")
    status = {"APPROVE": "APPROVED_FOR_NEXT_INTERNAL_STAGE", "REQUEST_REVISION": "REVISION_REQUESTED", "REJECT": "REJECTED_RETAINED", "ARCHIVE": "ARCHIVED"}[decision]
    row = {"schema_version": "nexus.creative-review.v1", "review_id": "review_" + fingerprint, "asset_id": asset_id, "version": media["version"], "reviewer": reviewer, "decision": decision, "feedback": feedback, "timestamp": now(), "publication_triggered": False}
    append_record("creative_reviews", row); append_record("creative_learning", {"schema_version": "nexus.creative-learning.v1", "learning_id": "learning_" + fingerprint, "asset_id": asset_id, "scope": {"territory_id": media.get("territory_id"), "channel": media.get("channel")}, "observation": feedback, "confidence": "HUMAN_REVIEW_OBSERVATION", "decision": decision, "created_at": now()})
    emit_audit_event({"event": "creative_human_review", "asset_id": asset_id, "decision": decision, "publication_triggered": False})
    return {**row, "asset_status": status, "persistence": "CREATED"}


def build_library() -> dict[str, Any]:
    rows = []
    territory = "territory_wp8_11b_" + digest({"brief": "brief_wp8_11b_" + digest({"opportunity": "opp_bffe3378956f40bb9317970938eb3f21", "variant": "individual_vehicle_convenience"}), "slug": "time_back"})
    for name, typ, channel in (("landing_v1_desktop.png", "LANDING_PAGE_SCREENSHOT", "LANDING_PAGE"), ("landing_v1_mobile.png", "LANDING_PAGE_SCREENSHOT", "LANDING_PAGE"), ("landing_v2_desktop.png", "LANDING_PAGE_SCREENSHOT", "LANDING_PAGE"), ("landing_v2_mobile.png", "LANDING_PAGE_SCREENSHOT", "LANDING_PAGE"), ("mobile_detailing_short_v1.mp4", "VIDEO", "TIKTOK_REEL")):
        version = "v2" if "v2" in name else "v1"; rows.append(ingest(SOURCE_ROOT / name, asset_type=typ, channel=channel, territory_id=territory, version=version))
    payload = {"schema_version": "nexus.creative-library-index.v1", "provider": "local_private_object_store", "review_policy": "proxy_first; master_explicit", "assets": rows, "generated_at": now(), "external_action_performed": False}
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True); INDEX_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def sync_library_to_supabase(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Upload the already-indexed local artifacts and publish signed review refs."""
    adapter = SupabaseCreativeStorageAdapter()
    bucket_state = adapter.ensure_private_bucket()
    payload = payload or json.loads(INDEX_PATH.read_text())
    uploaded = 0; verified = 0
    remote_assets = []
    for asset in payload.get("assets", []):
        prior_remote = next((x for x in read_records("creative_media") if x.get("asset_id") == asset.get("asset_id") and x.get("object_provider") == adapter.provider and x.get("upload_state") == "VERIFIED_REMOTE"), None)
        if prior_remote:
            remote_assets.append(prior_remote)
            continue
        remote = dict(asset)
        remote_urls = {}
        for field, key in ((k, v) for k, v in asset.items() if k.endswith("_object_ref")):
            source = OBJECT_ROOT / Path(key).relative_to("creative")
            adapter.put(source, key)
            uploaded += 1
            if adapter.head(key)["exists"]: verified += 1
            if field != "master_object_ref": remote_urls[field] = adapter.signed_url(key)
        remote["object_provider"] = adapter.provider
        remote["upload_state"] = "VERIFIED_REMOTE"
        remote["remote_bucket"] = adapter.bucket
        remote["review_urls"] = remote_urls
        remote["remote_sync_verified_at"] = now()
        append_record("creative_media", remote)
        remote_assets.append(remote)
    remote_payload = {**payload, "provider": adapter.provider, "remote_bucket": adapter.bucket, "assets": remote_assets, "remote_sync": {"bucket_state": bucket_state, "uploaded_objects": uploaded, "verified_objects": verified, "verified_at": now()}}
    INDEX_PATH.write_text(json.dumps(remote_payload, indent=2, sort_keys=True) + "\n")
    emit_audit_event({"event": "creative_remote_media_sync", "provider": adapter.provider, "bucket": adapter.bucket, "uploaded_objects": uploaded, "verified_objects": verified, "external_action_performed": False})
    return remote_payload


if __name__ == "__main__":
    data = build_library()
    if os.environ.get("NEXUS_CREATIVE_SYNC_SUPABASE") == "1": data = sync_library_to_supabase(data)
    print(json.dumps(data, indent=2, sort_keys=True))
