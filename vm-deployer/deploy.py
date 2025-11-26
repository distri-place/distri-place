#!/usr/bin/env python3

import concurrent.futures
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class VMConfig:
    host: str
    user: str
    ssh_key: str


@dataclass
class Config:
    username: str
    vms: List[VMConfig]
    gateway_host: str
    gateway_user: str
    gateway_key: str
    port_start: int = 8000
    port_end: int = 8010
    remote_app_dir: str = "/home/{}/distri-place"


class VMDeployer:
    def __init__(self, root_dir: str | None = None):
        self.root_dir = root_dir or os.path.dirname(os.path.abspath(__file__ + "/../"))
        self.config = self.load_config()
        self.vm_endpoints: Dict[int, str] = {}
        self.lb_process = None
        self.vm_processes: Dict[int, subprocess.Popen] = {}

    def load_config(self) -> Config:
        env_vars = {}
        config_file = os.path.join(self.root_dir, "vm-config.env")

        if not os.path.exists(config_file):
            raise FileNotFoundError("vm-config.env not found")

        with open(config_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        while "${" in value and "}" in value:
                            start = value.find("${")
                            end = value.find("}", start)
                            if start != -1 and end != -1:
                                var_name = value[start + 2 : end]
                                var_value = env_vars.get(
                                    var_name, os.environ.get(var_name, "")
                                )
                                value = value[:start] + var_value + value[end + 1 :]
                            else:
                                break
                        env_vars[key] = value

        username = env_vars["USERNAME"]
        vms = []
        for i in [1, 2, 3]:
            vms.append(
                VMConfig(
                    host=env_vars[f"VM{i}_HOST"],
                    user=env_vars[f"VM{i}_USER"],
                    ssh_key=os.path.expanduser(env_vars[f"VM{i}_SSH_KEY"]),
                )
            )

        return Config(
            username=username,
            vms=vms,
            gateway_host=env_vars["GATEWAY_HOST"],
            gateway_user=env_vars["GATEWAY_USER"],
            gateway_key=os.path.expanduser(env_vars["GATEWAY_KEY"]),
            port_start=int(env_vars.get("PORT_START", 8000)),
            port_end=int(env_vars.get("PORT_END", 8010)),
            remote_app_dir=env_vars["REMOTE_APP_DIR"],
        )

    def run_ssh_cmd(
        self, vm: VMConfig, cmd: str, timeout: int = 30
    ) -> subprocess.CompletedProcess:
        ssh_cmd = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "BatchMode=yes",
            "-o",
            f"ProxyCommand=ssh -o StrictHostKeyChecking=no -o BatchMode=yes -i {self.config.gateway_key} -W %h:%p {self.config.gateway_user}@{self.config.gateway_host}",
            "-i",
            vm.ssh_key,
            f"{vm.user}@{vm.host}",
            cmd,
        ]
        return subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)

    def find_available_port(self, vm: VMConfig) -> Optional[int]:
        for port in range(self.config.port_start, self.config.port_end + 1):
            try:
                result = self.run_ssh_cmd(
                    vm, f"! ss -tuln | grep -q :{port}", timeout=10
                )
                if result.returncode == 0:
                    return port
            except subprocess.TimeoutExpired:
                continue
        return None

    def deploy_to_vm(self, vm_num: int, vm: VMConfig) -> bool:
        print(f"Deploying to VM{vm_num} ({vm.host})")

        try:
            result = self.run_ssh_cmd(vm, "echo 'SSH test'", timeout=10)
            if result.returncode != 0:
                print(f"Cannot connect to VM{vm_num}")
                return False

            port = self.find_available_port(vm)
            if not port:
                print(f"No available ports on VM{vm_num}")
                return False

            print(f"Using port {port} on VM{vm_num}")

            self.run_ssh_cmd(vm, f"mkdir -p {self.config.remote_app_dir}")

            server_dir = os.path.join(self.root_dir, "server")
            rsync_cmd = [
                "rsync",
                "-avz",
                "--delete",
                "--exclude=venv",
                "-e",
                f"ssh -o StrictHostKeyChecking=no -o ProxyCommand='ssh -o StrictHostKeyChecking=no -i {self.config.gateway_key} -W %h:%p {self.config.gateway_user}@{self.config.gateway_host}' -i {vm.ssh_key}",
                f"{server_dir}/",
                f"{vm.user}@{vm.host}:{self.config.remote_app_dir}/",
            ]
            result = subprocess.run(rsync_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Failed to copy code to VM{vm_num}: {result.stderr}")
                return False

            setup_cmd = f"""
            cd {self.config.remote_app_dir}
            make setup
            """

            result = self.run_ssh_cmd(vm, setup_cmd, timeout=120)
            if result.returncode != 0:
                print(f"Failed to setup environment on VM{vm_num}: {result.stderr}")
                return False

            start_cmd = f"cd {self.config.remote_app_dir} && make start-node NODE_ID=node-{vm_num} PORT={port} HOST=0.0.0.0"

            ssh_cmd = [
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "ConnectTimeout=10",
                "-o",
                "BatchMode=yes",
                "-o",
                f"ProxyCommand=ssh -o StrictHostKeyChecking=no -o BatchMode=yes -i {self.config.gateway_key} -W %h:%p {self.config.gateway_user}@{self.config.gateway_host}",
                "-i",
                vm.ssh_key,
                f"{vm.user}@{vm.host}",
                start_cmd,
            ]

            process = subprocess.Popen(
                ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            self.vm_processes[vm_num] = process

            time.sleep(3)
            if process.poll() is None:
                self.vm_endpoints[vm_num] = f"{vm.host}:{port}"
                print(f"VM{vm_num} deployed successfully on {vm.host}:{port}")
                return True
            else:
                stdout, stderr = process.communicate()
                print(f"Failed to start service on VM{vm_num}: {stderr}")
                return False

        except Exception as e:
            print(f"Error deploying VM{vm_num}: {e}")
            return False

    def deploy_all_vms(self) -> bool:
        print("Starting VM deployment")

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_vm = {
                executor.submit(self.deploy_to_vm, i + 1, vm): i + 1
                for i, vm in enumerate(self.config.vms)
            }

            success_count = 0
            for future in concurrent.futures.as_completed(future_to_vm):
                vm_num = future_to_vm[future]
                try:
                    if future.result():
                        success_count += 1
                except Exception as e:
                    print(f"VM{vm_num} deployment failed: {e}")

        print(f"Deployment complete: {success_count}/3 VMs deployed successfully")
        return success_count == 3

    def start_load_balancer(self):
        """Start load balancer on gateway and set up port forwarding"""
        backends = list(self.vm_endpoints.values())
        print(f"Starting load balancer on gateway with backends: {backends}")

        lb_dir = os.path.join(self.root_dir, "loadbalancer")
        rsync_cmd = [
            "rsync",
            "-avz",
            "--delete",
            "-e",
            f"ssh -o StrictHostKeyChecking=no -i {self.config.gateway_key}",
            f"{lb_dir}/",
            f"{self.config.gateway_user}@{self.config.gateway_host}:~/loadbalancer/",
        ]
        result = subprocess.run(rsync_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Failed to copy load balancer to gateway: {result.stderr}")
            return

        backends_str = " ".join(backends)
        start_cmd = f"cd loadbalancer && python3 loadbalancer.py 8080 {backends_str}"

        ssh_cmd = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-i",
            self.config.gateway_key,
            f"{self.config.gateway_user}@{self.config.gateway_host}",
            start_cmd,
        ]

        lb_ssh_process = subprocess.Popen(
            ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        print("Load balancer started on gateway")

        print("Setting up SSH port forwarding from gateway to localhost:8080")
        forward_cmd = [
            "ssh",
            "-N",
            "-L",
            "8080:localhost:8080",
            "-o",
            "StrictHostKeyChecking=no",
            "-i",
            self.config.gateway_key,
            f"{self.config.gateway_user}@{self.config.gateway_host}",
        ]
        self.lb_process = subprocess.Popen(forward_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.vm_processes[0] = lb_ssh_process  # Use 0 for load balancer
        print("Load balancer started on gateway with port forwarding")

    def deploy(self):
        # Set up signal handler for clean shutdown
        def signal_handler(sig, frame):
            print("\nReceived shutdown signal, cleaning up...")
            self.cleanup()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            if not self.deploy_all_vms():
                print("VM deployment failed")
                return False

            self.start_load_balancer()

            print("Deployment successful!")
            print("Load balancer available at http://localhost:8080")
            print("Press Ctrl+C to stop")

            # Keep running and monitor processes
            while True:
                # Check if any process died
                dead_processes = []
                for vm_num, process in self.vm_processes.items():
                    if process.poll() is not None:
                        dead_processes.append(vm_num)
                
                if dead_processes:
                    for vm_num in dead_processes:
                        if vm_num == 0:
                            print("Load balancer process died!")
                        else:
                            print(f"VM{vm_num} process died!")
                    break
                
                time.sleep(1)

        except Exception as e:
            print(f"Error: {e}")
            return False
        finally:
            self.cleanup()

    def cleanup(self):
        print("Cleaning up all processes...")
        
        # Kill port forwarding process
        if self.lb_process:
            self.lb_process.terminate()
            try:
                self.lb_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.lb_process.kill()

        # Kill all SSH processes (VMs and load balancer)
        for vm_num, process in self.vm_processes.items():
            if vm_num == 0:
                print("Stopping load balancer...")
            else:
                print(f"Stopping VM{vm_num} service...")
            
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        
        print("All processes stopped")

    def test_ssh(self):
        print("Testing SSH connections...")
        for i, vm in enumerate(self.config.vms, 1):
            try:
                result = self.run_ssh_cmd(vm, "echo 'SSH test'", timeout=10)
                if result.returncode == 0:
                    print(f"VM{i} SSH: OK")
                else:
                    print(f"VM{i} SSH: FAILED")
            except Exception as e:
                print(f"VM{i} SSH: ERROR - {e}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "test-ssh":
        deployer = VMDeployer()
        deployer.test_ssh()
    else:
        deployer = VMDeployer()
        deployer.deploy()


if __name__ == "__main__":
    main()
