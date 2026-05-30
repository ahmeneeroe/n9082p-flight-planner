"""Local dev server for the N9082P flight planner -- mirrors the Lambda handler.

    python3 app/devserver.py [port]                     # default 8000, open
    PLANNER_PASSWORD=secret python3 app/devserver.py     # exercise the login page
                                                         # (note: cookie is Secure, so
                                                         #  the browser won't keep it over
                                                         #  plain http://localhost -- test
                                                         #  the password path via curl)

Then open http://localhost:8000/
"""
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(__file__))
from handler import handle  # noqa: E402


class _Handler(BaseHTTPRequestHandler):
    def _dispatch(self, method, body=""):
        parts = urlsplit(self.path)
        if method == "GET" and parts.path not in ("/", "/plan", "/login", ""):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return
        hdrs = {k.lower(): v for k, v in self.headers.items()}
        status, out_headers, out = handle(method, parts.query, hdrs, body, None)
        data = out.encode("utf-8")
        self.send_response(status)
        for k, v in out_headers.items():
            self.send_header("Set-Cookie" if k == "set-cookie" else k, v)
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        length = int(self.headers.get("content-length", 0) or 0)
        body = self.rfile.read(length).decode("utf-8") if length else ""
        self._dispatch("POST", body)

    def log_message(self, fmt, *args):
        pass  # quiet


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    pw = "set" if os.environ.get("PLANNER_PASSWORD") else "none (open)"
    print(f"N9082P planner -> http://localhost:{port}/   [password: {pw}]")
    ThreadingHTTPServer(("127.0.0.1", port), _Handler).serve_forever()
