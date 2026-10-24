"""Tests the Python side of the bridge with a fake bridge server.
No EasyEDA, no Node.js, no API key needed."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from easyeda.bridge import Bridge, BridgeError
from easyeda.spike import NETS, PARTS, js_schematic, looks_smd


class FakeBridge(BaseHTTPRequestHandler):
    def do_GET(self):
        self._send(200, {"service": "easyeda-bridge", "edaConnected": True})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if "boom" in body["code"]:
            self._send(500, {"success": False, "error": "EasyEDA said no"})
        else:
            self._send(200, {"success": True, "result": {"echo": body["code"]}})

    def _send(self, code, data):
        raw = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):        # keep test output quiet
        pass


@pytest.fixture
def bridge():
    server = HTTPServer(("127.0.0.1", 0), FakeBridge)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield Bridge(f"http://127.0.0.1:{server.server_port}")
    server.shutdown()


def test_health(bridge):
    assert bridge.health()["service"] == "easyeda-bridge"


def test_run_returns_result(bridge):
    assert bridge.run("return 1;") == {"echo": "return 1;"}


def test_error_becomes_bridge_error(bridge):
    with pytest.raises(BridgeError, match="EasyEDA said no"):
        bridge.run("boom")


def test_smd_guard():
    assert looks_smd("C0805")
    assert looks_smd("SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR")
    assert not looks_smd("TO-220-3_L10.0-W4.5-P2.54-L")


def test_every_net_pin_belongs_to_a_part():
    refs = {p["ref"] for p in PARTS}
    assert set(NETS) == refs


def test_schematic_js_contains_all_parts():
    js = js_schematic(PARTS, NETS)
    for p in PARTS:
        assert p["lcsc"] in js
    assert "//" not in js                 # no JS comments (EasyEDA may run it as one line)
