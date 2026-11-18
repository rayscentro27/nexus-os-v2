"""Inert, network-free process used only by Nova release certification."""
from __future__ import annotations

import argparse
import os
import signal
import time


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hold", action="store_true")
    parser.add_argument("--exit-immediately", action="store_true")
    args = parser.parse_args()
    release_id = os.environ.get("NOVA_CERT_RELEASE_ID", "UNKNOWN")
    print(f"RELEASE_ID={release_id}", flush=True)
    if args.exit_immediately:
        return 23
    if not args.hold:
        return 2
    running = True

    def stop(_signum, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while running:
        time.sleep(0.2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
