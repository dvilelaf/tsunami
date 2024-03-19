#!/usr/bin/env bash

REPO_PATH=$PWD

# Push packages and fetch service
make clean

autonomy push-all

autonomy fetch --local --service dvilela/tsunami && cd tsunami

# Build the image
autonomy init --reset --author dvilela --remote --ipfs --ipfs-node "/dns/registry.autonolas.tech/tcp/443/https"
autonomy build-image

# Copy .env file
cp $REPO_PATH/.env .

# Copy the keys and build the deployment
cp $REPO_PATH/keys.json .

autonomy deploy build -ltm --agent-cpu-limit 4.0 --agent-memory-limit 8192 --agent-memory-request 1024

# Run the deployment
autonomy deploy run --build-dir abci_build/
