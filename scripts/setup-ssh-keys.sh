#!/usr/bin/env bash

set -e

ENV_FILE="vm-config.env"
[ ! -f "$ENV_FILE" ] && { echo "Error: $ENV_FILE not found"; exit 1; }
source "$ENV_FILE"

generate_key() {
    local key_path="${1/#\~/$HOME}"
    if [ ! -f "$key_path" ]; then
        ssh-keygen -t ed25519 -f "$key_path" -N ""
    else
        echo "Key already exists: $key_path"
    fi
}

copy_key() {
    local key_path="${1/#\~/$HOME}"
    local user="$2"
    local host="$3"
    local gateway_key="${GATEWAY_KEY/#\~/$HOME}"

    ssh-copy-id -i "${key_path}.pub" \
        -o ProxyCommand="ssh -i ${gateway_key} ${SSH_OPTS} ${GATEWAY_USER}@${GATEWAY_HOST} -W %h:%p" \
        ${SSH_OPTS} "${user}@${host}"
}

generate_key "$GATEWAY_KEY"
generate_key "$VM1_SSH_KEY"
generate_key "$VM2_SSH_KEY"
generate_key "$VM3_SSH_KEY"

echo "Setting up gateway access"
gateway_key="${GATEWAY_KEY/#\~/$HOME}"
ssh-copy-id -i "${gateway_key}.pub" "${GATEWAY_USER}@${GATEWAY_HOST}"

copy_key "$VM1_SSH_KEY" "$VM1_USER" "$VM1_HOST"
copy_key "$VM2_SSH_KEY" "$VM2_USER" "$VM2_HOST"
copy_key "$VM3_SSH_KEY" "$VM3_USER" "$VM3_HOST"
