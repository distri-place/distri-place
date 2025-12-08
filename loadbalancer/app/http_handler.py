import http.server
import logging

import requests

from app.websocket_handler import handle_websocket_upgrade

logger = logging.getLogger(__name__)


class LoadBalancerHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, *args, load_balancer=None, **kwargs):
        self.load_balancer = load_balancer
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.proxy_request()

    def do_POST(self):
        self.proxy_request()

    def proxy_request(self):
        try:
            if (
                self.headers.get("Upgrade", "").lower() == "websocket"
                and self.headers.get("Connection", "").lower().find("upgrade") != -1
            ):
                handle_websocket_upgrade(self, self.load_balancer)
                return

            backend = self.load_balancer.get_next_backend()
            target_url = f"http://{backend}{self.path}"
            headers = dict(self.headers)
            headers.pop("host", None)
            headers.pop("connection", None)

            if self.command == "POST":
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length)
                response = requests.post(target_url, data=body, headers=headers, timeout=10)
            else:
                response = requests.get(target_url, headers=headers, timeout=10)

            self.send_response(response.status_code)
            for key, value in response.headers.items():
                if key.lower() not in ["connection", "transfer-encoding", "content-encoding"]:
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response.content)

        except Exception as e:
            self.send_error(502, f"Bad Gateway: {str(e)}")

    def log_message(self, format, *args):
        pass