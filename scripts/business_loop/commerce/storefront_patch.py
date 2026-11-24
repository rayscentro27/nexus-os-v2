#!/usr/bin/env python3
"""Idempotently extend the existing pilot landing page with interest capture + first-party tracking.

Only the conversion layer is added; the page design is untouched except the CTA
targets and a status line. Re-running replaces the previously injected block.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]
from business_loop.commerce.supabase_io import config  # noqa: E402

PAGE = ROOT / "dist/campaign-host/holiday-commerce-pilot/holiday-ceramic-mug/index.html"
BACKUP = ROOT / "dist/creative/landing_backups/holiday-ceramic-mug.index.pre_conversion_r1.html"
IDS = {"project_id": "proj_98ef515bccee4b58", "venture_id": "vnt_holiday_commerce_pilot_2026",
       "opportunity_id": "opp_holiday_ceramic_mug_2026", "product_id": "prod_stoneware_mug_14oz"}
CAMPAIGN_ID = "holiday_quiet_ritual_mug_r1"
START, END = "<!-- NEXUS_CONVERSION_R1_START -->", "<!-- NEXUS_CONVERSION_R1_END -->"

FORM_HTML = """<!-- NEXUS_CONVERSION_R1_START -->
<style>
.nx-form{margin:24px auto 0;max-width:440px;display:flex;flex-direction:column;gap:10px;text-align:left}
.nx-form label{font-size:13px;color:var(--text-secondary,#8a7d6b)}
.nx-form input{width:100%;box-sizing:border-box;padding:14px 16px;font-size:16px;border:1px solid rgba(120,100,80,.35);border-radius:6px;background:rgba(255,255,255,.9);color:#1d1712}
.nx-form button{cursor:pointer;border:0}
.nx-form button[disabled]{opacity:.6;cursor:default}
.nx-msg{min-height:22px;font-size:14px}
.nx-msg.ok{color:#2f6b3a}.nx-msg.err{color:#a3341f}
.nx-hp{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}
.nx-status{font-size:13px;opacity:.85;margin-top:8px}
#nx-test-checkout{display:none;margin-top:18px}
</style>
<form id="nx-interest" class="nx-form" novalidate>
  <label for="nx-email">Email (required)</label>
  <input id="nx-email" name="email" type="email" autocomplete="email" inputmode="email" required maxlength="254" placeholder="you@example.com">
  <label for="nx-first">First name (optional)</label>
  <input id="nx-first" name="first_name" type="text" autocomplete="given-name" maxlength="60">
  <div class="nx-hp" aria-hidden="true"><label for="nx-company">Company</label><input id="nx-company" name="company" tabindex="-1" autocomplete="off"></div>
  <button type="submit" class="btn-primary" id="nx-submit" data-cta="register_interest">Register interest</button>
  <div id="nx-msg" class="nx-msg" role="status" aria-live="polite"></div>
  <div class="nx-status">Not yet available for purchase. Register to be notified when it opens. We only use your email for this.</div>
  <a id="nx-test-checkout" class="btn-link" href="#" data-cta="test_checkout">Test checkout (Stripe TEST mode, no real charge)</a>
</form>
<!-- NEXUS_CONVERSION_R1_END -->"""


def script_block(payment_link: str) -> str:
    cfg = config()
    js_cfg = {"url": cfg["url"], "anon": cfg["anon"], "ids": IDS, "campaign": CAMPAIGN_ID, "paymentLink": payment_link}
    return START.replace("START", "SCRIPT_START") + "\n<script>\n(function(){\n" \
        f"var C={json.dumps(js_cfg)};\n" + r"""
function store(k,v){try{if(v===undefined){return sessionStorage.getItem(k)}sessionStorage.setItem(k,v)}catch(e){return null}}
function lstore(k,v){try{if(v===undefined){return localStorage.getItem(k)}localStorage.setItem(k,v)}catch(e){return null}}
function rid(){try{return 's'+crypto.getRandomValues(new Uint32Array(3)).join('').slice(0,24)}catch(e){return 's'+Date.now()+Math.floor(Math.random()*1e9)}}
var qs=new URLSearchParams(location.search);
var sid=store('nx_sid');if(!sid){sid=(qs.get('nx_cert')==='1'?'nexus-cert-':'')+rid();store('nx_sid',sid)}
var A=null;try{A=JSON.parse(store('nx_attr')||'null')}catch(e){}
var keys=['utm_source','utm_medium','utm_campaign','utm_content'];
if(!A||qs.get('utm_source')){A={};keys.forEach(function(k){var v=qs.get(k);if(v)A[k]=v.slice(0,64)});
 var ref='';try{ref=document.referrer?new URL(document.referrer).hostname:''}catch(e){}
 A.source=(A.utm_source||ref||'direct').slice(0,64);A.content_variant=(A.utm_content||'none').slice(0,64);A.campaign=(A.utm_campaign||C.campaign).slice(0,96);
 store('nx_attr',JSON.stringify(A))}
function base(){var o={};for(var k in C.ids)o[k]=C.ids[k];o.session_id=sid;o.source=A.source;o.campaign=A.campaign;o.content_variant=A.content_variant;
 keys.forEach(function(k){if(A[k])o[k]=A[k]});return o}
function post(table,body){return fetch(C.url+'/rest/v1/'+table,{method:'POST',keepalive:true,headers:{'apikey':C.anon,'Authorization':'Bearer '+C.anon,'Content-Type':'application/json','Prefer':'return=minimal'},body:JSON.stringify(body)})}
function ev(type,detail){var b=base();b.event_type=type;b.page_path=location.pathname.slice(0,200);b.detail=detail||{};b.client_ts=new Date().toISOString();
 return post('commerce_events',b).catch(function(){})}
window.nxTrack=ev;
ev('PAGE_VIEW',{});
document.addEventListener('click',function(e){var a=e.target.closest('a.btn-primary,a.btn-link,button.btn-primary');if(!a)return;
 var cta=a.getAttribute('data-cta')||(a.textContent||'').trim().slice(0,60);if(cta==='register_interest')return;
 if(cta==='test_checkout')return;ev('CTA_CLICK',{cta:cta})},true);
document.querySelectorAll('a[href="#preview"]').forEach(function(a){a.addEventListener('click',function(){setTimeout(function(){var i=document.getElementById('nx-email');if(i)i.focus({preventScroll:true})},350)})});
var f=document.getElementById('nx-interest');if(!f)return;var started=false,busy=false,msg=document.getElementById('nx-msg'),btn=document.getElementById('nx-submit');
f.addEventListener('focusin',function(){if(!started){started=true;ev('INTEREST_FORM_STARTED',{})}});
var RE=/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/;
function say(t,ok){msg.textContent=t;msg.className='nx-msg '+(ok?'ok':'err')}
f.addEventListener('submit',function(e){e.preventDefault();if(busy)return;
 var email=(document.getElementById('nx-email').value||'').trim();var first=(document.getElementById('nx-first').value||'').trim().slice(0,60);
 if(document.getElementById('nx-company').value){say('Thanks!',true);return}
 if(!RE.test(email)||email.length>254){say('Please enter a valid email address.',false);return}
 var key='nx_lead_'+email.toLowerCase();if(lstore(key)){say("You're already on the list. We'll be in touch.",true);return}
 busy=true;btn.disabled=true;say('Sending...',true);var b=base();b.email=email;if(first)b.first_name=first;
 post('commerce_leads',b).then(function(r){if(r.status===201||r.status===409){lstore(key,'1');
   say(r.status===201?"You're on the list. We'll email you when it opens.":"You're already on the list. We'll be in touch.",true);
   ev('INTEREST_FORM_SUBMITTED',{result:r.status===201?'new':'duplicate'})}else{say('Something went wrong. Please try again.',false);ev('INTEREST_FORM_SUBMITTED',{result:'error',http:r.status})}})
  .catch(function(){say('Network error. Please try again.',false)}).then(function(){busy=false;btn.disabled=false})});
var tc=document.getElementById('nx-test-checkout');
if(C.paymentLink&&qs.get('checkout_test')==='1'&&tc){tc.style.display='inline-block';
 tc.href=C.paymentLink+'?client_reference_id='+encodeURIComponent(sid)+'&utm_content='+encodeURIComponent(A.content_variant);
 tc.addEventListener('click',function(){ev('CHECKOUT_CLICK',{mode:'TEST'})})}
if(qs.get('checkout')==='success'){ev('PURCHASE_COMPLETED',{mode:qs.get('mode')||'TEST',unverified_client_signal:true});say('Test checkout completed (no real charge).',true)}
})();
</script>
""" + END.replace("END", "SCRIPT_END")


# ---------------------------------------------------------------- R2 product truth
# Every product statement below is limited to what Printify draft 6afa4814536c7c3c520f7865
# (blueprint 478, provider 99, variant 104692) would actually ship.
STAGED_PRICE = "$24"
MOCKUP = "printify_mockup_612am_15oz_front.jpg"
BANNED = re.compile(r"stoneware|clay|handcrafted|hand-thrown|handmade|artisan|unglazed|small-batch|small batch|kiln|heft|scorch|chip in the dishwasher|engineered", re.I)

ANATOMY = """<section id="anatomy" class="anatomy-section" aria-labelledby="anatomy-title">
      <div class="anatomy-header">
        <div class="eyebrow">WHAT YOU WOULD RECEIVE</div>
        <h2 id="anatomy-title">A simple white mug for a quiet start.</h2>
        <p style="color: var(--text-secondary);">Product details come from the print partner's specification for this exact item.</p>
      </div>

      <div class="specs-list">
        <div class="spec-item">
          <div class="spec-num">01 / SIZE</div>
          <h4>15 oz white ceramic mug</h4>
          <p>Glossy white ceramic finish, printed with the 6:12 AM mark.</p>
        </div>
        <div class="spec-item">
          <div class="spec-num">02 / CARE</div>
          <h4>Microwave and dishwasher safe</h4>
          <p>BPA and lead free, per the print partner's product specification.</p>
        </div>
        <div class="spec-item">
          <div class="spec-num">03 / MADE TO ORDER</div>
          <h4>Printed on demand</h4>
          <p>Each mug is printed and shipped by our print partner after an order is placed (about 10 days handling, US shipping at cost).</p>
        </div>
      </div>
    </section>"""


def truth_rewrite(html: str) -> str:
    rep = [
        (r"<title>.*?</title>", "<title>The 6:12 AM Quiet Ritual · 15 oz White Ceramic Mug</title>"),
        (r'<meta name="description" content="[^"]*">', '<meta name="description" content="A 15 oz white ceramic mug printed with the 6:12 AM mark, for the quiet minutes before the house wakes. Studio preview - not yet for sale.">'),
        (r'<span>An Autumn & Winter Craft Concept</span>', '<span>A 15 oz White Ceramic Mug</span>'),
        (r'<div class="batch-tag">[^<]*</div>', '<div class="batch-tag">15 OZ WHITE CERAMIC · STUDIO PREVIEW</div>'),
        (r'<img src="\./meta_holiday_ceramic_mug_1794355016\.webp"[^>]*>', f'<img src="./{MOCKUP}" alt="White 15 oz ceramic mug printed with 6:12 AM, the quiet ritual (print partner mockup)" width="1200" height="1200">'),
        (r'<div class="hero-meta-badge">[^<]*</div>', '<div class="hero-meta-badge">Print partner mockup of the actual product</div>'),
        (r'<div class="eyebrow">A Counter-Holiday Domestic Anchor</div>', '<div class="eyebrow">A Counter-Holiday Morning Mug</div>'),
        (r'<p class="hero-lead">.*?</p>', '<p class="hero-lead">Before the house wakes up, before the holiday rush takes over: a 15 oz white ceramic mug for your own quiet fifteen minutes.</p>'),
        (r'(<h2 id="tension-title">We have enough holiday noise.</h2>)\s*<p>.*?</p>\s*<p>.*?</p>',
         r'\1\n      <p>December is loud. This mug carries no snowflakes and no Santas - just a small reminder to keep a few quiet minutes for yourself.</p>\n      <p>Plain white ceramic, printed with the 6:12 AM mark, made to order.</p>'),
        (r'\s*<section class="media-showcase".*?</section>\s*(?=<!-- Anatomy)', "\n\n    "),
        (r'<!-- Anatomy of Heavy Stoneware[^>]*-->\s*<section id="anatomy".*?</section>', "<!-- Product facts (R2 truth layer) -->\n    " + ANATOMY),
        (r'(<h3 id="guarantee-title">)[^<]*(</h3>)\s*<p>.*?</p>', r'\1Register interest\2\n      <p>The 6:12 AM mug is not on sale yet. Staged price: ' + STAGED_PRICE + r' plus shipping at cost. Leave your email and we will tell you when it opens.</p>'),
        (r'<div class="price">Concept Preview · Studio Edition</div>', f'<div class="price">{STAGED_PRICE} (staged) · not yet for sale</div>'),
    ]
    for pat, new in rep:
        html, n = re.subn(pat, new, html, count=1, flags=re.S)
        if n != 1:
            raise RuntimeError(f"truth_rewrite_pattern_missing:{pat[:40]}")
    return html


def visible_text(html: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))


def patch(payment_link: str = "") -> dict:
    if not BACKUP.exists():
        BACKUP.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(PAGE, BACKUP)
    html = truth_rewrite(BACKUP.read_text())  # always rebuild from the pre-conversion page (idempotent)
    # The section's dead CTA becomes the real form; the sticky bar CTA states the real action.
    html = html.replace('<a href="#preview" class="btn-primary">Request Campaign Updates</a>', FORM_HTML, 1)
    html = html.replace('class="btn-primary" style="padding: 12px 24px; font-size: 14px;">Stay Informed</a>',
                        'class="btn-primary" style="padding: 12px 24px; font-size: 14px;">Register interest</a>')
    html = html.replace("</body>", script_block(payment_link) + "</body>", 1)
    PAGE.write_text(html)
    return {"page": str(PAGE.relative_to(ROOT)), "sha256": hashlib.sha256(PAGE.read_bytes()).hexdigest(), "backup": str(BACKUP.relative_to(ROOT)),
            "form": FORM_HTML.split("\n")[0] in html, "payment_link_configured": bool(payment_link)}


if __name__ == "__main__":
    print(json.dumps(patch(sys.argv[1] if len(sys.argv) > 1 else ""), indent=1))
