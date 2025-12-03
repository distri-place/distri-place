import http.server
import socketserver
import sys
import threading
import urllib.request


class RoundRobinLoadBalancer:
    def __init__(self, backends):
        self.backends = backends
        self.current = 0
        self.lock = threading.Lock()

    def get_next_backend(self):
        with self.lock:
            backend = self.backends[self.current]
            self.current = (self.current + 1) % len(self.backends)
            return backend


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
            backend = self.load_balancer.get_next_backend()
            target_url = f"http://{backend}{self.path}"

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b""

            req = urllib.request.Request(target_url, data=body, method=self.command)

            for header, value in self.headers.items():
                if header.lower() not in ["connection", "host"]:
                    req.add_header(header, value)

            with urllib.request.urlopen(req, timeout=10) as response:
                self.send_response(response.getcode())
                for header, value in response.headers.items():
                    if header.lower() not in ["connection", "transfer-encoding"]:
                        self.send_header(header, value)
                self.end_headers()
                self.wfile.write(response.read())

        except Exception as e:
            print(f"Error: {e}")
            self.send_error(502, str(e))

    def log_message(self, format, *args):
        pass


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 loadbalancer.py <port> <backend1:port1> [backend2:port2] ...")
        sys.exit(1)

    port = int(sys.argv[1])
    backends = sys.argv[2:]

    print(f"Load balancer on port {port}, backends: {backends}")

    load_balancer = RoundRobinLoadBalancer(backends)

    def handler(*args, **kwargs):
        LoadBalancerHandler(*args, load_balancer=load_balancer, **kwargs)

    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
