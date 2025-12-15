# distri-place

A distributed r/place implementation.

## Demo video

[![Demo Video](https://img.youtube.com/vi/-ALniSWCHyc/0.jpg)](https://www.youtube.com/watch?v=-ALniSWCHyc)

## Quick Start

### Development

```bash
make dev        # Build and run the full system with logs
make dev-up     # Just start the containers
make dev-down   # Stop everything
make dev-logs   # View logs
```

### Demo

```bash
make demo       # Run demo on university VMs using tmux
make setup-ssh  # Setup SSH keys for university VMs
make test-ssh   # Test SSH connections to university VMs
```

### Client Only

```bash
make client-up    # Run just the client
make client-down  # Stop client
make client-logs  # View client logs
```

## University Demo

### Prerequisites

1. **Setup VM Configuration**: Copy `vm-config.example.env` to `vm-config.env` and update with your vms
2. **Setup SSH Keys**: Run `make setup-vms` to generate and distribute SSH keys to the VMs
3. **Test SSH Connections**: Verify connectivity with `make test-ssh`

### Running the Demo

#### Step 1: Initialize tmux Session

```bash
make demo
```

This command sets up a tmux session and opens a port forward from melkki to localhost:8080.

#### Step 2: Start Server Nodes

On each of the **svmc** VMs:

1. Clone the repository:
   ```bash
   git clone <repository-url> distri-place
   cd distri-place/server
   ```
2. Start the server node (use different node numbers for each VM):

   ```bash
   # On svmc1:
   make start-node-1

   # On svmc2:
   make start-node-2

   # On svmc3:
   make start-node-3
   ```

#### Step 3: Start Load Balancer

On the **melkki** VM:

1. Clone the repository:
   ```bash
   git clone <repository-url> distri-place
   cd distri-place/loadbalancer
   ```
2. Start the load balancer demo:
   ```bash
   make start-demo
   ```

#### Step 4: Start Client

From the base directory on your local machine:

```bash
make client-up
```

### Accessing the Demo

Once all components are running:

- The demo will be accessible at **http://localhost:3000**
- The `make demo` command automatically sets up port forwarding from melkki (8080) to your local machine
- The client connects through this port forward to interact with the distributed system

### Demo Architecture Overview

The demo runs across multiple university VMs:

- **svmc VMs**: Run distributed server nodes
- **melkki VM**: Runs the load balancer with port forwarding to localhost:8080
- **Local machine**: Runs the client interface accessible at localhost:3000
