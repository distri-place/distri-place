#!/usr/bin/env python3
import argparse
from pathlib import Path
import subprocess
import sys
import time


class ClusterManager:
    def __init__(self, num_nodes: int = 3, base_port: int = 8000):
        self.num_nodes = num_nodes
        self.base_port = base_port
        self.processes = []
        self.server_dir = Path(__file__).parent.parent

    def start_cluster(self):
        print(f"Starting cluster with {self.num_nodes} nodes...")

        try:
            for i in range(1, self.num_nodes + 1):
                node_id = f"node-{i}"
                port = self.base_port + i - 1

                print(f"Starting {node_id} on port {port}...")
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "app.main",
                        "--node-id",
                        node_id,
                    ],
                    cwd=self.server_dir,
                )

                self.processes.append(process)
                time.sleep(1)

            # Keep the main process alive
            while True:
                time.sleep(1)
                # Check if any process died
                for i, process in enumerate(self.processes):
                    if process.poll() is not None:
                        print(f"Node-{i + 1} has stopped unexpectedly")

        except KeyboardInterrupt:
            print("\nShutting down cluster...")
            self.stop_cluster()
        except Exception as e:
            print(f"Error: {e}")
            self.stop_cluster()
            sys.exit(1)

    def stop_cluster(self):
        for _, process in enumerate(self.processes, 1):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--nodes",
        "-n",
        type=int,
        default=3,
        help="Number of nodes to start",
    )
    parser.add_argument(
        "--base-port",
        "-p",
        type=int,
        default=8000,
        help="Base port number",
    )

    args = parser.parse_args()

    cluster = ClusterManager(num_nodes=args.nodes, base_port=args.base_port)
    cluster.start_cluster()


if __name__ == "__main__":
    main()
