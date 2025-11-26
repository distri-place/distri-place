#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

CONFIG_FILE="$ROOT_DIR/vm-config.env"
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo -e "Error: Configuration file not found. Create vm-config.env"
    exit 1
fi

source "$CONFIG_FILE"
source "$SCRIPT_DIR/_utils.sh"

echo -e "Loading configuration from: $CONFIG_FILE"

deploy_to_vm() {
    local vm_num=$1
    local host_var="VM${vm_num}_HOST"
    local user_var="VM${vm_num}_USER"
    local key_var="VM${vm_num}_SSH_KEY"

    local host=${!host_var}
    local user=${!user_var}
    local key=${!key_var}

    if [[ -z "$host" || -z "$user" || -z "$key" ]]; then
        echo -e "VM$vm_num configuration incomplete"
        return 1
    fi

    echo -e "Deploying to VM$vm_num ($host)"

    if ! test_ssh "$host" "$user" "$key" >/dev/null 2>&1; then
        echo -e "Cannot connect to VM$vm_num ($host)"
        return 1
    fi

    echo "Finding available port on VM$vm_num"
    local port=$(find_available_port "$host" "$user" "$key")
    if [[ -z "$port" ]]; then
        echo -e "No available ports found on VM$vm_num"
        return 1
    fi

    echo "Using port $port on VM$vm_num"

    build_ssh_cmd "$key" "$user" "$host" "mkdir -p $REMOTE_APP_DIR" 2>/dev/null

    echo -e "Copying server code to VM$vm_num"
    rsync -avz --delete -e "ssh $(build_ssh_opts_for_rsync $key)" \
        "$ROOT_DIR/server/" "$user@$host:$REMOTE_APP_DIR/"

    echo -e "Setting up Python environment on VM$vm_num"
    ssh_with_heredoc "$key" "$user" "$host" << EOF
        cd $REMOTE_APP_DIR

        # Check Python version
        if ! python3 --version | grep -q "Python 3\.[8-9]\|Python 3\.1[0-9]"; then
            echo "Python 3.8+ required"
            exit 1
        fi

        # Create virtual environment if it doesn't exist
        if [[ ! -d venv ]]; then
            python3 -m venv venv
        fi

        # Activate virtual environment
        source venv/bin/activate

        # Install dependencies
        if [[ -f requirements.txt ]]; then
            timeout $REQUIREMENTS_TIMEOUT pip install -r requirements.txt
        fi

        # Stop any existing process
        pkill -f "python.*main.py" || true
        sleep 2
EOF

    if [[ $? -ne 0 ]]; then
        echo -e "Failed to setup environment on VM$vm_num"
        return 1
    fi

    echo -e "Starting service on VM$vm_num:$port"
    ssh_with_heredoc "$key" "$user" "$host" << EOF
        cd $REMOTE_APP_DIR
        source venv/bin/activate

        nohup python -m app.main \
            --node-id node-$vm_num \
            --port $port \
            > logs/node-$vm_num.log 2>&1 &

        echo \$! > node-$vm_num.pid

        # Wait a moment and check if process started
        sleep 3
        if ps -p \$(cat node-$vm_num.pid) > /dev/null 2>&1; then
            echo "Service started successfully on port $port"
        else
            echo "Failed to start service"
            exit 1
        fi
EOF

    if [[ $? -eq 0 ]]; then
        echo -e "VM$vm_num deployed successfully on $host:$port"
        echo "$host:$port" > "$ROOT_DIR/.vm${vm_num}_endpoint"
    else
        echo -e "Failed to start service on VM$vm_num"
        return 1
    fi
}

main() {
    log "Starting VM deployment"

    mkdir -p "$ROOT_DIR/server/logs"

    local success_count=0
    for vm in 1 2 3; do
        if deploy_to_vm $vm; then
            ((success_count++))
        else
            echo -e "VM$vm deployment failed"
        fi
    done

    echo -e "Deployment complete: $success_count/3 VMs deployed successfully"

    if [[ $success_count -gt 0 ]]; then
        echo -e "Generating client configuration"
        "$SCRIPT_DIR/generate-client-config.sh"
    fi

    if [[ $success_count -eq 3 ]]; then
        echo -e "All VMs deployed successfully!"
    else
        echo -e "Not all VMs deployed successfully. Check the logs above."
        exit 1
    fi
}

case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "test-ssh")
        echo -e "Testing SSH connections"
        for vm in 1 2 3; do
            host_var="VM${vm}_HOST"
            user_var="VM${vm}_USER"
            key_var="VM${vm}_SSH_KEY"

            host=${!host_var}
            user=${!user_var}
            key=${!key_var}

            if test_ssh "$host" "$user" "$key"; then
                echo -e "VM$vm SSH: OK"
            else
                echo -e "VM$vm SSH: FAILED"
            fi
        done
        ;;
    *)
        error "Unknown command: $1"
        exit 1
        ;;
esac
