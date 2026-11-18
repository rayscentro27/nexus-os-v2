"""Canonical Cloudflare R2 object storage for Creative media bytes."""
from __future__ import annotations

import os
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class R2ConfigurationError(RuntimeError):
    pass


class CloudflareR2StorageAdapter:
    provider = "CLOUDFLARE_R2"

    def __init__(self, *, approval_verifier: Any | None = None) -> None:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts/ops"))
        from nexus_runtime_env import load_runtime_env
        load_runtime_env(allowed_keys={"R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"})
        required = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")
        missing = [key for key in required if not os.environ.get(key)]
        if missing:
            raise R2ConfigurationError("CANONICAL_STORAGE_UNAVAILABLE")
        self.bucket = os.environ["R2_BUCKET"]
        self.approval_verifier = approval_verifier
        self._run_started = time.monotonic()
        self.endpoint = f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com"
        from nexus_agent_platform.creative.r2_governance import _read, GOVERNOR_POLICY_PATH
        policy = _read(GOVERNOR_POLICY_PATH)
        job_type = os.environ.get("NEXUS_JOB_TYPE", "CREATIVE_ASSET_PERSISTENCE")
        limits = (policy["certification_limits"] if job_type == "NEXUS_R2_LIVE_CERTIFICATION"
                  else policy["production_limits"])
        max_runtime = int(limits.get("max_runtime_seconds", limits.get("production_max_runtime_seconds", 0)))
        if max_runtime <= 0 or time.monotonic() - self._run_started >= max_runtime:
            raise TimeoutError("R2_RUN_TIME_LIMIT_EXCEEDED")
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise R2ConfigurationError("R2_S3_CLIENT_UNAVAILABLE") from exc
        self.client = boto3.client("s3", endpoint_url=self.endpoint,
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            config=Config(retries={"max_attempts": min(3, int(limits.get("max_retries", 3))), "mode": "standard"}))

    def _governed(self, action: str, usage: dict[str, Any], operation: Any, *,
                  object_key: str = "", write: bool = False) -> Any:
        from nexus_agent_platform.creative.r2_governance import operation_estimate, reserve_process_run_usage, _read, GOVERNOR_POLICY_PATH
        from nexus_agent_platform.provider_enforcement import execute
        detail = operation_estimate(action, byte_count=int(usage.get("bytes", 0)))
        estimate = {key: value for key, value in detail.items()
                    if isinstance(value, (int, float, bool))}
        cfg = _read(GOVERNOR_POLICY_PATH)
        job_type = os.environ.get("NEXUS_JOB_TYPE", "CREATIVE_ASSET_PERSISTENCE")
        if action == "OBJECT_DELETE_CERTIFICATION_ONLY" and job_type != "NEXUS_R2_LIVE_CERTIFICATION":
            raise PermissionError("R2_CERTIFICATION_DELETE_ONLY")
        limits = (cfg["certification_limits"] if job_type == "NEXUS_R2_LIVE_CERTIFICATION"
                  else cfg["production_limits"])
        reserve_process_run_usage(os.environ.get("NEXUS_DURABLE_JOB_ID", ""), action, detail, limits)
        estimate["job_budget"] = {
            "max_requests": int(limits.get("max_class_a_operations_per_run", limits.get("production_max_operations_per_job", 0))
                                 + limits.get("max_class_b_operations_per_run", limits.get("production_max_operations_per_job", 0))),
            "max_response_bytes": int(limits.get("max_total_upload_bytes_per_run", limits.get("production_max_bytes_per_job", 0)) * 2),
            "max_estimated_cost": float(cfg["certification_cost_ceiling_usd"] if job_type == "NEXUS_R2_LIVE_CERTIFICATION"
                                         else limits.get("production_max_estimated_cost_usd_per_job", 0)),
        }
        byte_cap = int(limits.get("max_total_upload_bytes_per_run",
                                  limits.get("production_max_bytes_per_job", 0)))
        if int(usage.get("bytes", 0)) > int(limits.get("max_single_object_bytes", byte_cap)):
            raise PermissionError("R2_SINGLE_OBJECT_LIMIT_EXCEEDED")
        if int(usage.get("bytes", 0)) and int(usage.get("bytes", 0)) > byte_cap:
            raise PermissionError("R2_RUN_BYTE_LIMIT_EXCEEDED")
        if time.monotonic() - getattr(self, "_run_started", time.monotonic()) >= int(limits.get("max_runtime_seconds",
                limits.get("production_max_runtime_seconds", 0))):
            raise TimeoutError("R2_RUN_TIME_LIMIT_EXCEEDED")
        # Distinct request IDs prevent the governor's idempotency key from
        # treating a second legitimate HEAD of the same object as a replay.
        operation_id = uuid.uuid4().hex
        result = execute("CLOUDFLARE_R2", "creative_canonical_storage", action, estimate,
            operation, job_id=os.environ.get("NEXUS_DURABLE_JOB_ID"),
            job_type=job_type,
            correlation_id=os.environ.get("NEXUS_CORRELATION_ID"),
            project_id=os.environ.get("NEXUS_PROJECT_ID", "NEXUS"),
            purpose=f"CANONICAL_CREATIVE_ASSET:{action}:{object_key}:{operation_id}")
        from nexus_agent_platform.governed.persistence import append_record
        append_record("creative_provider_receipts", {"receipt_id": f"r2:{operation_id}",
            "receipt_type": "R2_STORAGE_OPERATION", "provider": self.provider, "operation": action,
            "bucket": self.bucket, "bytes": int(usage.get("bytes", 0)),
            "request_count": detail["requests"], "operation_count": detail["operations"],
            "upload_bytes": detail["upload_bytes"], "download_bytes": detail["download_bytes"],
            "class_a_count": detail["class_a_count"], "class_b_count": detail["class_b_count"],
            "object_count": detail["object_count"], "estimated_cost": detail["cost"],
            "storage_gb_month_estimate": detail["storage_gb_month"],
            "cost_estimate_mode": "BOUNDED_ADVISORY",
            "workflow_id": os.environ.get("NEXUS_WORKFLOW_ID"),
            "work_order_id": os.environ.get("NEXUS_DURABLE_JOB_ID"),
            "campaign_id": os.environ.get("NEXUS_CAMPAIGN_ID"),
            "created_at": datetime.now(timezone.utc).isoformat()})
        return result

    def head(self, key: str) -> dict[str, Any]:
        from botocore.exceptions import ClientError
        def read():
            try:
                return self.client.head_object(Bucket=self.bucket, Key=key)
            except ClientError as exc:
                if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
                    return None
                raise
        result = self._governed("OBJECT_GET_METADATA", {}, read, object_key=key)
        if result is None:
            return {"exists": False, "provider": self.provider, "bucket": self.bucket, "object_key": key}
        return {"exists": True, "provider": self.provider, "bucket": self.bucket,
                "object_key": key, "size_bytes": int(result.get("ContentLength", 0)),
                "content_hash": (result.get("Metadata") or {}).get("sha256"),
                "mime_type": result.get("ContentType")}

    def check_bucket(self) -> dict[str, Any]:
        def check():
            return self.client.head_bucket(Bucket=self.bucket)
        try:
            self._governed("BUCKET_HEAD", {}, check, object_key="bucket-metadata")
            return {"exists": True, "bucket": self.bucket, "provider": self.provider}
        except Exception:
            return {"exists": False, "bucket": self.bucket, "provider": self.provider}

    def put(self, source: Path, key: str, *, content_hash: str, mime_type: str) -> dict[str, Any]:
        source = Path(source)
        current = self.head(key)
        if current.get("exists"):
            if current.get("content_hash") != content_hash:
                raise RuntimeError("R2_OBJECT_KEY_CONTENT_CONFLICT")
            return {**current, "verified": True, "deduplicated": True}
        def write():
            self.client.upload_file(str(source), self.bucket, key,
                ExtraArgs={"ContentType": mime_type, "Metadata": {"sha256": content_hash}})
        self._governed("OBJECT_PUT", {"bytes": source.stat().st_size}, write, object_key=key, write=True)
        verified = self.head(key)
        if not verified.get("exists") or verified.get("content_hash") != content_hash:
            raise RuntimeError("R2_OBJECT_VERIFICATION_FAILED")
        return {**verified, "verified": True, "deduplicated": False}

    def signed_read_url(self, key: str, expires_seconds: int = 900) -> str:
        from nexus_agent_platform.creative.r2_governance import _read, GOVERNOR_POLICY_PATH
        policy = _read(GOVERNOR_POLICY_PATH)
        if not self.head(key).get("exists"):
            raise FileNotFoundError("R2_OBJECT_NOT_FOUND")
        ttl_policy = policy["certification_limits"]
        ttl = max(60, min(int(expires_seconds), int(ttl_policy["max_signed_url_ttl_seconds"])))
        return self._governed("SIGNED_READ_URL", {}, lambda: self.client.generate_presigned_url("get_object",
            Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=ttl), object_key=key)

    def get_to_file(self, key: str, target: Path, *, max_bytes: int = 50 * 1024 * 1024) -> dict[str, Any]:
        """Fetch a bounded object only after metadata confirms its size."""
        target = Path(target)
        metadata = self.head(key)
        if not metadata.get("exists"):
            raise FileNotFoundError("R2_OBJECT_NOT_FOUND")
        size = int(metadata.get("size_bytes", 0))
        if size <= 0 or size > min(int(max_bytes), 50 * 1024 * 1024):
            raise ValueError("R2_BOUNDED_GET_LIMIT_EXCEEDED")
        target.parent.mkdir(parents=True, exist_ok=True)
        def read():
            self.client.download_file(self.bucket, key, str(target))
            if target.stat().st_size != size:
                raise IOError("R2_GET_SIZE_MISMATCH")
        self._governed("OBJECT_GET_VERIFICATION", {"bytes": size}, read, object_key=key)
        return {"object_key": key, "size_bytes": size, "target": str(target), "verified": True}

    def delete(self, key: str, *, approval_id: str | None = None) -> None:
        if not approval_id or not self.approval_verifier or not self.approval_verifier(approval_id, key):
            raise PermissionError("R2_DELETE_APPROVAL_REQUIRED")
        self._governed("OBJECT_DELETE_CERTIFICATION_ONLY", {}, lambda: self.client.delete_object(Bucket=self.bucket, Key=key), object_key=key, write=True)

    def copy(self, source_key: str, target_key: str) -> dict[str, Any]:
        raise PermissionError("R2_OPERATION_NOT_AUTHORIZED")
