from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest

from prototype.status_checker.status_checker import check_status


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "http://example.com/")
            self.end_headers()
            return
        code = 500 if self.path == "/error" else 200
        self.send_response(code)
        self.end_headers()
        self.wfile.write(b"controlled")

    def log_message(self, *_args):
        pass


@pytest.fixture
def local_server():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_local_canary_classifies_success_and_http_error(local_server):
    assert check_status(local_server + "/")['classification'] == "UP"
    assert check_status(local_server + "/error")['classification'] == "HTTP_ERROR"


def test_local_canary_blocks_redirect_and_non_loopback(local_server):
    result = check_status(local_server + "/redirect")
    assert result['classification'] == "REDIRECT_BLOCKED"
    assert result['redirect_followed'] is False
    with pytest.raises(ValueError, match="localhost"):
        check_status("http://example.com/")
