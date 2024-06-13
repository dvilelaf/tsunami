# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2024 David Vilela Freire
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

"""This package contains round behaviours of TsunamiAbciApp."""

import json
import random
import secrets
from abc import ABC
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Type, Union, cast

from aea.protocols.base import Message
from twitter_text import parse_tweet  # type: ignore

from packages.dvilela.connections.kv_store.connection import (
    PUBLIC_ID as KV_STORE_CONNECTION_PUBLIC_ID,
)
from packages.dvilela.connections.llama.connection import (
    PUBLIC_ID as LLAMA_CONNECTION_PUBLIC_ID,
)
from packages.dvilela.connections.suno.connection import (
    PUBLIC_ID as SUNO_CONNECTION_PUBLIC_ID,
)
from packages.dvilela.contracts.olas_registries.contract import OlasRegistriesContract
from packages.dvilela.contracts.olas_tokenomics.contract import OlasTokenomicsContract
from packages.dvilela.contracts.olas_treasury.contract import OlasTreasuryContract
from packages.dvilela.protocols.kv_store.dialogues import (
    KvStoreDialogue,
    KvStoreDialogues,
)
from packages.dvilela.protocols.kv_store.message import KvStoreMessage
from packages.dvilela.skills.tsunami_abci.dialogues import (
    TwitterDialogue,
    TwitterDialogues,
)
from packages.dvilela.skills.tsunami_abci.models import Params
from packages.dvilela.skills.tsunami_abci.prompts import (
    EVENT_USER_PROMPT_TEMPLATES,
    MUSIC_GENRES,
    OMEN_USER_PROMPT,
    PROPOSAL_CLOSED_USER_PROMPT,
    PROPOSAL_NEW_USER_PROMPT,
    REPO_USER_PROMPT_RELEASE,
    SUNO_PROMPT_TEMPLATE,
    SUNO_USER_PROMPT,
    SYSTEM_PROMPTS,
    SYSTEM_PROMPT_SUMMARIZER,
)
from packages.dvilela.skills.tsunami_abci.rounds import (
    GovernancePayload,
    GovernanceRound,
    PublishTweetsPayload,
    PublishTweetsRound,
    SunoPayload,
    SunoRound,
    SynchronizedData,
    TrackChainEventsPayload,
    TrackChainEventsRound,
    TrackOmenPayload,
    TrackOmenRound,
    TrackReposPayload,
    TrackReposRound,
    TsunamiAbciApp,
)
from packages.dvilela.skills.tsunami_abci.subgraph import (
    AGENT_QUERY,
    OMEN_XDAI_FPMMS_QUERY,
    OMEN_XDAI_TRADES_QUERY,
)
from packages.valory.connections.farcaster.connection import (
    PUBLIC_ID as FARCASTER_CONNECTION_PUBLIC_ID,
)
from packages.valory.connections.twitter.connection import (
    PUBLIC_ID as TWITTER_CONNECTION_PUBLIC_ID,
)
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.protocols.ledger_api import LedgerApiMessage
from packages.valory.protocols.srr.dialogues import SrrDialogue, SrrDialogues
from packages.valory.protocols.srr.message import SrrMessage
from packages.valory.protocols.twitter.message import TwitterMessage
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)
from packages.valory.skills.abstract_round_abci.models import Requests


MAX_TWEET_ATTEMPTS = 5
TWEET_ATTEMPTS_SUMMARIZE = 3
MAX_TWEET_CHARS = 280
HTTP_OK = 200
OLAS_REGISTRY_URL = "https://registry.olas.network"
GITHUB_REPO_LATEST_URL = "https://api.github.com/repos/{repo}/releases/latest"
DAY_IN_SECONDS = 3600 * 24
OMEN_API_ENDPOINT = "https://api.thegraph.com/subgraphs/name/protofire/omen-xdai"
OMEN_RUN_HOUR = 15
SUNO_RUN_HOUR = 10
SUNO_RUN_DAY = 4

TRACKED_REPOS = [
    "dvilelaf/tsunami",
    "valory-xyz/IEKit",
    "valory-xyz/governatooorr",
    "valory-xyz/mech",
    "valory-xyz/apy-oracle",
    "valory-xyz/price-oracle",
    "valory-xyz/open-aea",
    "valory-xyz/open-autonomy",
    "valory-xyz/autonomous-fund",
    "valory-xyz/hello-world",
    "valory-xyz/market-creator",
    "valory-xyz/agent-academy-2",
    "valory-xyz/agent-academy-1",
    "valory-xyz/generatooorr",
    "valory-xyz/olas-operate-app",
    "valory-xyz/trader",
    "valory-xyz/trader-quickstart",
]


def tweet_len(tweet: str) -> int:
    """Calculates a tweet length"""
    return parse_tweet(tweet).asdict()["weightedLength"]


def tweet_to_thread(tweet: str) -> Optional[List[str]]:
    """Create a thread from a long text"""

    def sentence_split(sentence: str, separator: str) -> List[str]:
        """Separates a sentence into parts"""
        parts = sentence.split(separator)
        for p in parts[:-1]:
            p += separator.rstrip()
        return [p.strip() for p in parts]

    def string_dot_split(text: str) -> List:
        """Separates a string into parts"""

        # We use the dot to separate. In order to avoid ellipsis from being removed,
        # we replace them with a special code
        ellipsis = "..."
        if ellipsis in text:
            parts = text.split(ellipsis)

            # Pre-append dot if the sentence starts with uppercase
            parts = [part if part[0].islower() else "." + part for part in parts]
            joined_parts = "<ellipsis>".join(parts)

            # Remove inital dot if it exists
            text = (
                joined_parts if not joined_parts.startswith(".") else joined_parts[1:]
            )
        # Recover ellipsis and strip
        sentences = [s.replace("<ellipsis>", "...").strip() for s in text.split(".")]

        # Remove empty sentences
        sentences = [s for s in sentences if s]
        return sentences

    sentences = string_dot_split(tweet)
    thread: List[str] = []

    # Keep iterating while there are sentences to process
    while sentences:
        # Get the next sentence
        next_sentence = sentences.pop(0)
        sentence_end = ". " if next_sentence[-1] not in ("?", "!", ".") else " "
        next_sentence += sentence_end

        # Does the sentence fit in a tweet?
        if tweet_len(next_sentence) > MAX_TWEET_CHARS:
            # First check if we can split this sentence (if it includes '? ' or '! ')
            if "? " in next_sentence:
                next_sentences = sentence_split(next_sentence, "? ")
                sentences = next_sentences + sentences
                continue

            if "! " in next_sentence:
                next_sentences = sentence_split(next_sentence, "! ")
                sentences = next_sentences + sentences
                continue

            # The sentece is too long to fit a tweet. A thread cannot be created
            return None

        # Add the first tweet
        if not thread:
            thread.append(next_sentence)
            continue

        # Add a new tweet if the previous one has grown too long
        if tweet_len(thread[-1] + next_sentence) > MAX_TWEET_CHARS:
            thread[-1] = thread[-1].strip()
            thread.append(next_sentence)
            continue

        # Extend the previous tweet
        thread[-1] += next_sentence

    thread[-1] = thread[-1].strip()
    return thread


class TsunamiBaseBehaviour(BaseBehaviour, ABC):  # pylint: disable=too-many-ancestors
    """Base behaviour for the tsunami_abci skill."""

    def __init__(self, **kwargs: Any):
        """Init"""
        super().__init__(**kwargs)

        self.tracked_events = {
            "ethereum": {
                "service_registry": {
                    "contract_id": str(OlasRegistriesContract.contract_id),
                    "contract_address": self.params.service_registry_address_ethereum,
                    "event_to_template": {
                        "CreateService": EVENT_USER_PROMPT_TEMPLATES["service_minted"],
                    },
                },
                "agent_registry": {
                    "contract_id": str(OlasRegistriesContract.contract_id),
                    "contract_address": self.params.agent_registry_address_ethereum,
                    "event_to_template": {
                        "CreateUnit": EVENT_USER_PROMPT_TEMPLATES["agent_minted"]
                    },
                },
                "component_registry": {
                    "contract_id": str(OlasRegistriesContract.contract_id),
                    "contract_address": self.params.component_registry_address_ethereum,
                    "event_to_template": {
                        "CreateUnit": EVENT_USER_PROMPT_TEMPLATES["component_minted"]
                    },
                },
                "tokenomics": {
                    "contract_id": str(OlasTokenomicsContract.contract_id),
                    "contract_address": self.params.tokenomics_address_ethereum,
                    "event_to_template": {
                        "EpochSettled": EVENT_USER_PROMPT_TEMPLATES["epoch_settled"]
                    },
                },
                "treasury": {
                    "contract_id": str(OlasTreasuryContract.contract_id),
                    "contract_address": self.params.treasury_address_ethereum,
                    "event_to_template": {
                        "DonateToServicesETH": EVENT_USER_PROMPT_TEMPLATES[
                            "donation_sent"
                        ]
                    },
                },
            },
            "gnosis": {
                "service_registry": {
                    "contract_id": str(OlasRegistriesContract.contract_id),
                    "contract_address": self.params.service_registry_address_gnosis,
                    "event_to_template": {
                        "CreateService": EVENT_USER_PROMPT_TEMPLATES["service_minted"],
                    },
                },
            },
        }

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)

    def publish_tweet(self, text: Union[str, List[str]]) -> Generator[None, None, Dict]:
        """Publish tweet"""

        self.context.logger.info(f"Creating tweet with text: {text}")
        response = yield from self._create_tweet(
            text=text, credentials=self.params.twitter_credentials
        )

        if response.performative == TwitterMessage.Performative.ERROR:
            self.context.logger.error(
                f"Writing tweet failed with following error message: {response}"
            )
            return {"success": False, "tweet_id": None}

        self.context.logger.info(f"Posted tweet with ID: {response.tweet_id}")
        return {"success": True, "tweet_id": response.tweet_id}

    def publish_cast(self, text: Union[str, List[str]]) -> Generator[None, None, Dict]:
        """Publish cast"""

        # Enforce text to be a list
        texts = text if isinstance(text, list) else [text]

        cast_id = None
        for text_ in texts:
            self.context.logger.info(f"Creating cast with text: {text_}")

            response = yield from self._create_cast(text=text_)
            response_data = json.loads(response.payload)

            if response.error:
                self.context.logger.error(
                    f"Writing cast failed with following error message: {response}"
                )
                # Interrupt the process. If this was a thread, it will be cut short.
                return {"success": False, "cast_id": cast_id}

            # Keep the first cast_id only
            if not cast_id:
                cast_id = response_data["cast_id"]
            self.context.logger.info(f"Posted cast with ID: {response_data['cast_id']}")

        return {"success": True, "cast_ids": cast_id}

    def publish_telegram(
        self, text: Union[str, List[str]]
    ) -> Generator[None, None, Dict]:
        """Publish telegram"""

        if isinstance(text, list):
            text = "\n\n".join(text)

        self.context.logger.info(f"Creating Telegram message with text:\n{text}")

        url = (
            f"https://api.telegram.org/bot{self.params.telegram_token}/sendMessage?"
            f"chat_id={self.params.telegram_chat_id}"
        )

        data = {"text": text}

        headers = {
            "Content-Type": "application/json",
        }

        # Send message
        response = yield from self.get_http_response(  # type: ignore
            method="POST", url=url, headers=headers, content=json.dumps(data).encode()
        )

        if response.status_code != HTTP_OK:  # type: ignore
            self.context.logger.error(
                f"Error sending Telegram message: {response}"  # type: ignore
            )
            return {"success": False}

        self.context.logger.info("Posted Telegram message")
        return {"success": True}

    def _create_tweet(
        self,
        text: Union[str, List[str]],
        credentials: dict,
    ) -> Generator[None, None, TwitterMessage]:
        """Send a request message from the skill context."""
        twitter_dialogues = cast(TwitterDialogues, self.context.twitter_dialogues)
        twitter_message, twitter_dialogue = twitter_dialogues.create(
            counterparty=str(TWITTER_CONNECTION_PUBLIC_ID),
            performative=TwitterMessage.Performative.CREATE_TWEET,
            text=json.dumps(
                {"text": text, "credentials": credentials}
            ),  # temp hack: we need to update the connection and protocol
        )
        twitter_message = cast(TwitterMessage, twitter_message)
        twitter_dialogue = cast(TwitterDialogue, twitter_dialogue)
        response = yield from self._do_twitter_request(
            twitter_message, twitter_dialogue
        )
        return response

    def _do_twitter_request(
        self,
        message: TwitterMessage,
        dialogue: TwitterDialogue,
        timeout: Optional[float] = None,
    ) -> Generator[None, None, TwitterMessage]:
        """Do a request and wait the response, asynchronously."""

        self.context.outbox.put_message(message=message)
        request_nonce = self._get_request_nonce_from_dialogue(dialogue)
        cast(Requests, self.context.requests).request_id_to_callback[
            request_nonce
        ] = self.get_callback_request()
        response = yield from self.wait_for_message(timeout=timeout)
        return response

    def _create_cast(
        self,
        text: str,
    ) -> Generator[None, None, SrrMessage]:
        """Send a request message from the skill context."""
        srr_dialogues = cast(SrrDialogues, self.context.srr_dialogues)
        srr_message, srr_dialogue = srr_dialogues.create(
            counterparty=str(FARCASTER_CONNECTION_PUBLIC_ID),
            performative=SrrMessage.Performative.REQUEST,
            payload=json.dumps({"method": "post_cast", "args": {"text": text}}),
        )
        srr_message = cast(SrrMessage, srr_message)
        srr_dialogue = cast(SrrDialogue, srr_dialogue)
        response = yield from self._do_connection_request(srr_message, srr_dialogue)  # type: ignore
        return response  # type: ignore

    def _call_llama(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Generator[None, None, SrrMessage]:
        """Send a request message from the skill context."""
        srr_dialogues = cast(SrrDialogues, self.context.srr_dialogues)
        srr_message, srr_dialogue = srr_dialogues.create(
            counterparty=str(LLAMA_CONNECTION_PUBLIC_ID),
            performative=SrrMessage.Performative.REQUEST,
            payload=json.dumps({"system": system_prompt, "user": user_prompt}),
        )
        srr_message = cast(SrrMessage, srr_message)
        srr_dialogue = cast(SrrDialogue, srr_dialogue)
        response = yield from self._do_connection_request(srr_message, srr_dialogue)  # type: ignore
        return response  # type: ignore

    def _call_suno(
        self,
        prompt: str,
    ) -> Generator[None, None, SrrMessage]:
        """Send a request message from the skill context."""
        srr_dialogues = cast(SrrDialogues, self.context.srr_dialogues)
        srr_message, srr_dialogue = srr_dialogues.create(
            counterparty=str(SUNO_CONNECTION_PUBLIC_ID),
            performative=SrrMessage.Performative.REQUEST,
            payload=json.dumps({"prompt": prompt}),
        )
        srr_message = cast(SrrMessage, srr_message)
        srr_dialogue = cast(SrrDialogue, srr_dialogue)
        response = yield from self._do_connection_request(srr_message, srr_dialogue)  # type: ignore
        return response  # type: ignore

    def _read_kv(
        self,
        keys: Tuple[str],
    ) -> Generator[None, None, Optional[Dict]]:
        """Send a request message from the skill context."""
        self.context.logger.info(f"Reading keys from db: {keys}")
        kv_store_dialogues = cast(KvStoreDialogues, self.context.kv_store_dialogues)
        kv_store_message, srr_dialogue = kv_store_dialogues.create(
            counterparty=str(KV_STORE_CONNECTION_PUBLIC_ID),
            performative=KvStoreMessage.Performative.READ_REQUEST,
            keys=keys,
        )
        kv_store_message = cast(KvStoreMessage, kv_store_message)
        kv_store_dialogue = cast(KvStoreDialogue, srr_dialogue)
        response = yield from self._do_connection_request(
            kv_store_message, kv_store_dialogue  # type: ignore
        )
        if response.performative != KvStoreMessage.Performative.READ_RESPONSE:
            return None

        data = {key: response.data.get(key, None) for key in keys}  # type: ignore

        return data

    def _write_kv(
        self,
        data: Dict[str, str],
    ) -> Generator[None, None, bool]:
        """Send a request message from the skill context."""
        kv_store_dialogues = cast(KvStoreDialogues, self.context.kv_store_dialogues)
        kv_store_message, srr_dialogue = kv_store_dialogues.create(
            counterparty=str(KV_STORE_CONNECTION_PUBLIC_ID),
            performative=KvStoreMessage.Performative.CREATE_OR_UPDATE_REQUEST,
            data=data,
        )
        kv_store_message = cast(KvStoreMessage, kv_store_message)
        kv_store_dialogue = cast(KvStoreDialogue, srr_dialogue)
        response = yield from self._do_connection_request(
            kv_store_message, kv_store_dialogue  # type: ignore
        )
        return response == KvStoreMessage.Performative.SUCCESS

    def _do_connection_request(
        self,
        message: Message,
        dialogue: Message,
        timeout: Optional[float] = None,
    ) -> Generator[None, None, Message]:
        """Do a request and wait the response, asynchronously."""

        self.context.outbox.put_message(message=message)
        request_nonce = self._get_request_nonce_from_dialogue(dialogue)  # type: ignore
        cast(Requests, self.context.requests).request_id_to_callback[
            request_nonce
        ] = self.get_callback_request()
        response = yield from self.wait_for_message(timeout=timeout)
        return response

    def build_thread(
        self, user_prompt: str, header: Optional[str] = None
    ) -> Generator[None, None, Optional[List[str]]]:
        """Build thread"""

        # Randomly select a personality
        # TODO: this only works for a single agent
        system_prompt_base = secrets.choice(SYSTEM_PROMPTS)  # nosec
        self.context.logger.info("Llama is building a tweet...")

        attempts = 0
        thread = None
        while attempts < MAX_TWEET_ATTEMPTS:
            system_prompt = system_prompt_base

            # Summarize if we've been retrying for some time
            if attempts >= TWEET_ATTEMPTS_SUMMARIZE:
                system_prompt += SYSTEM_PROMPT_SUMMARIZER

            # Call llama conection
            response = yield from self._call_llama(
                system_prompt=system_prompt, user_prompt=user_prompt
            )

            response_json = json.loads(response.payload)

            if "error" in response_json:
                self.context.logger.error(response_json["error"])
                continue

            tweet_attempt = response_json["response"]

            # Add header
            if header:
                tweet_attempt = header + tweet_attempt

            # Add Contribute's hashtag
            if "#OlasNetwork" not in tweet_attempt:
                tweet_attempt += " #OlasNetwork"

            # Create a single-tweet thread
            if tweet_len(tweet_attempt) < MAX_TWEET_CHARS:
                self.context.logger.info("Tweet is OK!")
                thread = [tweet_attempt]
                break

            self.context.logger.error(
                f"Tweet is too long [{tweet_len}]: {tweet_attempt}"
            )

            # Create a multi-tweet thread instead
            thread_attempt = tweet_to_thread(tweet_attempt)

            if thread_attempt:
                self.context.logger.info(f"Thread is OK!:\n{thread_attempt}")
                thread = thread_attempt
                break

            self.context.logger.error(f"Thread could not be built: {tweet_attempt}")

            attempts += 1

        if attempts >= MAX_TWEET_ATTEMPTS:
            self.context.logger.error("Too many attempts. Aborting tweet.")

        return thread


class TrackChainEventsBehaviour(
    TsunamiBaseBehaviour
):  # pylint: disable=too-many-ancestors
    """TrackChainEventsBehaviour"""

    matching_round: Type[AbstractRound] = TrackChainEventsRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            tweets = self.synchronized_data.tweets
            if self.params.event_tracking_enabled:
                tweets += yield from self.build_tweets()
            payload = TrackChainEventsPayload(
                sender=self.context.agent_address, tweets=json.dumps(tweets)
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def build_tweets(  # pylint: disable=too-many-locals,too-many-statements
        self,
    ) -> Generator[None, None, List[str]]:  # pylint: disable=too-many-locals
        """Build tweets"""
        tweets = self.synchronized_data.tweets

        # If there are no tweets in the synchronized_data, this might be the first period.
        # We need to check the db
        if not tweets:
            response = yield from self._read_kv(keys=("tweets",))

            if response is None:
                self.context.logger.error(
                    "Error reading from the database. Tweets won't be loaded."
                )

            elif response["tweets"]:
                tweets = json.loads(response["tweets"])
                self.context.logger.info(f"Loaded tweets from db: {tweets}")

        # Chain loop
        for chain_id, contracts_data in self.tracked_events.items():
            # Default from_block
            from_block = getattr(self.params, f"initial_block_{chain_id}")

            # Get from block
            db_data = yield from self._read_kv(keys=(f"from_block_{chain_id}",))

            if db_data is None:
                self.context.logger.error(
                    "Error reading from the database. from_block won't be loaded."
                )
            else:
                from_block = int(db_data.get(f"from_block_{chain_id}") or from_block)

            # Get to block
            ledger_api_response = yield from self.get_ledger_api_response(
                performative=LedgerApiMessage.Performative.GET_STATE,
                ledger_callable="get_block_number",
                chain_id=chain_id,
            )

            if ledger_api_response.performative != LedgerApiMessage.Performative.STATE:
                self.context.logger.error(
                    f"Error while retieving latest block number: {ledger_api_response}\n. Skipping chain {chain_id}..."
                )
                continue

            latest_block = cast(
                int, ledger_api_response.state.body["get_block_number_result"]
            )

            self.context.logger.info(
                f"chaind_id: {chain_id} from_block: {from_block} to_block: {latest_block}"
            )

            # Contract loop
            for contract_name, contract_data in contracts_data.items():
                contract_id = contract_data["contract_id"]
                contract_address = contract_data["contract_address"]
                unit_type = "service" if contract_name == "service_registry" else "unit"
                component_type = contract_name.split("_", maxsplit=1)[
                    0
                ]  # service, agent or component

                # Event type loop
                for event_name, event_template in contract_data[
                    "event_to_template"
                ].items():
                    self.context.logger.info(
                        f"Getting {event_name} events from contract {contract_name} on {chain_id} [{contract_address}]"
                    )

                    # Get events
                    events, _ = yield from self.get_events(
                        contract_id,
                        chain_id,
                        contract_address,
                        event_name,
                        from_block,
                        latest_block,
                    )

                    if events is None:
                        self.context.logger.error(
                            f"Error while retrieving events: {ledger_api_response}\n. Skipping event type {chain_id}:{contract_name}:{event_name}..."
                        )
                        continue

                    # Event loop
                    for event in events:
                        self.context.logger.info(f"Processing event {event}")

                        unit_id = getattr(event.args, f"{unit_type}Id")

                        kwargs = {
                            "unit_id": unit_id,
                            "chain_name": chain_id,
                        }

                        user_prompt = event_template.format(**kwargs)

                        # Get token URI
                        uri = yield from self.get_token_uri(
                            chain_id, contract_id, contract_address, unit_id
                        )

                        if uri is None:
                            self.context.logger.error(
                                f"Error while retieving uri: {ledger_api_response}\n. Skipping event {chain_id}:{contract_name}:{event_name}:{event}..."
                            )
                            continue

                        # Get unit data
                        self.context.logger.info("Getting token data...")
                        response = yield from self.get_http_response(  # type: ignore
                            method="GET", url=uri
                        )

                        if response.status_code != HTTP_OK:  # type: ignore
                            self.context.logger.error(
                                f"Error while download token data: {ledger_api_response}\n. Skipping event {chain_id}:{contract_name}:{event_name}:{event}...\n{response}"  # type: ignore
                            )
                            continue

                        response_json = json.loads(response.body)  # type: ignore
                        self.context.logger.info(f"Got token data: {response_json}")

                        unit_name = response_json["name"]
                        unit_description = response_json["description"]
                        user_prompt += f" The {unit_type}'s name is {unit_name}. Its description is: {unit_description}'"
                        unit_url = f"{OLAS_REGISTRY_URL}/{chain_id}/{component_type}s/{unit_id}"

                        thread = yield from self.build_thread(user_prompt)

                        if thread is None:
                            self.context.logger.error(
                                "Error while building thread. Skipping..."
                            )
                            continue

                        # Add a link to the unit
                        thread.append(unit_url)

                        tweets.append(
                            {
                                "text": thread,
                                "twitter_published": False,
                                "farcaster_published": False,
                                "telegram_published": False,
                                "timestamp": datetime.now().strftime(
                                    "%Y-%m-%dT%H:%M:%SZ"
                                ),
                            }
                        )

            # Write from block
            yield from self._write_kv({f"from_block_{chain_id}": str(latest_block)})

        # Save tweets to the db
        yield from self._write_kv({"tweets": json.dumps(tweets)})

        self.context.logger.info(f"Prepared tweets: {tweets}")

        return tweets

    def get_events(  # pylint: disable=too-many-arguments
        self,
        contract_id: str,
        chain_id: str,
        contract_address: str,
        event_name: str,
        from_block: int,
        to_block: int,
    ) -> Generator[None, None, Tuple[Optional[List], Optional[int]]]:
        """Get registries events"""

        self.context.logger.info(
            f"Retrieving {event_name} events later than block {from_block} on contract {chain_id}::{contract_id}::{contract_address}"
        )

        contract_api_msg = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=contract_address,
            contract_id=contract_id,
            contract_callable="get_events",
            event_name=event_name,
            from_block=from_block,
            to_block=to_block,
            chain_name=chain_id,  # chain_id is intercepted so we need to duplicate this to reach the contract
            chain_id=chain_id,
        )

        if contract_api_msg.performative != ContractApiMessage.Performative.STATE:
            self.context.logger.info(
                f"Error retrieving the events [{contract_api_msg}]"
            )
            return None, None

        events = cast(dict, contract_api_msg.state.body)["events"]
        latest_block = cast(dict, contract_api_msg.state.body)["latest_block"]

        self.context.logger.info(
            f"Got {len(events)} {event_name} events on {chain_id} from block {from_block} until block {latest_block}"
        )

        return events, latest_block

    def get_token_uri(
        self, chain_id: str, contract_id: str, contract_address: str, unit_id: str
    ) -> Generator[None, None, Optional[str]]:
        """Get registries events"""

        self.context.logger.info(
            f"Retrieving uri for unit_id {unit_id} on contract {chain_id}::{contract_id}::{contract_address}"
        )

        contract_api_msg = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=contract_address,
            contract_id=contract_id,
            contract_callable="get_token_uri",
            unit_id=unit_id,
            chain_id=chain_id,
        )

        if contract_api_msg.performative != ContractApiMessage.Performative.STATE:
            self.context.logger.info(
                f"Error retrieving the events [{contract_api_msg.performative}]"
            )
            return None

        uri = cast(dict, contract_api_msg.state.body)["result"]

        self.context.logger.info(f"Got uri: {uri}")

        return uri


class TrackReposBehaviour(TsunamiBaseBehaviour):  # pylint: disable=too-many-ancestors
    """TrackReposBehaviour"""

    matching_round: Type[AbstractRound] = TrackReposRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            tweets = self.synchronized_data.tweets

            if self.params.repo_tracking_enabled:
                repo_tweets = yield from self.get_repo_tweets()
                tweets += repo_tweets

                # Save tweets to the db
                yield from self._write_kv({"tweets": json.dumps(tweets)})

            payload = TrackReposPayload(
                sender=self.context.agent_address, tweets=json.dumps(tweets)
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def get_repo_tweets(self) -> Generator[None, None, List]:
        """Get tweets about new repo releases"""

        tweets: List[Dict] = []

        response = yield from self._read_kv(keys=("repos",))

        if response is None:
            self.context.logger.error("Error reading repos from the database.")
            return tweets

        repos = json.loads(response["repos"]) if response["repos"] else {}

        self.context.logger.info(f"Loaded repos from db: {repos}")

        for repo in TRACKED_REPOS:
            latest_known_version = repos.get(repo, None)
            self.context.logger.info(f"Getting repo {repo}...")
            response = yield from self.get_http_response(  # type: ignore
                method="GET", url=GITHUB_REPO_LATEST_URL.replace("{repo}", repo)
            )

            if response.status_code != HTTP_OK:  # type: ignore
                self.context.logger.error(
                    f"Error while getting the repo {repo}: {response}"  # type: ignore
                )
                continue

            response_json = json.loads(response.body)  # type: ignore
            version = response_json["tag_name"]
            published_at = response_json["published_at"]

            if latest_known_version and version == latest_known_version:
                self.context.logger.info("Repo has not been updated yet")
                continue

            if (
                datetime.now() - datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
            ).total_seconds() > DAY_IN_SECONDS:
                self.context.logger.info(
                    "Repo has not been updated during the last 24 hours"
                )
                continue

            self.context.logger.info(
                f"A new version of {repo} has been released: {version}"
            )

            user_prompt = REPO_USER_PROMPT_RELEASE.format(version=version, repo=repo)
            thread = yield from self.build_thread(user_prompt)

            if thread is None:
                self.context.logger.error("Error while building thread. Skipping...")
                continue

            repos[repo] = version
            thread.append(response_json["html_url"])
            tweets.append(
                {
                    "text": thread,
                    "twitter_published": False,
                    "farcaster_published": False,
                    "telegram_published": False,
                    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            )

        # Save repos to the db
        yield from self._write_kv({"repos": json.dumps(repos)})

        return tweets


class TrackOmenBehaviour(TsunamiBaseBehaviour):  # pylint: disable=too-many-ancestors
    """TrackOmenBehaviour"""

    matching_round: Type[AbstractRound] = TrackOmenRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            tweets = self.synchronized_data.tweets
            if self.params.omen_tracking_enabled:
                omen_tweets = yield from self.get_omen_tweets()
                tweets += omen_tweets

                # Save tweets to the db
                yield from self._write_kv({"tweets": json.dumps(tweets)})

            payload = TrackOmenPayload(
                sender=self.context.agent_address, tweets=json.dumps(tweets)
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def get_omen_tweets(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-statements
        self,
    ) -> Generator[None, None, List]:
        """Get tweets about Omen markets"""

        tweets: List[Dict] = []

        response = yield from self._read_kv(keys=("omen_last_run_date",))

        if response is None:
            self.context.logger.error(
                "Error reading omen_last_run_date from the database."
            )
            return tweets

        omen_last_run_date = response["omen_last_run_date"]
        omen_last_run_date = (
            datetime.strptime(omen_last_run_date, "%Y-%m-%d")
            if omen_last_run_date
            else None
        )
        self.context.logger.info(
            f"Loaded omen_last_run_date from db: {omen_last_run_date}"
        )

        # Check run time
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if omen_last_run_date and today <= omen_last_run_date:
            self.context.logger.info("Omen task already ran today")
            return tweets

        if now.hour < OMEN_RUN_HOUR:
            self.context.logger.info(
                f"Not time to run Omen yet [{now.hour} < {OMEN_RUN_HOUR}]"
            )
            return tweets

        # We are retrieving data for the last 24 hours
        creation_timestamp_gt = str(int((now - timedelta(days=1)).timestamp()))

        headers = {
            "Accept": "application/json, multipart/mixed",
            "Content-Type": "application/json",
        }

        # Markets
        self.context.logger.info("Getting Omen markets...")

        query = OMEN_XDAI_FPMMS_QUERY.substitute(
            creationTimestamp_gt=creation_timestamp_gt,
        )

        content_json = {
            "query": query,
            "variables": None,
            "extensions": {"headers": None},
        }

        response = yield from self.get_http_response(  # type: ignore
            method="POST",
            url=OMEN_API_ENDPOINT,
            content=json.dumps(content_json).encode(),
            headers=headers,
        )

        if response.status_code != HTTP_OK:  # type: ignore
            self.context.logger.error(
                f"Error while getting the markets: {response}"  # type: ignore
            )
            return tweets

        markets_json = json.loads(response.body)  # type: ignore
        markets = markets_json.get("data", {}).get("fixedProductMarketMakers", [])

        # Trades
        self.context.logger.info("Getting Omen trades...")

        query = OMEN_XDAI_TRADES_QUERY.substitute(
            creationTimestamp_gt=creation_timestamp_gt,
        )

        content_json = {
            "query": query,
            "variables": None,
            "extensions": {"headers": None},
        }

        response = yield from self.get_http_response(  # type: ignore
            method="POST",
            url=OMEN_API_ENDPOINT,
            content=json.dumps(content_json).encode(),
            headers=headers,
        )

        if response.status_code != HTTP_OK:  # type: ignore
            self.context.logger.error(
                f"Error while getting the trades: {response}"  # type: ignore
            )
            return tweets

        trades_json = json.loads(response.body)  # type: ignore
        trades = trades_json.get("data", {}).get("fpmmTrades", [])

        # Calculate data
        n_markets = len(markets)
        n_trades = len(trades)
        usd_amount = sum([float(t["collateralAmountUSD"]) for t in trades])
        traders = [t["creator"]["id"] for t in trades]
        trader_counter = Counter(traders)
        n_traders = len(trader_counter)
        biggest_trader_address, biggest_trader_trades = trader_counter.most_common(1)[0]

        # Build thread
        user_prompt = OMEN_USER_PROMPT.format(
            n_markets=n_markets,
            n_agents=n_traders,
            n_trades=n_trades,
            usd_amount=int(usd_amount),  # to avoid numeric confusion on the LLM
            biggest_trader_address=biggest_trader_address,
            biggest_trader_trades=biggest_trader_trades,
        )
        thread = yield from self.build_thread(user_prompt)

        if thread is None:
            self.context.logger.error("Error while building thread. Skipping...")
            return tweets

        # Add random opened markets
        if markets:
            header = "Here's some questions the Market Creator has opened today:"
            thread.append(header)

            market_questions = [m["question"]["title"] for m in markets]

            # Get random sample of markets where its questions fit in a tweet
            some_markets = random.sample(
                list(filter(lambda m: len(m) < 250, market_questions)),
                min(3, n_markets),
            )
            some_questions = ["☴ " + m for m in some_markets]
            thread += some_questions

        # Add random traded questions
        header = "Here's some questions Olas agents have been trading on:"
        thread.append(header)

        # Get random sample of trades where its questions fit in a tweet
        traded_questions = list({t["title"] for t in trades})
        filtered_questions = list(filter(lambda t: len(t) < 250, traded_questions))
        some_questions = random.sample(
            filtered_questions, min(3, len(filtered_questions))
        )
        some_questions = ["☴ " + q for q in some_questions]
        thread += some_questions

        tweets.append(
            {
                "text": thread,
                "twitter_published": False,
                "farcaster_published": False,
                "telegram_published": False,
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

        # Save run time to the db
        yield from self._write_kv({"omen_last_run_date": today.strftime("%Y-%m-%d")})

        return tweets


class SunoBehaviour(TsunamiBaseBehaviour):  # pylint: disable=too-many-ancestors
    """SunoBehaviour"""

    matching_round: Type[AbstractRound] = SunoRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            tweets = self.synchronized_data.tweets
            if self.params.suno_enabled:
                suno_tweets = yield from self.get_suno_tweets()
                tweets += suno_tweets

                # Save tweets to the db
                yield from self._write_kv({"tweets": json.dumps(tweets)})

            payload = SunoPayload(
                sender=self.context.agent_address, tweets=json.dumps(tweets)
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def get_suno_tweets(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-statements
        self,
    ) -> Generator[None, None, List]:
        """Get tweets with songs from Suno"""

        tweets: List[Dict] = []

        response = yield from self._read_kv(keys=("suno_last_run_date",))

        if response is None:
            self.context.logger.error(
                "Error reading suno_last_run_date from the database."
            )
            return tweets

        suno_last_run_date = response["suno_last_run_date"]
        suno_last_run_date = (
            datetime.strptime(suno_last_run_date, "%Y-%m-%d")
            if suno_last_run_date
            else None
        )
        self.context.logger.info(
            f"Loaded suno_last_run_date from db: {suno_last_run_date}"
        )

        # Check run time
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if now.weekday() != SUNO_RUN_DAY:
            self.context.logger.info(
                f"Suno task does not run today: {now.weekday()} != {SUNO_RUN_DAY}"
            )
            return tweets

        if suno_last_run_date and today <= suno_last_run_date:
            self.context.logger.info("Suno task already ran this week")
            return tweets

        if now.hour < SUNO_RUN_HOUR:
            self.context.logger.info(
                f"Not time to run Suno yet [{now.hour} < {SUNO_RUN_HOUR}]"
            )
            return tweets

        SUBGRAPH_URL = "https://subgraph.autonolas.tech/subgraphs/name/autonolas"

        headers = {
            "Content-Type": "application/json",
        }

        data = {
            "query": AGENT_QUERY,
            "variables": {
                "package_type": "agent",
            },
        }

        # Get all existing agents from the subgraph
        self.context.logger.info("Getting agents from subgraph")
        response = yield from self.get_http_response(  # type: ignore
            method="POST",
            url=SUBGRAPH_URL,
            headers=headers,
            content=json.dumps(data).encode(),
        )

        if response.status_code != HTTP_OK:  # type: ignore
            self.context.logger.error(
                f"Error getting agents from subgraph: {response}"  # type: ignore
            )
            return tweets

        response_json = json.loads(response.body)["data"]  # type: ignore
        agents = [u for u in response_json["units"] if u["packageType"] == "agent"]
        agents = sorted(agents, key=lambda i: int(i["tokenId"]))

        n_agents = len(agents)
        self.context.logger.info(f"Got {n_agents} agents")

        # Filter out agents from past songs
        response = yield from self._read_kv(keys=("previous_suno_agents",))

        if response is None:
            self.context.logger.error(
                "Error reading previous_suno_agents from the database."
            )
            return tweets

        previous_suno_agents = response["previous_suno_agents"]
        self.context.logger.info(
            f"Loaded previous_suno_agents from db: {previous_suno_agents}"
        )

        previous_suno_agents = json.loads(previous_suno_agents or "[]")
        agents = [a for a in agents if int(a["tokenId"]) not in previous_suno_agents]

        # Select a random agent and genre
        agent = secrets.choice(agents)  # nosec
        agent_name = agent["publicId"].split("/")[-1]
        agent_description = agent["description"]
        genres = random.sample(MUSIC_GENRES, 2)
        prompt = SUNO_PROMPT_TEMPLATE.format(
            genre=", ".join(genres),
            agent_name=agent_name,
            agent_description=agent_description,
        )
        self.context.logger.info("Suno prompt is: {prompt}")
        previous_suno_agents.append(int(agent["tokenId"]))

        # Call Suno conection
        suno_response = yield from self._call_suno(prompt=prompt)

        response_json = json.loads(suno_response.payload)

        if "error" in response_json:
            self.context.logger.error(response_json["error"])
            return tweets

        song_urls = response_json["response"]

        if not song_urls:
            self.context.logger.error("Error while creating the songs")
            return tweets

        # Create a thread
        thread = yield from self.build_thread(
            SUNO_USER_PROMPT.format(genre=", ".join(genres), agent_name=agent_name)
        )

        if thread is None:
            self.context.logger.error("Error while building thread. Skipping...")
            return tweets

        # Add a link to the unit
        thread.append(song_urls[0])
        self.context.logger.info(f"Created Suno thread: {thread}")

        tweets.append(
            {
                "text": thread,
                "twitter_published": False,
                "farcaster_published": False,
                "telegram_published": False,
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

        # Save run time to the db
        yield from self._write_kv({"suno_last_run_date": today.strftime("%Y-%m-%d")})

        # Save agents to the db
        yield from self._write_kv(
            {"previous_suno_agents": json.dumps(previous_suno_agents, sort_keys=True)}
        )

        return tweets


class GovernanceBehaviour(TsunamiBaseBehaviour):  # pylint: disable=too-many-ancestors
    """GovernanceBehaviour"""

    matching_round: Type[AbstractRound] = GovernanceRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            tweets = self.synchronized_data.tweets
            if self.params.governance_enabled:
                suno_tweets = yield from self.get_governance_tweets()
                tweets += suno_tweets

                # Save tweets to the db
                yield from self._write_kv({"tweets": json.dumps(tweets)})

            payload = GovernancePayload(
                sender=self.context.agent_address, tweets=json.dumps(tweets)
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def get_governance_tweets(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-statements
        self,
    ) -> Generator[None, None, List]:
        """Get tweets with governance proposals"""

        tweets: List[Dict] = []

        # Load proposals from the db
        response = yield from self._read_kv(keys=("governance_proposals",))

        if response is None:
            self.context.logger.error(
                "Error reading governance_proposals from the database."
            )
            return tweets

        governance_proposals = json.loads(response["governance_proposals"] or "{}")

        self.context.logger.info(
            f"Loaded governance_proposals from db: {governance_proposals}"
        )

        # Get active proposals from Boardroom
        self.context.logger.info("Getting active proposals from Boardroom")

        url = "https://api.boardroom.info/v1/protocols/autonolas/proposals"
        headers = {
            "Accept": "application/json",
        }
        parameters = {"key": self.params.boardroom_api_key, "status": "active"}

        response = yield from self.get_http_response(  # type: ignore
            method="GET", url=url, headers=headers, parameters=parameters
        )

        if response.status_code != HTTP_OK:  # type: ignore
            self.context.logger.error(
                f"Error getting active proposals from Boardroom: {response}"  # type: ignore
            )
            return tweets

        active_proposals = json.loads(response.body)["data"]  # type: ignore

        # Filter some info out
        KEEP_FIELDS = ("title", "adapter", "externalUrl")
        active_proposals = {
            ap["refId"]: {k: v for k, v in ap.items() if k in KEEP_FIELDS}
            for ap in active_proposals
        }

        # Create new and closed proposals
        new_proposals = {
            k: v for k, v in active_proposals.items() if k not in governance_proposals
        }
        closed_proposals = {
            k: v for k, v in governance_proposals.items() if k not in active_proposals
        }
        self.context.logger.info(
            f"Got {len(new_proposals)} new proposals and {len(closed_proposals)} closed proposals"
        )

        # Prepare tweets (new proposals)
        for proposal_id, proposal in new_proposals.items():
            user_prompt = PROPOSAL_NEW_USER_PROMPT.format(
                proposal_title=proposal["title"]
            )
            thread_header = "🚨 Governance alert: new proposal 🚨\n\n"
            thread = yield from self.build_thread(user_prompt, header=thread_header)

            if thread is None:
                self.context.logger.error("Error while building thread. Skipping...")
                continue

            proposal_url = (
                f"https://boardroom.io/{proposal['protocol']}/proposal/{proposal_id}"
                if proposal["adapter"] == "onchain"
                else proposal["externalUrl"]
            )
            thread.append(proposal_url)

            tweets.append(
                {
                    "text": thread,
                    "twitter_published": False,
                    "farcaster_published": False,
                    "telegram_published": False,
                    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            )

            # Add proposal to the db
            governance_proposals[proposal_id] = proposal

        # Prepare tweets (closed proposals)
        for proposal_id, proposal in closed_proposals.items():
            # Get the vote result
            self.context.logger.info(f"Getting proposal from Boardroom: {proposal_id}")

            url = f"https://api.boardroom.info/v1/proposals/{proposal_id}"
            headers = {
                "Accept": "application/json",
            }
            parameters = {
                "key": self.params.boardroom_api_key,
            }

            response = yield from self.get_http_response(  # type: ignore
                method="GET", url=url, headers=headers, parameters=parameters
            )

            if response.status_code != HTTP_OK:  # type: ignore
                self.context.logger.error(
                    f"Error getting proposal from Boardroom: {response}"  # type: ignore
                )
                continue

            proposal = json.loads(response.body)["data"]  # type: ignore
            vote_result = proposal["choices"][proposal["results"][0]["choice"]]

            self.context.logger.error(f"Vote result was: {vote_result}")  # type: ignore

            user_prompt = PROPOSAL_CLOSED_USER_PROMPT.format(
                proposal_title=proposal["title"], vote_result=vote_result
            )
            thread_header = "🚨 Governance alert: closed proposal 🚨\n\n"
            thread = yield from self.build_thread(user_prompt, header=thread_header)

            if thread is None:
                self.context.logger.error("Error while building thread. Skipping...")
                continue

            proposal_url = (
                f"https://boardroom.io/{proposal['protocol']}/proposal/{proposal_id}"
                if proposal["adapter"] == "onchain"
                else proposal["externalUrl"]
            )
            thread.append(proposal_url)

            tweets.append(
                {
                    "text": thread,
                    "twitter_published": False,
                    "farcaster_published": False,
                    "telegram_published": False,
                    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            )

            # Remove proposal from the db
            del governance_proposals[proposal_id]

        # Save proposals to the db
        yield from self._write_kv(
            {"governance_proposals": json.dumps(governance_proposals, sort_keys=True)}
        )

        return tweets


class PublishTweetsBehaviour(
    TsunamiBaseBehaviour
):  # pylint: disable=too-many-ancestors
    """PublishTweetsBehaviour"""

    matching_round: Type[AbstractRound] = PublishTweetsRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            tweets = self.synchronized_data.tweets

            # Publish tweets
            for tweet in tweets:
                if self.params.publish_twitter and not tweet["twitter_published"]:
                    response = yield from self.publish_tweet(tweet["text"])
                    tweet["twitter_published"] = response["success"]

            # Publish casts
            sleep_between_casts = len(tweets) > 10
            for tweet in tweets:
                if self.params.publish_farcaster and not tweet["farcaster_published"]:
                    response = yield from self.publish_cast(tweet["text"])
                    tweet["farcaster_published"] = response["success"]

                # Avoid being rate limited (10 casts/60 seconds)
                if sleep_between_casts:
                    yield from self.sleep(6)

            # Publish telegram
            for tweet in tweets:
                if self.params.publish_telegram and not tweet["telegram_published"]:
                    response = yield from self.publish_telegram(tweet["text"])
                    tweet["telegram_published"] = response["success"]

            # Remove published tweets
            tweets = [
                t
                for t in tweets
                if not t["twitter_published"]
                or not t["farcaster_published"]
                or not t["telegram_published"]
            ]

            # Save tweets to the db
            yield from self._write_kv({"tweets": json.dumps(tweets)})

            payload = PublishTweetsPayload(
                sender=self.context.agent_address, tweets=json.dumps(tweets)
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class TsunamiRoundBehaviour(AbstractRoundBehaviour):
    """TsunamiRoundBehaviour"""

    initial_behaviour_cls = TrackChainEventsBehaviour
    abci_app_cls = TsunamiAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [  # type: ignore
        TrackChainEventsBehaviour,
        TrackReposBehaviour,
        TrackOmenBehaviour,
        SunoBehaviour,
        GovernanceBehaviour,
        PublishTweetsBehaviour,
    ]
