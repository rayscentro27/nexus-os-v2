#!/usr/bin/env python3
"""Fixed-path stdio-to-Unix-socket MCP proxy for the isolated canary sidecar."""
from __future__ import annotations

import json
import os
import socket
import sys

SOCKET_PATH = os.environ.get("NOVA_ACTION_CANARY_SOCKET")
if SOCKET_PATH != "/opt/data/canaries/nova-action-canary/sandbox/canary.sock":
    raise SystemExit("Canary socket path is not the approved fixed path")


def main() -> None:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(SOCKET_PATH)
    with client, client.makefile("rwb", buffering=0) as remote:
        for raw in sys.stdin.buffer:
            remote.write(raw)
            try:
                request = json.loads(raw)
            except (ValueError, TypeError):
                continue
            if "id" not in request:
                continue
            response = remote.readline()
            if not response:
                return
            sys.stdout.buffer.write(response)
            sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
