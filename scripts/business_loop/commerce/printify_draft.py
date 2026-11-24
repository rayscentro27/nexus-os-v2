#!/usr/bin/env python3
"""Create exactly ONE unpublished Printify draft product for the pilot (owner-authorized R2).

Allowed writes: one design image upload + one product create. Never calls
publish, orders, or shipping-purchase endpoints. Idempotent via a state file:
once a draft exists it is only read back.
"""
from __future__ import annotations

import base64
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]
from business_loop.commerce.governed_clients import CommerceGuard, PrintifyReader, _governed, job_context  # noqa: E402

STATE = ROOT / "reports/business_loop/printify_draft_r2.json"
DESIGN = ROOT / "dist/creative/business_loop/proj_98ef515bccee4b58/printify_design_612am_2475x1275.png"
SHOP_ID, BLUEPRINT, PROVIDER, VARIANT = 29243395, 478, 99, 104692
ALLOWED_WRITES = {"/uploads/images.json", f"/shops/{SHOP_ID}/products.json"}
TITLE = "The 6:12 AM Ritual Mug - 15oz White Ceramic"
DESCRIPTION = ("A 15oz white glossy ceramic mug printed with the 6:12 AM Ritual mark, for the quiet minutes before the house wakes. "
               "Printed on demand by Printify. Microwave and dishwasher safe; BPA and lead free (per Printify product specification).")


class PrintifyDraftWriter(PrintifyReader):
    def post(self, path: str, body: dict):
        if path not in ALLOWED_WRITES:
            raise CommerceGuard(f"printify_write_not_authorized:{path}")
        return _governed("PRINTIFY", "POST", self.BASE + path, {"Authorization": f"Bearer {self._token}", "User-Agent": "Nexus-Commerce/1.0",
                                                                  "Content-Type": "application/json", "Accept": "application/json"}, json.dumps(body).encode())


def render_design() -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    w, h = 2475, 1275
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    serif = next((f for f in ("/System/Library/Fonts/Supplemental/Georgia.ttf", "/Library/Fonts/Georgia.ttf") if Path(f).exists()), None)
    big = ImageFont.truetype(serif, 330) if serif else ImageFont.load_default()
    small = ImageFont.truetype(serif, 96) if serif else ImageFont.load_default()
    ink = (32, 26, 20, 255)
    for text, font, y in (("6:12 AM", big, 360), ("the quiet ritual", small, 760)):
        tw = d.textlength(text, font=font)
        d.text(((w - tw) / 2, y), text, font=font, fill=ink)
    d.line([(w * 0.42, 720), (w * 0.58, 720)], fill=ink, width=5)
    buf = io.BytesIO(); img.save(buf, "PNG")
    DESIGN.parent.mkdir(parents=True, exist_ok=True); DESIGN.write_bytes(buf.getvalue())
    return buf.getvalue()


def create_or_read(price_cents: int = 2900) -> dict:
    job_context("printify-draft")
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    w = PrintifyDraftWriter()
    if not state.get("product_id"):
        png = render_design()
        st, up = w.post("/uploads/images.json", {"file_name": DESIGN.name, "contents": base64.b64encode(png).decode()})
        if st not in (200, 201):
            raise RuntimeError(f"upload_failed:{st}:{up}")
        body = {"title": TITLE, "description": DESCRIPTION, "blueprint_id": BLUEPRINT, "print_provider_id": PROVIDER,
                "variants": [{"id": VARIANT, "price": price_cents, "is_enabled": True}],
                "print_areas": [{"variant_ids": [VARIANT], "placeholders": [{"position": "front", "images": [{"id": up["id"], "x": 0.5, "y": 0.5, "scale": 1, "angle": 0}]}]}],
                "tags": ["nexus-pilot", "proj_98ef515bccee4b58"]}
        st, prod = w.post(f"/shops/{SHOP_ID}/products.json", body)
        if st not in (200, 201):
            raise RuntimeError(f"product_create_failed:{st}:{prod}")
        state = {"product_id": prod["id"], "shop_id": SHOP_ID, "upload_id": up["id"], "created_at": datetime.now(timezone.utc).isoformat(),
                 "draft_price_cents": price_cents, "writes": ["uploads/images", "shops/products (create)"], "published": False, "orders": 0}
        STATE.write_text(json.dumps(state, indent=2) + "\n")
    st, prod = w.get(f"/shops/{SHOP_ID}/products/{state['product_id']}.json")
    if st != 200:
        raise RuntimeError(f"product_read_failed:{st}")
    v = next(x for x in prod["variants"] if x["id"] == VARIANT)
    state.update({"read_at": datetime.now(timezone.utc).isoformat(), "title": prod.get("title"), "visible": prod.get("visible"),
                  "is_locked": prod.get("is_locked"), "external": prod.get("external"), "blueprint_id": prod.get("blueprint_id"),
                  "print_provider_id": prod.get("print_provider_id"),
                  "variant": {"id": v["id"], "title": v.get("title"), "sku": v.get("sku"), "cost_cents": v.get("cost"), "price_cents": v.get("price"),
                              "is_enabled": v.get("is_enabled"), "is_available": v.get("is_available"), "grams": v.get("grams")},
                  "mockups": [{"src": i.get("src"), "position": i.get("position"), "is_default": i.get("is_default")} for i in prod.get("images", [])
                              if VARIANT in (i.get("variant_ids") or [])][:6]})
    STATE.write_text(json.dumps(state, indent=2) + "\n")
    return state


if __name__ == "__main__":
    s = create_or_read()
    print(json.dumps({k: s[k] for k in ("product_id", "shop_id", "visible", "blueprint_id", "print_provider_id", "variant")} | {"mockups": len(s["mockups"])}, indent=1))
