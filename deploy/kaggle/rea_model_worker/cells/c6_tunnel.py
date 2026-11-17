# ===================== CELL 6 — TEMPORARY ENDPOINT (tunnel) =====================
import re, socket, urllib.request, urllib3.util.connection as _uc
_uc.allowed_gai_family = lambda: socket.AF_INET   # no IPv6 route on Kaggle
TUNNEL_PROC = None
PUBLIC_BASE = None
NAMED_TUNNEL_HOSTNAME = "https://kaggle-model.goclearonline.cc"   # existing route -> 127.0.0.1:8080 (named mode only)
if BLOCKER is None and TUNNEL != "none":
    cf = WORK / "cloudflared"
    if not cf.exists():
        subprocess.run(["wget", "-q", "-O", str(cf),
                        f"https://github.com/cloudflare/cloudflared/releases/download/{CLOUDFLARED_VERSION}/cloudflared-linux-amd64"], check=True)
        if hashlib.sha256(cf.read_bytes()).hexdigest() != CLOUDFLARED_SHA256:
            raise RuntimeError("CLOUDFLARED_HASH_MISMATCH")
        os.chmod(cf, 0o755)
    tlog = WORK / "cloudflared.log"
    if TUNNEL == "named":
        token, _ = get_secret(SECRET_TUNNEL_TOKEN)
        if not token:
            raise RuntimeError(f"{SECRET_TUNNEL_TOKEN} secret not attached")
        tf = WORK / ".tunnel.token"; tf.write_text(token); os.chmod(tf, 0o600); del token
        TUNNEL_PROC = subprocess.Popen([str(cf), "tunnel", "--no-autoupdate", "run", "--token-file", str(tf)],
                                       stdout=open(tlog, "w"), stderr=subprocess.STDOUT, start_new_session=True)
        PUBLIC_BASE = NAMED_TUNNEL_HOSTNAME
    else:
        TUNNEL_PROC = subprocess.Popen([str(cf), "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{PORT}"],
                                       stdout=open(tlog, "w"), stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(60):
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", tlog.read_text())
            if m:
                PUBLIC_BASE = m.group(0)
                break
            time.sleep(1)
    reachable = False
    for _ in range(45):                       # DNS/edge propagation, bounded
        try:
            with urllib.request.urlopen(PUBLIC_BASE + "/health", timeout=10) as r:
                reachable = r.status == 200
        except Exception:
            pass
        if reachable:
            break
        time.sleep(2)
    kv("MODEL_ENDPOINT", (PUBLIC_BASE or "NONE") + "/v1")
    kv("ENDPOINT_TYPE", "EPHEMERAL")
    kv("ENDPOINT_PERSISTENCE", "NO")
    kv("PUBLIC_EXPOSURE", f"{'cloudflare quick tunnel' if TUNNEL == 'quick' else 'cloudflare named tunnel'} -> authenticated proxy only; "
       f"llama-server stays on loopback; reachable={'YES' if reachable else 'NO'}")
