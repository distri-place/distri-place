# distri-place

A distributed r/place implementation.

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

## University VM Demo

For the university VM demo, you need to set up SSH keys first:

1. Copy `vm-config.example.env` to `vm-config.env` and update with your username
2. Generate and distribute SSH keys: `make setup-ssh`
3. Test connections: `make test-ssh`
4. Start demo with 3-pane tmux session: `make demo`
5. Run client `make client-up

