from __future__ import annotations

import json
import subprocess
import sys


def main() -> int:
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "calyx_scope", "arguments": {}},
    }
    body = json.dumps(message, separators=(",", ":")).encode("utf-8")
    wire = b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body
    proc = subprocess.Popen(
        [sys.executable, "-m", "calyx.mcp_server.server", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = proc.communicate(wire, timeout=10)
    text = out.decode("utf-8", errors="replace")
    if err:
        print(err.decode("utf-8", errors="replace"), file=sys.stderr)
    print(text)
    try:
        _, raw_body = text.split("\r\n\r\n", 1)
        response = json.loads(raw_body)
        content_text = response["result"]["content"][0]["text"]
        scope = json.loads(content_text)
        roots = {root["path"] for root in scope["allowed_roots"]}
    except Exception:
        return 1
    if scope.get("server") != "station-calyx-local" or "D:\\Calyx_Data" not in roots:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
