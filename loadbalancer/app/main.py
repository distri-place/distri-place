import http.server
import socket
import socketserver
import sys
import threading

import requests


class SimpleLoadBalancer:
    def __init__(self, backends):
        self.backends = backends
        self.current = 0

    def get_next_backend(self):
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
            if (
                self.headers.get("Upgrade", "").lower() == "websocket"
                and self.headers.get("Connection", "").lower().find("upgrade") != -1
            ):
                self.handle_websocket_upgrade()
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

    def handle_websocket_upgrade(self):
        try:
            backend = self.load_balancer.get_next_backend()
            backend_host, backend_port = backend.split(":")
            backend_port = int(backend_port)

            backend_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            backend_socket.connect((backend_host, backend_port))

            request_line = f"{self.command} {self.path} {self.request_version}\r\n"
            backend_socket.send(request_line.encode())

            for header, value in self.headers.items():
                header_line = f"{header}: {value}\r\n"
                backend_socket.send(header_line.encode())
            backend_socket.send(b"\r\n")

            response_data = b""
            while True:
                chunk = backend_socket.recv(1024)
                if not chunk:
                    break
                response_data += chunk
                if b"\r\n\r\n" in response_data:
                    break

            self.wfile.write(response_data)
            self.wfile.flush()

            client_socket = self.connection

            def forward_data(source, destination):
                try:
                    while True:
                        data = source.recv(4096)
                        if not data:
                            break
                        destination.send(data)
                except:
                    pass
                finally:
                    try:
                        source.close()
                        destination.close()
                    except:
                        pass

            t1 = threading.Thread(
                target=forward_data, args=(client_socket, backend_socket), daemon=True
            )
            t2 = threading.Thread(
                target=forward_data, args=(backend_socket, client_socket), daemon=True
            )
            t1.start()
            t2.start()
            t1.join()
            t2.join()

        except Exception as e:
            try:
                self.send_error(502, f"WebSocket upgrade failed: {str(e)}")
            except:
                pass

    def log_message(self, format, *args):
        pass


def main():
    if len(sys.argv) < 3:
        sys.exit(1)

    port = int(sys.argv[1])
    backends = sys.argv[2:]
    load_balancer = SimpleLoadBalancer(backends)

    def handler(*args, **kwargs):
        LoadBalancerHandler(*args, load_balancer=load_balancer, **kwargs)

    with socketserver.TCPServer(("0.0.0.0", port), handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
