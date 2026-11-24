"""Assemble nexus_rea_model_worker.ipynb from cells/*.py, embedding the proxy and REA system prompt."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CELLS = ["c1_config", "c2_audit", "c3_deps", "c4_model", "c5_api", "c6_tunnel", "c7_tests", "c8_rea_sim", "c9_contract"]
HEADER = """# Nexus REA model worker (Kaggle) — MODEL COMPUTE ONLY

Hosts one Hugging Face GGUF model with llama.cpp behind an authenticated OpenAI-compatible proxy for the Contabo
OpenCode + REA MCP harness. Not a job authority, state store, orchestrator, cost governor, continuation engine or MCP host.

**Run:** GPU T4 x2, Internet ON. Optional secrets (Add-ons -> Secrets): `NEXUS_REA_MODEL_API_KEY` (bearer key Contabo uses;
without it an ephemeral self-test key is generated), `HF_TOKEN` (gated models only), `CLOUDFLARE_TUNNEL_TOKEN` (TUNNEL="named").
To change model edit only the `MODEL_*` block in Cell 1. Outputs: `/kaggle/working/rea_model_worker_report.json` (no secrets)."""


def lines(text):
    out = text.splitlines(keepends=True)
    return out


def main():
    proxy = (HERE / "rea_model_proxy.py").read_text()
    prompt = (HERE / "REA_MODEL_SYSTEM_PROMPT.md").read_text()
    selector = (HERE / "model_selector.py").read_text()
    catalog = (HERE / "model_catalog.json").read_text()
    cells = [{"cell_type": "markdown", "metadata": {}, "source": lines(HEADER)}]
    for name in CELLS:
        src = (HERE / "cells" / f"{name}.py").read_text()
        if name == "c5_api":
            src = f"PROXY_SOURCE = {proxy!r}\nREA_SYSTEM_PROMPT = {prompt!r}\n" + src
        if name == "c4_model":
            src = f"SELECTOR_SOURCE = {selector!r}\nCATALOG_JSON = {catalog!r}\n" + src
        cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines(src)})
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                       "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    (HERE / "kernel" / "nexus_rea_model_worker.ipynb").parent.mkdir(exist_ok=True)
    (HERE / "kernel" / "nexus_rea_model_worker.ipynb").write_text(json.dumps(nb, indent=1))
    # Also a flat script form for reuse / review.
    flat = "\n\n".join((f"PROXY_SOURCE = {proxy!r}\nREA_SYSTEM_PROMPT = {prompt!r}\n" if n == "c5_api" else "") +
                       (f"SELECTOR_SOURCE = {selector!r}\nCATALOG_JSON = {catalog!r}\n" if n == "c4_model" else "") +
                       (HERE / "cells" / f"{n}.py").read_text() for n in CELLS)
    (HERE / "nexus_rea_model_worker_flat.py").write_text(flat)
    print("built", len(cells), "cells")


if __name__ == "__main__":
    main()
