#!/usr/bin/env bash

# Set env vars
export $(grep -v '^#' .env | xargs)

# Push packages and fetch service
make clean

autonomy push-all

autonomy fetch --local --service dvilela/tsunami && cd tsunami

# Build the image
autonomy init --reset --author dvilela --remote --ipfs --ipfs-node "/dns/registry.autonolas.tech/tcp/443/https"
autonomy build-image

# Copy the keys and build the deployment
cp $KEY_DIR/keys.json .
autonomy deploy build -ltm

# Run the deployment
autonomy deploy run --build-dir abci_build/