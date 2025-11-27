# distri-place

## Starting

```bash
docker-compose up --build
```

## University VM Demo

For the university VM demo, you need to set up SSH keys first:

1. Copy `vm-config.example.env` to `vm-config.env` and update with your username
2. Generate and distribute SSH keys: `make setup-ssh`
3. Test connections: `make test-ssh`
4. Start demo with 3-pane tmux session: `make demo`