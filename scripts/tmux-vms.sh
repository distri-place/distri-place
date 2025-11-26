#!/usr/bin/env bash

ENV_FILE="vm-config.env"
source "$ENV_FILE"

tmux kill-session -t vms 2>/dev/null || true

tmux new-session -d -s vms
tmux split-window -h -t vms
tmux split-window -h -t vms
tmux select-layout -t vms even-horizontal

tmux send-keys -t vms.1 "ssh ${SSH_OPTS} -i ${VM1_SSH_KEY} -o ProxyCommand=\"ssh -i ${GATEWAY_KEY} ${SSH_OPTS} ${GATEWAY_USER}@${GATEWAY_HOST} -W %h:%p\" ${VM1_USER}@${VM1_HOST}" Enter
tmux send-keys -t vms.2 "ssh ${SSH_OPTS} -i ${VM2_SSH_KEY} -o ProxyCommand=\"ssh -i ${GATEWAY_KEY} ${SSH_OPTS} ${GATEWAY_USER}@${GATEWAY_HOST} -W %h:%p\" ${VM2_USER}@${VM2_HOST}" Enter
tmux send-keys -t vms.3 "ssh ${SSH_OPTS} -i ${VM3_SSH_KEY} -o ProxyCommand=\"ssh -i ${GATEWAY_KEY} ${SSH_OPTS} ${GATEWAY_USER}@${GATEWAY_HOST} -W %h:%p\" ${VM3_USER}@${VM3_HOST}" Enter

if [ -n "$TMUX" ]; then
    tmux switch-client -t vms
else
    tmux attach-session -t vms
fi
