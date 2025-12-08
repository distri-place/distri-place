import logging

logger = logging.getLogger(__name__)


class SimpleLoadBalancer:
    def __init__(self, backends):
        self.backends = backends
        self.current = 0

    def get_next_backend(self):
        backend = self.backends[self.current]
        self.current = (self.current + 1) % len(self.backends)
        return backend