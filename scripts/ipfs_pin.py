from aea_cli_ipfs.ipfs_utils import IPFSTool
import os
from pathlib import Path
import json

MINT_PATH = Path(".", "mints")
MINT_FILE = "mints.json"
IPFS_NODE = "/dns/registry.autonolas.tech/tcp/443/https"
IPFS_GATEWAY = "https://gateway.autonolas.tech/ipfs/"


if __name__ == "__main__":

    ipfs_tool = IPFSTool(IPFS_NODE)
    image_to_hash = {}

    for file in os.listdir(MINT_PATH):
        if file.endswith(".jpg"):
            image_path = Path(MINT_PATH, file)

            _, hash_, _ = ipfs_tool.add(
                dir_path=image_path,
                pin=True,
                wrap_with_directory=False
            )
            image_to_hash[image_path.stem] = {"id": None, "image_hash": hash_}
            print(f"Successfully stored {file}: {IPFS_GATEWAY}{hash_}")

    print(json.dumps(image_to_hash, indent=4))
    with open(Path(MINT_PATH, MINT_FILE), "w", encoding="utf-8") as out_file:
        json.dump(image_to_hash, out_file, indent=4)