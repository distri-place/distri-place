#!/usr/bin/env bash

# SSH utility functions for VM deployment
# This script should be sourced by other scripts that need SSH functionality

# Build SSH command with proper options
build_ssh_cmd() {
    local key=$1
    local user=$2
    local host=$3
    shift 3
    local cmd="$*"
    
    local ssh_args=(-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes -o PasswordAuthentication=no)
    
    if [[ -n "$GATEWAY_HOST" ]]; then
        if [[ -n "$GATEWAY_KEY" ]]; then
            ssh_args+=(-o ProxyCommand="ssh -o StrictHostKeyChecking=no -o BatchMode=yes -i $GATEWAY_KEY -W %h:%p $GATEWAY_USER@$GATEWAY_HOST")
        else
            ssh_args+=(-o ProxyJump="$GATEWAY_USER@$GATEWAY_HOST")
        fi
    fi
    
    ssh "${ssh_args[@]}" -i "$key" "$user@$host" "$cmd"
}

# Build SSH options string for rsync
build_ssh_opts_for_rsync() {
    local key=$1
    local opts="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes -o PasswordAuthentication=no"
    
    if [[ -n "$GATEWAY_HOST" ]]; then
        if [[ -n "$GATEWAY_KEY" ]]; then
            opts="$opts -o ProxyCommand='ssh -o StrictHostKeyChecking=no -o BatchMode=yes -i $GATEWAY_KEY -W %h:%p $GATEWAY_USER@$GATEWAY_HOST'"
        else
            opts="$opts -o ProxyJump=$GATEWAY_USER@$GATEWAY_HOST"
        fi
    fi
    
    echo "$opts -i $key"
}

# Run SSH with heredoc
ssh_with_heredoc() {
    local key=$1
    local user=$2
    local host=$3
    
    local ssh_args=(-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes -o PasswordAuthentication=no)
    
    if [[ -n "$GATEWAY_HOST" ]]; then
        if [[ -n "$GATEWAY_KEY" ]]; then
            ssh_args+=(-o ProxyCommand="ssh -o StrictHostKeyChecking=no -o BatchMode=yes -i $GATEWAY_KEY -W %h:%p $GATEWAY_USER@$GATEWAY_HOST")
        else
            ssh_args+=(-o ProxyJump="$GATEWAY_USER@$GATEWAY_HOST")
        fi
    fi
    
    ssh "${ssh_args[@]}" -i "$key" "$user@$host"
}

# Test SSH connectivity
test_ssh() {
    local host=$1
    local user=$2
    local key=$3
    
    build_ssh_cmd "$key" "$user" "$host" "echo 'SSH connection successful'"
}

# Find an available port on remote host
find_available_port() {
    local host=$1
    local user=$2
    local key=$3
    local start_port=${4:-$PORT_START}
    local end_port=${5:-$PORT_END}

    for port in $(seq "$start_port" "$end_port"); do
        if build_ssh_cmd "$key" "$user" "$host" "! ss -tuln | grep -q :$port" 2>/dev/null; then
            echo "$port"
            return 0
        fi
    done

    return 1
}