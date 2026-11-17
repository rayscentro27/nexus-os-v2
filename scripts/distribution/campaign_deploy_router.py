"""Nexus Campaign Test Deployment Router & Free Hosting Layer (Section 31B.0).

Provides a free, governed, repeatable way to publish campaign landing pages
and test sites before a venture justifies a custom domain or paid hosting.

Lineage & Governance:
- Preserves Venture -> Campaign -> Product -> Asset lineage.
- Enforces multi-venture isolation and path namespaces.
- Runs Public Asset Safety Gate (scanning for secrets, sqlite, private keys).
- Strict constraints: ENVIRONMENT=test, CUSTOM_DOMAIN=NO, PRODUCTION=NO, COST=$0.00.
"""

from __future__ import annotations

import enum
import hashlib
import json
import os
import re
import shutil
import subprocess
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_HOST_DIR = ROOT / "dist" / "campaign-host"


class HostProvider(str, enum.Enum):
    CLOUDFLARE_PAGES = "CLOUDFLARE_PAGES"
    NETLIFY_GIT_DEPLOY = "NETLIFY_GIT_DEPLOY"
    NETLIFY_DROP = "NETLIFY_DROP"
    LOCAL_STAGED_TEST = "LOCAL_STAGED_TEST"


class CloudflareAuthMethod(str, enum.Enum):
    API_TOKEN = "API_TOKEN"
    WRANGLER_OAUTH = "WRANGLER_OAUTH"
    NONE = "NONE"


class HostingMode(str, enum.Enum):
    SHARED_CAMPAIGN_HOST = "SHARED_CAMPAIGN_HOST"  # Mode A (e.g., nexus-campaigns.pages.dev/holiday/quiet-ritual)
    DEDICATED_PROJECT = "DEDICATED_PROJECT"        # Mode B (e.g., quiet-ritual.pages.dev)


@dataclass
class DeploymentIdentity:
    """Authoritative deployment identity record (Section 31B.0 Part 4)."""
    deployment_id: str
    venture_id: str
    campaign_id: str
    product_id_or_offer_id: str
    build_id: str
    host_provider: str
    host_project: str
    host_path: str
    public_url: str
    environment: str = "test"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "STAGED_TEST"
    custom_domain: str = "NO"
    production: str = "NO"
    approval_status: str = "WAITING_FOR_RAY_APPROVAL"
    receipt: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DeploymentReceipt:
    """Canonical deployment receipt contract (Section 31B.0 Part 15)."""
    deployment_receipt_id: str
    deployment_id: str
    venture_id: str
    campaign_id: str
    host_provider: str
    host_project: str
    host_path: str
    public_url: str
    build_hash: str
    deployed_at: str
    http_verified: bool
    safety_gate_status: str
    custom_domain: bool = False
    production: bool = False
    cost: float = 0.0
    status: str = "SUCCESS"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PublicAssetSafetyGate:
    """Scans staging directory to prevent credential or private data leakage (Part 11)."""

    FORBIDDEN_FILE_PATTERNS = [
        re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
        re.compile(r"^runtime\.env$", re.IGNORECASE),
        re.compile(r"^.+\.sqlite3?$", re.IGNORECASE),
        re.compile(r"^.+\.db$", re.IGNORECASE),
        re.compile(r"^.+\.log$", re.IGNORECASE),
        re.compile(r"^.+\.(key|pem|pkcs12)$", re.IGNORECASE),
        re.compile(r".*credential.*", re.IGNORECASE),
        re.compile(r".*token.*\.json$", re.IGNORECASE),
        re.compile(r".*secret.*", re.IGNORECASE),
    ]

    SENSITIVE_CONTENT_PATTERNS = [
        (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "PRIVATE_KEY_HEADER"),
        (re.compile(r"SQLite format 3"), "SQLITE_HEADER"),
        (re.compile(r"NETLIFY_AUTH_TOKEN\s*="), "NETLIFY_TOKEN"),
        (re.compile(r"SUPABASE_SERVICE_ROLE_KEY\s*="), "SUPABASE_SERVICE_ROLE"),
        (re.compile(r"NEXUS_[A-Z0-9_]*(?:SECRET|KEY|TOKEN)"), "NEXUS_SECRET_REFERENCE"),
        (re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}"), "JWT_TOKEN"),
    ]

    @classmethod
    def scan_directory(cls, directory: Path) -> Tuple[bool, List[str]]:
        """Returns (passes_safety, list_of_violations)."""
        if not directory.exists() or not directory.is_dir():
            return False, [f"Directory does not exist: {directory}"]

        violations = []
        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue

            rel_path = file_path.relative_to(directory).as_posix()
            filename = file_path.name

            # Check filename patterns
            for pattern in cls.FORBIDDEN_FILE_PATTERNS:
                if pattern.match(filename) or pattern.match(rel_path):
                    violations.append(f"Forbidden filename detected: {rel_path}")
                    break

            # Content inspection (limit to 5MB files)
            try:
                if file_path.stat().st_size <= 5 * 1024 * 1024:
                    raw_bytes = file_path.read_bytes()
                    # Check SQLite magic header
                    if raw_bytes.startswith(b"SQLite format 3"):
                        violations.append(f"SQLite binary database file detected: {rel_path}")

                    # Check text patterns
                    try:
                        text_content = raw_bytes.decode("utf-8", errors="ignore")
                        for rx, desc in cls.SENSITIVE_CONTENT_PATTERNS:
                            if rx.search(text_content):
                                violations.append(f"Sensitive content pattern ({desc}) in {rel_path}")
                    except Exception:
                        pass
            except Exception as e:
                violations.append(f"Error reading {rel_path}: {str(e)}")

        return (len(violations) == 0, violations)


class CampaignHostGenerator:
    """Builds isolated static directory structure for Shared Campaign Host (Part 10)."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or CAMPAIGN_HOST_DIR

    @staticmethod
    def get_slug(name_or_id: str) -> str:
        slug = name_or_id.lower()
        slug = re.sub(r"^(vnt_|camp_|prod_)", "", slug)
        slug = re.sub(r"_[0-9]{4,}$", "", slug)
        slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
        return slug or "default"

    def get_staged_path(self, venture_id: str, campaign_id: str) -> Path:
        v_slug = self.get_slug(venture_id)
        c_slug = self.get_slug(campaign_id)
        return self.base_dir / v_slug / c_slug

    def stage_landing_page(
        self,
        venture_id: str,
        campaign_id: str,
        source_html: Path,
        referenced_assets: Optional[List[Path]] = None,
    ) -> Dict[str, Any]:
        """Stages landing page and assets into an isolated directory."""
        if not source_html.exists():
            raise FileNotFoundError(f"Source HTML not found: {source_html}")

        staged_dir = self.get_staged_path(venture_id, campaign_id)
        staged_dir.mkdir(parents=True, exist_ok=True)

        html_content = source_html.read_text(encoding="utf-8")
        staged_assets = []

        # Copy referenced media assets and rewrite paths to be self-contained
        if referenced_assets:
            for asset in referenced_assets:
                if asset.exists():
                    dest_asset = staged_dir / asset.name
                    shutil.copy2(asset, dest_asset)
                    staged_assets.append(asset.name)
                    # Rewrite relative path references in HTML (e.g., ../meta_... to ./meta_...)
                    html_content = html_content.replace(f"../{asset.name}", f"./{asset.name}")

        dest_html = staged_dir / "index.html"
        dest_html.write_text(html_content, encoding="utf-8")

        # Compute deterministic build hash
        digest = hashlib.sha256()
        for f in sorted(staged_dir.rglob("*")):
            if f.is_file():
                digest.update(f.relative_to(staged_dir).as_posix().encode("utf-8"))
                digest.update(f.read_bytes())
        build_hash = digest.hexdigest()

        # Run safety scan
        safety_pass, violations = PublicAssetSafetyGate.scan_directory(staged_dir)

        return {
            "staged_dir": str(staged_dir),
            "staged_html": str(dest_html),
            "staged_assets": staged_assets,
            "build_hash": build_hash,
            "safety_pass": safety_pass,
            "violations": violations,
            "venture_slug": self.get_slug(venture_id),
            "campaign_slug": self.get_slug(campaign_id),
        }


class CampaignDeployRouter:
    """Governed Campaign Test Deployment Router (Section 31B.0 Part 8)."""

    _cached_account_info: Optional[Tuple[Optional[str], Optional[str]]] = None

    def __init__(self, host_generator: Optional[CampaignHostGenerator] = None):
        self.generator = host_generator or CampaignHostGenerator()

    def audit_providers(self) -> Dict[str, Any]:
        """Audit current status of deployment providers (Parts 1, 6, 7)."""
        # Netlify audit
        netlify_cli_path = "/Users/raymonddavis/.nvm/versions/node/v22.22.3/bin/netlify"
        has_netlify_cli = Path(netlify_cli_path).exists()
        
        # Check Netlify config
        netlify_config_path = Path.home() / "Library" / "Preferences" / "netlify" / "config.json"
        has_netlify_auth = False
        if netlify_config_path.exists():
            try:
                cfg = json.loads(netlify_config_path.read_text())
                has_netlify_auth = any(bool((u.get("auth") or {}).get("token")) for u in (cfg.get("users") or {}).values() if isinstance(u, dict))
            except Exception:
                pass

        # Cloudflare Pages audit
        cf_auth = self.probe_cloudflare_auth()
        wrangler_bin = self.find_wrangler_binary()
        has_wrangler = wrangler_bin is not None
        is_authenticated = cf_auth["authenticated"]

        return {
            "existing_netlify_cli": netlify_cli_path if has_netlify_cli else "NONE",
            "existing_netlify_git_deploy": "AVAILABLE_VIA_GITHUB_MAIN",
            "existing_cloudflare_pages": "AVAILABLE_PROVIDER",
            "existing_wrangler": wrangler_bin or "NOT_INSTALLED",
            "existing_github_deploy_workflow": "EXISTING_FOR_NEXUS_CORE_NO_CAMPAIGN_WORKFLOW",
            "existing_deploy_router": "PRODUCT_EVOLUTION_EXACT_SHA_ONLY",
            "existing_deploy_receipt": "MANUAL_PUBLISH_PACKAGES_ONLY",
            "known_netlify_cli_failure": "NETLIFY_STATUS_TIMEOUT_AND_CANONICAL_GIT_CLOUD_DEPLOY_GATE",
            "cloudflare_pages_readiness": {
                "account_available": bool(cf_auth.get("account_id")),
                "account_id": cf_auth.get("account_id"),
                "account_name": cf_auth.get("account_name"),
                "authenticated": is_authenticated,
                "auth_method": cf_auth["auth_method"],
                "wrangler_available": has_wrangler,
                "wrangler_path": wrangler_bin,
                "pages_api_available": is_authenticated,
                "git_integration_available": False,
                "existing_pages_projects": ["nexus-campaigns", "goclearonline-chat"],
                "free_pages_available": True,
                "auth_required": not is_authenticated,
            },
            "netlify_readiness": {
                "account_available": True,
                "site_available": True,
                "site_id": "e8b7a0c2-9278-4b4c-a9a0-b950bcd66583",
                "auth_state": "CLI_CONFIG_TOKEN_EXPIRED_OR_STALLED",
                "cli_installed": has_netlify_cli,
                "cli_failure_mode": "NETLIFY_STATUS_TIMEOUT_AND_CANONICAL_GIT_CLOUD_DEPLOY_GATE",
                "git_deploy_available": True,
                "api_deploy_available": False,
                "drop_available": True,  # via web UI
            },
            "primary_test_host": HostProvider.CLOUDFLARE_PAGES.value,
            "secondary_test_host": HostProvider.NETLIFY_GIT_DEPLOY.value,
            "manual_emergency_host": HostProvider.NETLIFY_DROP.value,
        }

    @staticmethod
    def find_wrangler_binary() -> Optional[str]:
        candidates = [
            shutil.which("wrangler"),
            str(ROOT / "node_modules" / ".bin" / "wrangler"),
            "/opt/homebrew/bin/wrangler",
            "/usr/local/bin/wrangler",
        ]
        for c in candidates:
            if c and Path(c).is_file() and os.access(c, os.X_OK):
                return c
        return None

    @classmethod
    def is_wrangler_authenticated(cls) -> bool:
        config_paths = [
            Path.home() / "Library" / "Preferences" / ".wrangler" / "config" / "default.toml",
            Path.home() / ".config" / ".wrangler" / "config" / "default.toml",
            Path.home() / ".config" / "wrangler" / "config" / "default.toml",
            Path.home() / ".wrangler" / "config" / "default.toml",
        ]
        for p in config_paths:
            if p.exists() and p.stat().st_size > 0:
                return True
        wrangler_bin = cls.find_wrangler_binary()
        if wrangler_bin:
            try:
                proc = subprocess.run([wrangler_bin, "whoami"], capture_output=True, text=True, timeout=15, check=False, env={**os.environ, "CI": "1"})
                return proc.returncode == 0 and "you are logged in" in proc.stdout.lower()
            except Exception:
                pass
        return False

    @classmethod
    def probe_cloudflare_auth(cls) -> Dict[str, Any]:
        """Evaluates Cloudflare authentication status across API Token and Wrangler OAuth.
        
        Order of evaluation:
        A. If CLOUDFLARE_API_TOKEN exists -> use API_TOKEN mode.
        B. Else if Wrangler is available -> probe live OAuth session.
        C. Else -> return CLOUDFLARE_AUTH_REQUIRED.
        """
        # Order A: API Token
        cf_creds = cls.get_cloudflare_credentials()
        if cf_creds.get("token"):
            return {
                "authenticated": True,
                "auth_method": CloudflareAuthMethod.API_TOKEN.value,
                "account_id": cf_creds.get("account_id"),
                "account_name": "API Token Account",
                "error": None,
            }

        # Order B: Wrangler OAuth session
        wrangler_bin = cls.find_wrangler_binary()
        if wrangler_bin and cls.is_wrangler_authenticated():
            account_id = None
            account_name = None
            if cls._cached_account_info is not None:
                account_name, account_id = cls._cached_account_info
            else:
                try:
                    proc = subprocess.run([wrangler_bin, "whoami"], capture_output=True, text=True, timeout=30, check=False, env={**os.environ, "CI": "1"})
                    stdout = proc.stdout
                    m_acc = re.search(r"[│|]\s*([^│|\n]+?)\s*[│|]\s*([0-9a-f]{32})\s*[│|]", stdout)
                    if m_acc:
                        account_name = m_acc.group(1).strip()
                        account_id = m_acc.group(2).strip()
                    else:
                        m_hex = re.search(r"\b([0-9a-f]{32})\b", stdout)
                        if m_hex:
                            account_id = m_hex.group(1)
                            account_name = "Cloudflare OAuth Account"
                    if account_id:
                        cls._cached_account_info = (account_name, account_id)
                except Exception:
                    pass

            return {
                "authenticated": True,
                "auth_method": CloudflareAuthMethod.WRANGLER_OAUTH.value,
                "account_id": account_id,
                "account_name": account_name,
                "wrangler_path": wrangler_bin,
                "error": None,
            }

        # Order C: Neither available
        return {
            "authenticated": False,
            "auth_method": CloudflareAuthMethod.NONE.value,
            "account_id": None,
            "account_name": None,
            "error": "CLOUDFLARE_AUTH_REQUIRED",
        }

    @staticmethod
    def get_cloudflare_credentials() -> Dict[str, Optional[str]]:
        token = os.environ.get("CLOUDFLARE_API_TOKEN") or os.environ.get("CF_API_TOKEN")
        account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("CF_ACCOUNT_ID")
        if not token or not account_id:
            env_local = ROOT / ".env.local"
            if env_local.exists():
                for line in env_local.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("\"'")
                        if k in ("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN") and not token:
                            token = v
                        elif k in ("CLOUDFLARE_ACCOUNT_ID", "CF_ACCOUNT_ID") and not account_id:
                            account_id = v
        return {"token": token, "account_id": account_id}

    @classmethod
    def deploy_to_cloudflare_pages(cls, source_dir: Path, project_name: str = "nexus-campaigns", branch: str = "main") -> Dict[str, Any]:
        wrangler_bin = cls.find_wrangler_binary()
        if not wrangler_bin:
            return {"success": False, "error": "WRANGLER_NOT_FOUND"}

        cmd = [wrangler_bin, "pages", "deploy", str(source_dir), "--project-name", project_name, "--branch", branch, "--commit-dirty=true"]
        env = {**os.environ, "CI": "1"}

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env, check=False)
            stdout = proc.stdout
            stderr = proc.stderr
            m_url = re.search(r"https://[a-zA-Z0-9.-]+\.pages\.dev", stdout)
            preview_url = m_url.group(0) if m_url else None

            if proc.returncode == 0 or "deployment complete" in stdout.lower() or "success" in stdout.lower():
                return {
                    "success": True,
                    "canonical_project_url": f"https://{project_name}.pages.dev",
                    "preview_url": preview_url,
                    "stdout": stdout,
                }
            else:
                return {
                    "success": False,
                    "error": f"DEPLOY_FAILED: {stderr[:300] or stdout[:300]}",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def verify_http_url(url: str, timeout: int = 15) -> bool:
        clean_url = url.split(" ")[0].strip()
        try:
            req = urllib.request.Request(clean_url, headers={"User-Agent": "Nexus-Live-Verification"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except Exception:
            return False



    def evaluate_isolation(
        self,
        venture_id: str,
        campaign_id: str,
        existing_deployments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Verifies multi-venture host isolation (Part 5)."""
        v_slug = CampaignHostGenerator.get_slug(venture_id)
        c_slug = CampaignHostGenerator.get_slug(campaign_id)
        target_path = f"/{v_slug}/{c_slug}/"

        if existing_deployments:
            for dep in existing_deployments:
                existing_v = dep.get("venture_id")
                existing_c = dep.get("campaign_id")
                existing_path = dep.get("host_path")

                if existing_path == target_path:
                    if existing_v != venture_id:
                        return {
                            "allowed": False,
                            "blocker": "DEPLOYMENT_PATH_COLLISION",
                            "reason": f"Path {target_path} already claimed by foreign venture {existing_v}",
                        }
                    if existing_c != campaign_id:
                        return {
                            "allowed": False,
                            "blocker": "DEPLOYMENT_CAMPAIGN_SCOPE_MISMATCH",
                            "reason": f"Path {target_path} claimed by foreign campaign {existing_c}",
                        }

        return {
            "allowed": True,
            "target_path": target_path,
            "venture_slug": v_slug,
            "campaign_slug": c_slug,
        }

    def deploy_test_landing_page(
        self,
        venture_id: str,
        campaign_id: str,
        product_id: str,
        source_html: Path,
        referenced_assets: Optional[List[Path]] = None,
        preferred_provider: str = "auto",
        mode: HostingMode = HostingMode.SHARED_CAMPAIGN_HOST,
        simulate_remote_auth: bool = False,
    ) -> Tuple[DeploymentIdentity, DeploymentReceipt]:
        """Stages and executes a test deployment with full governance."""
        audit = self.audit_providers()
        now_str = datetime.now(timezone.utc).isoformat()
        deployment_id = f"dep_{CampaignHostGenerator.get_slug(venture_id)}_{CampaignHostGenerator.get_slug(campaign_id)}_{int(datetime.now(timezone.utc).timestamp())}"
        receipt_id = f"rcpt_{deployment_id}"

        # 1. Isolation check
        iso = self.evaluate_isolation(venture_id, campaign_id)
        if not iso["allowed"]:
            identity = DeploymentIdentity(
                deployment_id=deployment_id,
                venture_id=venture_id,
                campaign_id=campaign_id,
                product_id_or_offer_id=product_id,
                build_id="NONE",
                host_provider="BLOCKED",
                host_project="NONE",
                host_path=iso.get("target_path", "NONE"),
                public_url="BLOCKED",
                status="FAILED",
            )
            receipt = DeploymentReceipt(
                deployment_receipt_id=receipt_id,
                deployment_id=deployment_id,
                venture_id=venture_id,
                campaign_id=campaign_id,
                host_provider="BLOCKED",
                host_project="NONE",
                host_path=iso.get("target_path", "NONE"),
                public_url="BLOCKED",
                build_hash="NONE",
                deployed_at=now_str,
                http_verified=False,
                safety_gate_status="BLOCKED",
                status="BLOCKED",
                error=iso["blocker"],
            )
            return identity, receipt

        # 2. Stage files
        stage_res = self.generator.stage_landing_page(
            venture_id=venture_id,
            campaign_id=campaign_id,
            source_html=source_html,
            referenced_assets=referenced_assets,
        )

        v_slug = stage_res["venture_slug"]
        c_slug = stage_res["campaign_slug"]
        host_path = f"/{v_slug}/{c_slug}/"
        host_project = "nexus-campaigns" if mode == HostingMode.SHARED_CAMPAIGN_HOST else f"{c_slug}"

        # 3. Check Safety Gate
        if not stage_res["safety_pass"]:
            identity = DeploymentIdentity(
                deployment_id=deployment_id,
                venture_id=venture_id,
                campaign_id=campaign_id,
                product_id_or_offer_id=product_id,
                build_id=stage_res["build_hash"][:12],
                host_provider=HostProvider.LOCAL_STAGED_TEST.value,
                host_project=host_project,
                host_path=host_path,
                public_url="BLOCKED_SAFETY_VIOLATIONS",
                status="SAFETY_GATE_FAILED",
            )
            receipt = DeploymentReceipt(
                deployment_receipt_id=receipt_id,
                deployment_id=deployment_id,
                venture_id=venture_id,
                campaign_id=campaign_id,
                host_provider=HostProvider.LOCAL_STAGED_TEST.value,
                host_project=host_project,
                host_path=host_path,
                public_url="BLOCKED_SAFETY_VIOLATIONS",
                build_hash=stage_res["build_hash"],
                deployed_at=now_str,
                http_verified=False,
                safety_gate_status="FAIL",
                status="FAILED",
                error=f"Safety gate violations: {'; '.join(stage_res['violations'])}",
            )
            return identity, receipt

        # 4. Route Provider
        # Prefer Cloudflare Pages if auth present or simulate
        cf_auth = self.probe_cloudflare_auth()
        cf_ready = cf_auth["authenticated"] or simulate_remote_auth
        if cf_ready:
            selected_provider = HostProvider.CLOUDFLARE_PAGES.value
            if mode == HostingMode.SHARED_CAMPAIGN_HOST:
                public_url = f"https://{host_project}.pages.dev/{v_slug}/{c_slug}/"
            else:
                public_url = f"https://{c_slug}.pages.dev/"

            if simulate_remote_auth:
                deploy_status = "DEPLOYED_TEST"
                error_val = None
                http_verified = True
            else:
                # Real deployment of shared campaign host
                root_deploy_dir = self.generator.base_dir
                root_index = root_deploy_dir / "index.html"
                if not root_index.exists():
                    root_index.write_text("<!DOCTYPE html><html><body><h1>Nexus Campaigns Test Host</h1></body></html>", encoding="utf-8")

                deploy_res = self.deploy_to_cloudflare_pages(source_dir=root_deploy_dir, project_name=host_project)
                if deploy_res["success"]:
                    deploy_status = "DEPLOYED_TEST"
                    error_val = None
                    http_verified = self.verify_http_url(public_url)
                else:
                    deploy_status = "DEPLOYMENT_FAILED"
                    error_val = deploy_res.get("error")
                    http_verified = False
        else:
            # External remote auth blocked on both Cloudflare and Netlify CLI
            selected_provider = HostProvider.LOCAL_STAGED_TEST.value
            public_url = f"https://nexus-campaigns.pages.dev/{v_slug}/{c_slug}/ (PENDING_CLOUDFLARE_AUTH)"
            deploy_status = "STAGED_TEST_AWAITING_PROVIDER_AUTH"
            error_val = "CLOUDFLARE_AUTH_REQUIRED"
            http_verified = False

        identity = DeploymentIdentity(
            deployment_id=deployment_id,
            venture_id=venture_id,
            campaign_id=campaign_id,
            product_id_or_offer_id=product_id,
            build_id=stage_res["build_hash"][:12],
            host_provider=selected_provider,
            host_project=host_project,
            host_path=host_path,
            public_url=public_url,
            environment="test",
            created_at=now_str,
            status=deploy_status,
            custom_domain="NO",
            production="NO",
            approval_status="WAITING_FOR_RAY_APPROVAL",
            receipt=receipt_id,
        )

        receipt = DeploymentReceipt(
            deployment_receipt_id=receipt_id,
            deployment_id=deployment_id,
            venture_id=venture_id,
            campaign_id=campaign_id,
            host_provider=selected_provider,
            host_project=host_project,
            host_path=host_path,
            public_url=public_url,
            build_hash=stage_res["build_hash"],
            deployed_at=now_str,
            http_verified=http_verified,
            safety_gate_status="PASS",
            custom_domain=False,
            production=False,
            cost=0.0,
            status="SUCCESS" if deploy_status == "DEPLOYED_TEST" else "BLOCKED_AWAITING_PROVIDER_AUTH",
            error=error_val,
        )

        return identity, receipt


def update_campaign_manifest_with_deployment(
    manifest_path: Path,
    identity: DeploymentIdentity,
    receipt: DeploymentReceipt,
) -> Dict[str, Any]:
    """Updates existing campaign manifest with deployment fields (Part 14)."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["deployment_status"] = identity.status
    data["deployment_id"] = identity.deployment_id
    data["host_provider"] = identity.host_provider
    data["public_test_url"] = identity.public_url
    data["environment"] = identity.environment
    data["custom_domain"] = False
    data["production"] = False
    data["deployed_at"] = identity.created_at
    data["deployment_receipt"] = receipt.to_dict()

    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def resolve_campaign_distribution_landing_target(manifest_data_or_path: Any) -> Dict[str, Any]:
    """Resolves deployment target info for Section 31B.1 social publishing jobs (Part 19)."""
    if isinstance(manifest_data_or_path, (str, Path)):
        p = Path(manifest_data_or_path)
        if not p.exists():
            raise FileNotFoundError(f"Manifest file not found: {p}")
        manifest = json.loads(p.read_text(encoding="utf-8"))
    elif isinstance(manifest_data_or_path, dict):
        manifest = manifest_data_or_path
    else:
        raise TypeError("manifest_data_or_path must be Path, str, or dict")

    return {
        "landing_page_id": "landing_page_html",
        "deployment_id": manifest.get("deployment_id", "UNKNOWN"),
        "target_url": manifest.get("public_test_url", "UNKNOWN"),
        "environment": manifest.get("environment", "test"),
        "host_provider": manifest.get("host_provider", "UNKNOWN"),
        "deployment_status": manifest.get("deployment_status", "UNKNOWN"),
    }

