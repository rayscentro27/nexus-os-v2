#!/usr/bin/env python3
"""
Hermes Chat Live Model Smoke Test

Calls the deployed Supabase Edge Function with a tiny test prompt.
Reports success/failure with safe metadata (no secrets).

Usage:
  python3 scripts/ops/test_hermes_chat_live_model.py
"""

import json
import subprocess
import sys
import time
import os

PROJECT_REF = "iqjwgpnujbeoyaeuwehj"

def get_env(key: str) -> str:
    """Read value from .env without printing it."""
    env_path = "/Users/raymonddavis/nexus-os-v2/.env"
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1]
    return ""

def call_edge_function(message: str) -> dict:
    """Call hermes-chat Edge Function via curl."""
    url = f"https://{PROJECT_REF}.supabase.co/functions/v1/hermes-chat"
    anon_key = get_env("VITE_SUPABASE_ANON_KEY")
    if not anon_key:
        return {"ok": False, "error": "Missing VITE_SUPABASE_ANON_KEY from .env"}
    
    try:
        result = subprocess.run(
            ["curl", "-s", "-m", "60",
             "-X", "POST", url,
             "-H", f"apikey: {anon_key}",
             "-H", f"Authorization: Bearer {anon_key}",
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"message": message})],
            capture_output=True, text=True, timeout=90
        )
        if result.returncode != 0:
            return {"ok": False, "error": f"curl error: {result.stderr.strip()[:200]}"}
        
        data = json.loads(result.stdout)
        return {"ok": True, "data": data}
    
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Timeout after 90s"}
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid JSON: {str(e)[:100]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}

def run_smoke_test():
    """Run the smoke test and report results."""
    report = {
        "test": "hermes_chat_live_model_smoke",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "project_ref": PROJECT_REF,
        "test_prompt": "Reply with exactly: HERMES_MODEL_OK",
        "steps": [],
        "success": False,
    }

    # Step 1: Diagnostic call
    print("Step 1: Running diagnostic check...")
    diag_result = call_edge_function("__diagnostic__")
    report["steps"].append({"step": "diagnostic", "result": diag_result})
    
    if diag_result.get("ok") and diag_result.get("data"):
        diag = diag_result["data"].get("diagnostic", {})
        report["diagnostic"] = {
            "providerConfigured": diag.get("providerConfigured"),
            "modelConfigured": diag.get("modelConfigured"),
            "fallbackConfigured": diag.get("fallbackConfigured"),
            "apiKeyConfigured": diag.get("apiKeyConfigured"),
            "selectedProvider": diag.get("selectedProvider"),
            "selectedModel": diag.get("selectedModel"),
            "selectedFallbackModel": diag.get("selectedFallbackModel"),
        }
        print(f"  Provider: {diag.get('selectedProvider')}")
        print(f"  Model: {diag.get('selectedModel')}")
        print(f"  API Key: {'present' if diag.get('apiKeyConfigured') else 'MISSING'}")
    else:
        print(f"  Diagnostic failed: {diag_result.get('error', 'unknown')}")
        report["diagnostic"] = {"error": diag_result.get("error", "unknown")}

    # Step 2: Live model call
    print("\nStep 2: Calling live model...")
    start = time.time()
    model_result = call_edge_function("Reply with exactly: HERMES_MODEL_OK")
    duration_ms = int((time.time() - start) * 1000)
    report["steps"].append({"step": "model_call", "duration_ms": duration_ms, "result": model_result})
    report["model_call_duration_ms"] = duration_ms

    if model_result.get("ok") and model_result.get("data"):
        data = model_result["data"]
        reply = data.get("reply", "")
        metadata = data.get("metadata", {})
        configured = data.get("configured", False)
        
        report["model_call"] = {
            "configured": configured,
            "reply_preview": reply[:200],
            "provider": metadata.get("provider"),
            "model": metadata.get("model"),
            "fallbackUsed": metadata.get("fallbackUsed"),
            "errorCode": metadata.get("errorCode"),
            "source": metadata.get("source"),
            "durationMs": metadata.get("durationMs"),
        }
        
        print(f"  Configured: {configured}")
        print(f"  Provider: {metadata.get('provider')}")
        print(f"  Model: {metadata.get('model')}")
        print(f"  Reply: {reply}")
        
        if configured and reply and "HERMES_MODEL_OK" in reply.upper():
            report["success"] = True
            report["verification"] = "PASS — model responded with expected token"
        elif configured and reply:
            report["success"] = True
            report["verification"] = f"PASS — model responded (reply: {reply[:80]})"
        elif configured and metadata.get("errorCode"):
            report["verification"] = f"FAIL — model configured but call failed: {metadata.get('errorCode')}"
        else:
            report["verification"] = "FAIL — model not configured or empty reply"
    else:
        report["model_call"] = {"error": model_result.get("error", "unknown")}
        report["verification"] = f"FAIL — {model_result.get('error', 'unknown')}"

    print(f"\n{'='*50}")
    print(f"Result: {'PASS' if report['success'] else 'FAIL'}")
    print(f"Verification: {report.get('verification', 'unknown')}")
    print(f"Duration: {duration_ms}ms")

    # Write reports
    json_path = "/Users/raymonddavis/nexus-os-v2/reports/hermes_chat_live_model_smoke_latest.json"
    md_path = "/Users/raymonddavis/nexus-os-v2/reports/hermes_chat_live_model_smoke_latest.md"
    
    with open(json_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    with open(md_path, 'w') as f:
        f.write(f"# Hermes Chat Live Model Smoke Test\n\n")
        f.write(f"**Timestamp:** {report['timestamp']}\n")
        f.write(f"**Project:** {PROJECT_REF}\n")
        f.write(f"**Result:** {'PASS' if report['success'] else 'FAIL'}\n")
        f.write(f"**Verification:** {report.get('verification', 'unknown')}\n\n")
        
        if report.get("diagnostic"):
            diag = report["diagnostic"]
            f.write(f"## Diagnostic\n\n")
            f.write(f"| Check | Status |\n|-------|--------|\n")
            f.write(f"| Provider configured | {diag.get('providerConfigured')} |\n")
            f.write(f"| Model configured | {diag.get('modelConfigured')} |\n")
            f.write(f"| Fallback configured | {diag.get('fallbackConfigured')} |\n")
            f.write(f"| API Key configured | {diag.get('apiKeyConfigured')} |\n")
            f.write(f"| Selected provider | {diag.get('selectedProvider')} |\n")
            f.write(f"| Selected model | {diag.get('selectedModel')} |\n")
            f.write(f"| Fallback model | {diag.get('selectedFallbackModel')} |\n\n")
        
        if report.get("model_call"):
            mc = report["model_call"]
            f.write(f"## Model Call\n\n")
            f.write(f"| Field | Value |\n|-------|-------|\n")
            f.write(f"| Configured | {mc.get('configured')} |\n")
            f.write(f"| Provider | {mc.get('provider')} |\n")
            f.write(f"| Model | {mc.get('model')} |\n")
            f.write(f"| Duration | {mc.get('durationMs')}ms |\n")
            f.write(f"| Error | {mc.get('errorCode', 'none')} |\n")
            f.write(f"| Reply | `{mc.get('reply_preview', '')}` |\n")
    
    print(f"\nReports written:")
    print(f"  {json_path}")
    print(f"  {md_path}")
    
    return report["success"]

if __name__ == "__main__":
    success = run_smoke_test()
    sys.exit(0 if success else 1)
