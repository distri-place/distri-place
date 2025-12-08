import socketserver
import sys

from app.http_handler import LoadBalancerHandler
from app.load_balancer import SimpleLoadBalancer
from app.utils import logger as _  # noqa: F401 - Import to configure logging


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
