#!/usr/bin/env bash

ENV_FILE="vm-config.env"
source "$ENV_FILE"

echo "Testing SSH connections..."

echo "Testing VM1: ${VM1_USER}@${VM1_HOST}"
ssh ${SSH_OPTS} -i ${VM1_SSH_KEY} -o ProxyCommand="ssh -i ${GATEWAY_KEY} ${SSH_OPTS} ${GATEWAY_USER}@${GATEWAY_HOST} -W %h:%p" ${VM1_USER}@${VM1_HOST} "echo 'VM1 connection successful'" || echo "VM1 connection failed"

echo "Testing VM2: ${VM2_USER}@${VM2_HOST}"
ssh ${SSH_OPTS} -i ${VM2_SSH_KEY} -o ProxyCommand="ssh -i ${GATEWAY_KEY} ${SSH_OPTS} ${GATEWAY_USER}@${GATEWAY_HOST} -W %h:%p" ${VM2_USER}@${VM2_HOST} "echo 'VM2 connection successful'" || echo "VM2 connection failed"

echo "Testing VM3: ${VM3_USER}@${VM3_HOST}"
ssh ${SSH_OPTS} -i ${VM3_SSH_KEY} -o ProxyCommand="ssh -i ${GATEWAY_KEY} ${SSH_OPTS} ${GATEWAY_USER}@${GATEWAY_HOST} -W %h:%p" ${VM3_USER}@${VM3_HOST} "echo 'VM3 connection successful'" || echo "VM3 connection failed"

echo "SSH testing complete."