# Tsunami service

An [Olas](https://olas.network/) [service](https://registry.olas.network/ethereum/services/23) that tracks on-chain events on the Olas ecosystem and autonomously reports on it on Twitter and Farcaster.

## System requirements

- Python `>=3.8`
- [Tendermint](https://docs.tendermint.com/v0.34/introduction/install.html) `==0.34.19`
- [IPFS node](https://docs.ipfs.io/install/command-line/#official-distributions) `==0.6.0`
- [Pip](https://pip.pypa.io/en/stable/installation/)
- [Poetry](https://python-poetry.org/)
- [Docker Engine](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)

Alternatively, you can fetch this docker image with the relevant requirements satisfied:

> **_NOTE:_**  Tendermint and IPFS dependencies are missing from the image at the moment.

```bash
docker pull valory/open-autonomy-user:latest
docker container run -it valory/open-autonomy-user:latest
```


## Run you own instance

1. Clone this repo:

    ```git clone git@github.com:dvilelaf/tsunami.git```

2. Create the virtual environment:

    ```poetry shell && poetry install```

3. Sync packages:

    ```autonomy packages sync --update-packages```

### Run as agent

1. Modify `packages/dvilela/agents/tsunami/aea-config.yaml` and set the correct values for at least `farcaster_mnemonic`, `twitter_credentials`, `ethereum_ledger_rpc` and `gnosis_ledger_rpc`.


2. Run the script:

    ```bash run_agent.sh```

3. In other terminal, run a tendermint node. From the repo's root:

    ```make tm```


### Run as service

1. Make a copy of the env file:
    ```cp sample.env .env```

2. Fill in the required environment variables in .env.

3. Run the script:

    ```bash run_service.sh```