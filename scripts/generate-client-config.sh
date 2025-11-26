#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

VM_ENDPOINTS=()
for vm in 1 2 3; do
    endpoint_file="$ROOT_DIR/.vm${vm}_endpoint"
    if [[ -f "$endpoint_file" ]]; then
        endpoint=$(cat "$endpoint_file")
        VM_ENDPOINTS+=("$endpoint")
        echo -e "Found VM$vm endpoint: $endpoint"
    else
        echo -e "Warning: VM$vm endpoint not found"
    fi
done

if [[ ${#VM_ENDPOINTS[@]} -eq 0 ]]; then
    echo "Error: No VM endpoints found. Deploy VMs first."
    exit 1
fi

echo -e "Generating nginx configuration for VM deployment"

cat > "$ROOT_DIR/nginx/nginx-vm.conf" << 'EOF'
user  nginx;
worker_processes  auto;

events {
    worker_connections  1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout  65;

    # Upstream for VM servers
    upstream vm_servers {
EOF

# Add VM endpoints to upstream
for endpoint in "${VM_ENDPOINTS[@]}"; do
    echo "        server $endpoint max_fails=3 fail_timeout=30s;" >> "$ROOT_DIR/nginx/nginx-vm.conf"
done

cat >> "$ROOT_DIR/nginx/nginx-vm.conf" << 'EOF'
        # Load balancing method
        least_conn;
    }

    server {
        listen 8080;
        server_name _;

        # Serve static files
        root /usr/share/nginx/html;
        index index.html;

        # Static assets & SPA fallback
        location / {
            try_files $uri $uri/ /index.html;
        }

        # WebSocket endpoint
        location /ws/ {
            proxy_pass http://vm_servers;

            proxy_http_version 1.1;

            # WebSocket headers
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "Upgrade";

            # Preserve host and IP info
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts
            proxy_read_timeout 600s;
            proxy_send_timeout 600s;
        }

        # API endpoints
        location /client/ {
            proxy_pass http://vm_servers;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts for API calls
            proxy_read_timeout 30s;
            proxy_send_timeout 30s;
        }

        # Health check endpoint
        location /health {
            proxy_pass http://vm_servers;
            proxy_set_header Host $host;
        }
    }
}
EOF

echo -e "VM Endpoints: ${VM_ENDPOINTS[*]}"
