#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2024 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------


"""Updates fetched agent with correct config"""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


def main() -> None:
    """Main"""
    load_dotenv()

    with open(Path("tsunami", "aea-config.yaml"), "r", encoding="utf-8") as file:
        config = list(yaml.safe_load_all(file))

        config[1]["config"][
            "farcaster_mnemonic"
        ] = f"${{str:{os.getenv('FARCASTER_MNEMONIC')}}}"

        config[2]["config"]["repo_id"] = f"${{str:{os.getenv('LLAMA_REPO_ID')}}}"

        config[2]["config"]["filename"] = f"${{str:{os.getenv('LLAMA_FILENAME')}}}"

        config[5]["config"]["ledger_apis"]["ethereum"][
            "address"
        ] = f"${{str:{os.getenv('ETHEREUM_LEDGER_RPC')}}}"

        config[5]["config"]["ledger_apis"]["gnosis"][
            "address"
        ] = f"${{str:{os.getenv('GNOSIS_LEDGER_RPC')}}}"

        config[7]["config"][
            "suno_session_id"
        ] = f"${{str:{os.getenv('SUNO_SESSION_ID')}}}"

        config[7]["config"]["suno_cookie"] = f"${{str:{os.getenv('SUNO_COOKIE')}}}"

        config[8]["models"]["params"]["args"][
            "twitter_credentials"
        ] = f"${{str:{os.getenv('TWITTER_CREDENTIALS')}}}"

        config[8]["models"]["params"]["args"][
            "initial_block_ethereum"
        ] = f"${{int:{int(os.getenv('INITIAL_BLOCK_ETHEREUM'))}}}"  # type: ignore

        config[8]["models"]["params"]["args"][
            "initial_block_gnosis"
        ] = f"${{int:{int(os.getenv('INITIAL_BLOCK_GNOSIS'))}}}"  # type: ignore

        config[8]["models"]["params"]["args"][
            "event_tracking_enabled"
        ] = f"${{bool:{os.getenv('EVENT_TRACKING_ENABLED')}}}"

        config[8]["models"]["params"]["args"][
            "repo_tracking_enabled"
        ] = f"${{bool:{os.getenv('REPO_TRACKING_ENABLED')}}}"

        config[8]["models"]["params"]["args"][
            "omen_tracking_enabled"
        ] = f"${{bool:{os.getenv('OMEN_TRACKING_ENABLED')}}}"

        config[8]["models"]["params"]["args"][
            "suno_enabled"
        ] = f"${{bool:{os.getenv('SUNO_ENABLED')}}}"

        config[8]["models"]["params"]["args"][
            "telegram_chat_id"
        ] = f"${{int:{os.getenv('TELEGRAM_CHAT_ID')}}}"

        config[8]["models"]["params"]["args"][
            "telegram_token"
        ] = f"${{str:{os.getenv('TELEGRAM_TOKEN')}}}"

        config[8]["models"]["params"]["args"][
            "publish_twitter"
        ] = f"${{bool:{os.getenv('PUBLISH_TWITTER')}}}"

        config[8]["models"]["params"]["args"][
            "publish_farcaster"
        ] = f"${{bool:{os.getenv('PUBLISH_FARCASTER')}}}"

        config[8]["models"]["params"]["args"][
            "publish_telegram"
        ] = f"${{bool:{os.getenv('PUBLISH_TELEGRAM')}}}"

        config[8]["models"]["params"]["args"][
            "governance_enabled"
        ] = f"${{bool:{os.getenv('GOVERNANCE_ENABLED')}}}"

        config[8]["models"]["params"]["args"][
            "boardroom_api_key"
        ] = f"${{str:{os.getenv('BOARDROOM_API_KEY')}}}"

    with open(Path("tsunami", "aea-config.yaml"), "w", encoding="utf-8") as file:
        yaml.dump_all(config, file, sort_keys=False)


if __name__ == "__main__":
    main()
