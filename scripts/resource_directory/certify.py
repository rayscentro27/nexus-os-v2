"""Resource Directory + Router certification (spec section 27 tests). Deterministic, $0."""
from __future__ import annotations
import json, os, sys, tempfile, shutil
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SCRIPTS))


def main():
    from resource_directory import router as R
    res = {}

    # Test 1 — Research workload -> prefer Mac mini; Oracle must NOT win / must be prohibited
    t1 = R.route_task("market_research", workload="research")
    sel1 = (t1["selected"] or {}).get("environment_id")
    oracle1 = next((r for r in t1["ranked"] if r["environment_id"] == "oracle"), None)
    # Oracle correct behavior = NOT eligible for research (prohibited). Absent from eligible set also satisfies.
    oracle_ok = (oracle1 is None) or (not oracle1.get("eligible", False))
    res["test1_research"] = {"pass": sel1 == "mac_mini" and oracle_ok,
                             "selected": sel1, "oracle_in_top8": bool(oracle1),
                             "oracle_eligible": (oracle1 or {}).get("eligible", False)}

    # Test 2 — Landing-page build -> coding/sandbox worker; Oracle not selected
    t2 = R.route_task("landing_page_build", workload="frontend_build")
    sel2 = (t2["selected"] or {}).get("environment_id")
    res["test2_landing_page"] = {"pass": sel2 not in ("oracle", "mac_mini", None),
                                 "selected": sel2, "top3": [r["environment_id"] for r in t2["ranked"][:3]]}

    # Test 3 — GPU/data clustering -> free/included (Colab/Kaggle) outranks metered (Modal/RunPod)
    t3 = R.route_task("cluster_market_comments", workload="data_processing")
    order = [r["environment_id"] for r in t3["ranked"] if r["eligible"]]
    free_rank = min([order.index(e) for e in ("colab", "kaggle") if e in order], default=99)
    paid_rank = min([order.index(e) for e in ("modal", "runpod") if e in order], default=99)
    res["test3_gpu_data"] = {"pass": free_rank < paid_rank, "eligible_order": order[:5]}

    # Test 4 — REA reference analysis -> multiple compatible workers, not one fixed harness
    t4 = R.route_worker(["reverse_engineering", "frontend", "browser", "coding"])
    hc = t4["harness_candidates"]
    rea_harnesses = [h["harness_id"] for h in hc if h["harness_id"] in ("deepseek_harness", "claude_code", "codex", "antigravity", "hermes", "opencode")]
    res["test4_rea"] = {"pass": len(rea_harnesses) >= 3, "compatible_harnesses": rea_harnesses}

    # Test 5 — Production control -> Oracle authoritative
    t5 = R.route_task("nova_control", workload="control")
    res["test5_control"] = {"pass": (t5["selected"] or {}).get("environment_id") == "oracle",
                            "selected": (t5["selected"] or {}).get("environment_id")}

    # Tests 6 & 7 — exhausted quota + offline worker on an ISOLATED registry copy
    tmp = Path(tempfile.mkdtemp(prefix="resdir_cert_"))
    reg = json.load(open(R._RUNTIME / "nexus_environment_registry.json"))
    for e in reg["environments"]:
        if e["environment_id"] == "kaggle":
            e["quota_remaining"] = "EXHAUSTED"; e["health_status"] = "QUOTA_EXHAUSTED"
        if e["environment_id"] == "colab":
            e["status"] = "OFFLINE"; e["health_status"] = "OFFLINE"
    isolated = tmp / "env.json"; json.dump(reg, open(isolated, "w"))
    os.environ["NEXUS_ENV_REGISTRY_PATH"] = str(isolated)
    import importlib
    importlib.reload(R)
    t6 = R.route_task("gpu_batch", workload="gpu", approved_spend=0.0)
    # with Colab offline + Kaggle exhausted, only paid Modal/RunPod remain for pure gpu -> approval gate
    sel6 = (t6["selected"] or {}).get("environment_id")
    res["test6_exhausted_quota"] = {"pass": t6.get("venture_state") == R.PAUSE_STATE or (sel6 in ("modal", "runpod")),
                                    "selected": sel6, "venture_state": t6.get("venture_state"),
                                    "approval_reason": t6.get("approval_reason")}
    # test7: data_processing now routes AROUND offline colab / exhausted kaggle to next valid
    t7 = R.route_task("cluster", workload="data_processing", approved_spend=0.0)
    order7 = [r["environment_id"] for r in t7["ranked"] if r["eligible"]]
    res["test7_offline_reroute"] = {"pass": "colab" not in order7 and "kaggle" not in order7 and bool(order7) or t7.get("venture_state") == R.PAUSE_STATE,
                                    "eligible_order": order7[:5], "venture_state": t7.get("venture_state")}
    os.environ.pop("NEXUS_ENV_REGISTRY_PATH", None); importlib.reload(R)

    # Test 8 — Business Opportunity resource mapping (real existing opportunity)
    sys.path.insert(0, str(_SCRIPTS))
    from opportunities import engine as opp
    live = opp.list_opportunities(limit=3, include_internal_ids=True)
    req_caps = ["research", "coding", "frontend_build", "deployment", "data_processing"]
    omap = R.opportunity_resource_map(req_caps)
    res["test8_opportunity_map"] = {"pass": "nexus_capability_coverage_percent" in omap and bool(omap["matched_environments"]),
                                    "opportunity_sampled": (live[0]["title"] if live else "none"),
                                    "coverage_percent": omap["nexus_capability_coverage_percent"],
                                    "matched": [m["environment"] for m in omap["matched_environments"]],
                                    "missing": omap["new_capabilities_required"],
                                    "approvals_required": omap["approvals_required"]}

    # Test 9 — usage event record (no fabricated provider metrics)
    ev = R.record_environment_usage({"job_id": "cert_job_1", "environment_id": "mac_mini", "worker_id": "research-r16",
                                     "task_type": "research", "cost_class": "FREE", "status": "COMPLETED",
                                     "success": True, "actual_cost": 0, "ai_usage_ref": "ledger:deterministic:0"})
    res["test9_usage_event"] = {"pass": bool(ev.get("usage_event_id")) and ev.get("gpu_time") == "UNKNOWN",
                                "usage_event_id": ev.get("usage_event_id"), "unknowns_preserved": ev.get("compute_units") == "UNKNOWN"}

    # venture kernel interface (prepare, not activate)
    vi = R.venture_router_interface(["research", "coding", "deployment"])
    res["venture_router_interface"] = {"pass": vi.get("scheduler_wired") is False and "venture_state" in vi,
                                       "scheduler_wired": vi.get("scheduler_wired"), "venture_state": vi.get("venture_state")}

    res["_counts"] = {"environments": len(R.environments()), "workers": len(R.workers()),
                      "harnesses": len(R.harnesses()), "capabilities": len(R.capabilities())}
    res["_OVERALL_PASS"] = all(v.get("pass") for k, v in res.items() if isinstance(v, dict) and "pass" in v)
    return res


if __name__ == "__main__":
    print(json.dumps(main(), indent=1, default=str))
