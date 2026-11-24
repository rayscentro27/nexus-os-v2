"""Deterministic Creative asset ingestion into canonical private storage."""
from __future__ import annotations

import hashlib
import mimetypes
import os
import subprocess
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from nexus_agent_platform.creative.r2_storage import CloudflareR2StorageAdapter
from nexus_agent_platform.governed.persistence import append_record
from nexus_agent_platform.marketing_supabase_state import (
    find_asset_by_content_hash, get_asset_metadata, metadata_store_configured, record_asset_metadata,
)


class AssetPersistenceError(RuntimeError):
    pass


def _receipt_exists(receipt_id: str) -> bool:
    from nexus_agent_platform.governed.persistence import collection_path
    target = collection_path("creative_receipts")
    if not target.exists():
        return False
    with target.open("r", encoding="utf-8") as stream:
        for line in stream:
            try:
                if __import__("json").loads(line).get("receipt_id") == receipt_id:
                    return True
            except (ValueError, AttributeError):
                continue
    return False


class AssetPersistenceBot:
    bot_id = "ASSET_PERSISTENCE_BOT"
    bot_class = "DETERMINISTIC_WORKER"
    model_required = False

    def __init__(self, storage: Any | None = None, output_resolver: Any | None = None):
        self.storage = storage
        self.output_resolver = output_resolver

    def ingest(self, source: str | Path | Mapping[str, Any], *, work_order_id: str, campaign_id: str,
               asset_id: str, asset_type: str, format: str, provider: str,
               model: str | None, model_profile: str | None,
               execution_environment: str, parent_asset_id: str | None = None,
               variant: str | None = None, version: int = 1,
               approval_status: str = "PENDING", created_by: str = "CREATIVE",
               brand_id: str | None = None) -> dict[str, Any]:
        if isinstance(source, Mapping):
            if not self.output_resolver:
                raise AssetPersistenceError("PROVIDER_OUTPUT_RESOLVER_UNAVAILABLE")
            try:
                source = self.output_resolver(source)
            except Exception as exc:
                raise AssetPersistenceError("TEMPORARY_PROVIDER_OUTPUT_RETRIEVAL_FAILED") from exc
        path = Path(source)
        if not path.is_file() or path.is_symlink():
            raise AssetPersistenceError("ARTIFACT_NOT_A_REGULAR_FILE")
        size = path.stat().st_size
        if size <= 0 or size > int(os.environ.get("NEXUS_CREATIVE_MAX_ASSET_BYTES", str(512 * 1024 * 1024))):
            raise AssetPersistenceError("ARTIFACT_SIZE_OUT_OF_BOUNDS")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if not metadata_store_configured():
            raise AssetPersistenceError("ASSET_METADATA_STORE_UNAVAILABLE")
        try:
            store = self.storage or CloudflareR2StorageAdapter()
        except Exception as exc:
            raise AssetPersistenceError("CANONICAL_STORAGE_UNAVAILABLE") from exc
        suffix = path.suffix.lower().lstrip(".") or "bin"
        safe_brand = str(brand_id or "unbranded")[:100]
        for segment in (safe_brand, campaign_id, asset_id):
            if not segment or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-" for char in str(segment)):
                raise AssetPersistenceError("ASSET_PATH_IDENTIFIER_INVALID")
        key = f"creative/{safe_brand}/{campaign_id}/{asset_id}/v{max(1, int(version))}/master.{suffix}"
        try:
            existing = find_asset_by_content_hash(digest)
            if existing and existing.get("provenance", {}).get("storage_provider") == "CLOUDFLARE_R2":
                existing_key = existing.get("provenance", {}).get("storage_path")
                verified_existing = store.head(existing_key) if existing_key else {"exists": False}
            else:
                existing_key, verified_existing = None, {"exists": False}
            if existing_key and verified_existing.get("exists") and verified_existing.get("content_hash") == digest:
                key = existing_key
                verified = verified_existing
                receipt = {**verified_existing, "verified": True, "deduplicated": True}
            elif isinstance(store, CloudflareR2StorageAdapter):
                receipt = store.put(path, key, content_hash=digest,
                    mime_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream")
                verified = store.head(key)
            else:
                receipt = store.put(path, key, content_hash=digest,
                    mime_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream")
                verified = store.head(key)
        except Exception as exc:
            raise AssetPersistenceError("CANONICAL_STORAGE_UNAVAILABLE") from exc
        if not receipt.get("verified") or not verified.get("exists") or verified.get("content_hash") != digest:
            raise AssetPersistenceError("CANONICAL_STORAGE_VERIFICATION_FAILED")
        provider_name = str(receipt.get("provider") or "CLOUDFLARE_R2")
        if provider_name != "CLOUDFLARE_R2":
            raise AssetPersistenceError("NON_CANONICAL_STORAGE_PROVIDER_BLOCKED")
        receipt_id = f"generation:{work_order_id}:{digest[:16]}"
        dimensions: dict[str, Any] = {}
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            try:
                from PIL import Image
                with Image.open(path) as image:
                    dimensions = {"width": image.width, "height": image.height}
            except Exception:
                dimensions = {}
        elif path.suffix.lower() == ".mp4" and shutil.which("ffprobe"):
            try:
                probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height", "-of", "json", str(path)], check=True, capture_output=True, text=True, timeout=15)
                data = json.loads(probe.stdout); stream = next((x for x in data.get("streams", []) if x.get("width")), {})
                dimensions = {"width": stream.get("width"), "height": stream.get("height"), "duration_ms": round(float(data.get("format", {}).get("duration", 0)) * 1000)}
            except Exception:
                dimensions = {}
        metadata = {
            "asset_id": asset_id, "campaign_id": campaign_id, "brand_id": brand_id,
            "parent_asset_id": parent_asset_id, "work_order_id": work_order_id,
            "asset_type": asset_type, "format": format, "platform": None,
            "dimensions": {k: dimensions[k] for k in ("width", "height") if dimensions.get(k) is not None}, "duration_ms": dimensions.get("duration_ms"), "hook": None, "angle": None,
            "variant": variant, "version": max(1, int(version)),
            "creative_tool": "NEXUS_CREATIVE_WORKFLOW", "execution_environment": execution_environment,
            "provider": provider, "model": model, "model_profile": model_profile,
            "storage_provider": provider_name, "storage_bucket": getattr(store, "bucket", os.environ.get("R2_BUCKET")),
            "storage_path": key, "thumbnail_path": None, "content_hash": digest,
            "approval_status": approval_status, "created_by": created_by,
            "generation_receipt_id": receipt_id,
            "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            "size_bytes": size, "canonical_storage_verified": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "cost_if_available": None,
        }
        metadata["generation_receipt"] = {
            "receipt_id": receipt_id, "work_order_id": work_order_id,
            "campaign_id": campaign_id, "asset_id": asset_id,
            "r2_object_key": key, "r2_object_verified": True,
            "content_hash": digest, "size_bytes": size,
            "storage_provider": "CLOUDFLARE_R2", "created_at": metadata["created_at"],
            "receipt_state": "CANONICAL_OBJECT_VERIFIED_METADATA_REGISTERED_WITH_ASSET",
        }
        storage_receipt = dict(receipt)
        try:
            record_asset_metadata(asset_id=asset_id, campaign_id=campaign_id,
                project_id="NEXUS", asset_type=asset_type, artifact_ref=key,
                sha256=digest, size_bytes=size, mime_type=metadata["mime_type"],
                status="CANONICAL", approval_state=approval_status,
                version=version, provenance=metadata, require_configured=True)
        except Exception as exc:
            raise AssetPersistenceError("ASSET_METADATA_WRITE_FAILED") from exc
        try:
            persisted = get_asset_metadata(asset_id)
        except Exception as exc:
            raise AssetPersistenceError("ASSET_METADATA_WRITE_FAILED") from exc
        persisted_payload = (persisted or {}).get("payload") or {}
        persisted_provenance = persisted_payload.get("provenance") or {}
        if (not persisted or persisted_payload.get("campaign_id") != campaign_id
                or persisted_provenance.get("content_hash") != digest
                or persisted_provenance.get("storage_path") != key
                or (persisted_provenance.get("generation_receipt") or {}).get("receipt_id") != receipt_id):
            raise AssetPersistenceError("ASSET_METADATA_VERIFICATION_FAILED")
        receipt = {"receipt_id": receipt_id, "work_order_id": work_order_id,
            "campaign_id": campaign_id, "asset_id": asset_id,
            "storage_provider": provider_name, "storage_bucket": metadata["storage_bucket"],
            "storage_path": key, "content_hash": digest, "size_bytes": size,
            "status": "CANONICAL_STORAGE_AND_METADATA_VERIFIED",
            "temp_location": "TEMP_WORKER_OUTPUT", "created_at": metadata["created_at"],
            "canonicalized": True, "cleanup_eligible_at": None,
            "execution_environment": execution_environment}
        append_record("creative_receipts", receipt)
        if not _receipt_exists(receipt_id):
            raise AssetPersistenceError("GENERATION_RECEIPT_VERIFICATION_FAILED")
        return {"asset_id": asset_id, "storage_provider": provider_name,
                "storage_bucket": metadata["storage_bucket"], "storage_path": key,
                "content_hash": digest, "campaign_id": campaign_id,
                "version": max(1, int(version)), "status": "CANONICAL_ASSET_REGISTERED",
                "generation_receipt_id": receipt_id, "metadata": metadata, "receipt": receipt,
                "deduplicated": bool(storage_receipt.get("deduplicated"))}
