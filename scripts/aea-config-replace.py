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
import re
from pathlib import Path

import yaml
from dotenv import load_dotenv


AGENT_NAME = "tsunami"

PATH_TO_VAR = {
    # Chains
    "config/ledger_apis/ethereum/address": "ETHEREUM_LEDGER_RPC",
    "config/ledger_apis/gnosis/address": "GNOSIS_LEDGER_RPC",
    # Params
    "models/params/args/setup/all_participants": "ALL_PARTICIPANTS",
    "models/params/args/reset_tendermint_after": "RESET_TENDERMINT_AFTER",
    "models/params/args/reset_pause_duration": "RESET_PAUSE_DURATION",
    "models/params/args/termination_from_block": "TERMINATION_FROM_BLOCK",
    "models/params/args/fact_checker_api_key": "FACT_CHECKER_API_KEY",
    "models/params/args/enable_posting": "ENABLE_POSTING",
    "models/params/args/on_chain_service_id": "ON_CHAIN_SERVICE_ID",
    "models/params/args/max_tweets_per_period": "MAX_TWEETS_PER_PERIOD",
    "models/params/args/initial_block_ethereum": "INITIAL_BLOCK_ETHEREUM",
    "models/params/args/initial_block_gnosis": "INITIAL_BLOCK_GNOSIS",
    "models/params/args/event_tracking_enabled": "EVENT_TRACKING_ENABLED",
    "models/params/args/repo_tracking_enabled": "REPO_TRACKING_ENABLED",
    "models/params/args/omen_tracking_enabled": "OMEN_TRACKING_ENABLED",
    "models/params/args/suno_enabled": "SUNO_ENABLED",
    "models/params/args/telegram_chat_id": "TELEGRAM_CHAT_ID",
    "models/params/args/telegram_token": "TELEGRAM_TOKEN",
    "models/params/args/publish_twitter": "PUBLISH_TWITTER",
    "models/params/args/publish_farcaster": "PUBLISH_FARCASTER",
    "models/params/args/publish_telegram": "PUBLISH_TELEGRAM",
    "models/params/args/governance_enabled": "GOVERNANCE_ENABLED",
    "models/params/args/boardroom_api_key": "BOARDROOM_API_KEY",
    "models/params/args/subgraph_api_key": "SUBGRAPH_API_KEY",
    "models/params/args/use_twikit": "USE_TWIKIT",
    # Tweepy connection
    "config/twitter_credentials": "TWITTER_CREDENTIALS",
    # Twikit connection
    "config/twikit_username": "TWIKIT_USERNAME",
    "config/twikit_email": "TWIKIT_EMAIL",
    "config/twikit_password": "TWIKIT_PASSWORD",
    "config/twikit_cookies": "TWIKIT_COOKIES",
    # Farcaster
    "config/farcaster_mnemonic": "FARCASTER_MNEMONIC",
    # Llama
    "config/repo_id": "LLAMA_REPO_ID",
    "config/filename": "LLAMA_FILENAME",
    # Suno
    "config/suno_session_id": "SUNO_SESSION_ID",
    "config/suno_cookie": "SUNO_COOKIE",
    # DB
    "config/db_path": "DB_PATH",
}

CONFIG_REGEX = r"\${.*?:(.*)}"


def find_and_replace(config, path, new_value):
    """Find and replace a variable"""

    # Find the correct section where this variable fits
    section_index = None
    for i, section in enumerate(config):
        value = section
        try:
            for part in path:
                value = value[part]
            section_index = i
        except KeyError:
            continue

    # To persist the changes in the config variable,
    # access iterating the path parts but the last part
    sub_dic = config[section_index]
    for part in path[:-1]:
        sub_dic = sub_dic[part]

    # Now, get the whole string value
    old_str_value = sub_dic[path[-1]]

    # Extract the old variable value
    match = re.match(CONFIG_REGEX, old_str_value)
    old_var_value = match.groups()[0]

    # Replace the old variable with the secret value in the complete string
    new_str_value = old_str_value.replace(old_var_value, new_value)
    sub_dic[path[-1]] = new_str_value

    return config


def main() -> None:
    """Main"""
    load_dotenv()

    # Load the aea config
    with open(Path(AGENT_NAME, "aea-config.yaml"), "r", encoding="utf-8") as file:
        config = list(yaml.safe_load_all(file))

    # Search and replace all the secrets
    for path, var in PATH_TO_VAR.items():
        config = find_and_replace(config, path.split("/"), os.getenv(var))

    # Dump the updated config
    with open(Path(AGENT_NAME, "aea-config.yaml"), "w", encoding="utf-8") as file:
        yaml.dump_all(config, file, sort_keys=False)


if __name__ == "__main__":
    main()
