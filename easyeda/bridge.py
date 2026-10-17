"""Tiny client for EasyEDA's official bridge server (easyeda/easyeda-api-skill).

How it works:
  Python --HTTP--> bridge server (Node.js, port 49620-49629) --WebSocket--> EasyEDA Pro
We send a string of JavaScript; EasyEDA runs it as  async function(eda) { ... }
and sends back whatever the code `return`s.

Owner: Shammas.  Uses only the Python standard library.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

PORTS = range(49620, 49630)
SERVICE_ID = "easyeda-bridge"


class BridgeError(RuntimeError):
    """Anything that went wrong talking to EasyEDA."""


def _get_json(url: str, timeout: float) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def find_bridge() -> str:
    """Scan the port range and return e.g. 'http://127.0.0.1:49620'."""
    for port in PORTS:
        base = f"http://127.0.0.1:{port}"
        try:
            if _get_json(base + "/health", timeout=0.8).get("service") == SERVICE_ID:
                return base
        except (OSError, ValueError):
            continue
    raise BridgeError("Bridge server not found on ports 49620-49629. "
                      "Start it with:  node scripts/bridge-server.mjs  (in the easyeda-api-skill folder)")


class Bridge:
    def __init__(self, base_url: str | None = None):
        self.base = base_url or find_bridge()

    def health(self) -> dict:
        return _get_json(self.base + "/health", timeout=3)

    def run(self, js_code: str, timeout: float = 35) -> object:
        """Run JavaScript inside EasyEDA and return its `return` value.

        The bridge itself gives up after 30 s, so keep each call short.
        Don't put // comments in js_code: EasyEDA may run it as one line.
        """
        body = json.dumps({"code": js_code}).encode("utf-8")
        req = urllib.request.Request(self.base + "/execute", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                reply = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:          # bridge answered with an error code
            try:
                reply = json.loads(e.read().decode("utf-8"))
            except ValueError:
                raise BridgeError(f"HTTP {e.code} from bridge") from e
        except OSError as e:
            raise BridgeError(f"Could not reach the bridge: {e}") from e

        if not reply.get("success"):
            raise BridgeError(reply.get("error", "unknown error from EasyEDA"))
        return reply.get("result")


def js_value(value: object) -> str:
    """Turn a Python value into a JavaScript literal (JSON is valid JS)."""
    return json.dumps(value)
