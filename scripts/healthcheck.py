#!/usr/bin/env python3
"""
scripts/healthcheck.py

Container healthcheck. Fails (exit non-zero) when either:
- the OET corpus DB is missing/invalid (a Git-LFS pointer file, corrupt DB, ...), or
- the mcp-proxy HTTP server is not accepting connections on the MCP port.

Side-effect free: the TCP check opens and closes a connection without issuing a
request, so it does not create MCP sessions.
"""

import os
import socket
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from verify_db import check  # noqa: E402


def main():
    if not check():
        return 1

    port = int(os.environ.get("PORT", "8080"))
    try:
        sock = socket.create_connection(("127.0.0.1", port), timeout=5)
        sock.close()
    except OSError as e:
        print(f"FAIL: MCP proxy not accepting connections on 127.0.0.1:{port} ({e})",
              file=sys.stderr)
        return 1

    print(f"OK: DB valid, MCP proxy accepting connections on 127.0.0.1:{port}")
    return 0


if __name__ == "__main__":
    sys.exit(main())