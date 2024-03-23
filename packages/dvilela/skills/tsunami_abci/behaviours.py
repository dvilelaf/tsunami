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
from abc import ABC
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Type, cast

from aea.protocols.base import Message
from twitter_text import parse_tweet  # type: ignore

from packages.dvilela.connections.kv_store.connection import (
    PUBLIC_ID as KV_STORE_CONNECTION_PUBLIC_ID,
)
from packages.dvilela.connections.llama.connection import (
    PUBLIC_ID as LLAMA_CONNECTION_PUBLIC_ID,
)
from packages.dvilela.contracts.olas_registries.contract import OlasRegistriesContract
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
    SYSTEM_PROMPTS,
    SYSTEM_PROMPT_SUMMARIZER,
    USER_PROMPT_TEMPLATES,
)
from packages.dvilela.skills.tsunami_abci.rounds import (
    PrepareTweetsPayload,
    PrepareTweetsRound,
    PublishTweetsPayload,
    PublishTweetsRound,
    SynchronizedData,
    TsunamiAbciApp,
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


class TsunamiBaseBehaviour(BaseBehaviour, ABC):  # pylint: disable=too-many-ancestors
    """Base behaviour for the tsunami_abci skill."""

    def __init__(self, **kwargs: Any):
        """Init"""
        super().__init__(**kwargs)

        self.tracked_events = {
            "ethereum": {
                "service_registry": {
                    "contract_address": self.params.service_registry_address_ethereum,
                    "event_to_template": {
                        "CreateService": USER_PROMPT_TEMPLATES["service_minted"],
                    },
                },
                "agent_registry": {
                    "contract_address": self.params.agent_registry_address_ethereum,
                    "event_to_template": {
                        "CreateUnit": USER_PROMPT_TEMPLATES["agent_minted"]
                    },
                },
                "component_registry": {
                    "contract_address": self.params.component_registry_address_ethereum,
                    "event_to_template": {
                        "CreateUnit": USER_PROMPT_TEMPLATES["component_minted"]
                    },
                },
            },
            "gnosis": {
                "service_registry": {
                    "contract_address": self.params.service_registry_address_gnosis,
                    "event_to_template": {
                        "CreateService": USER_PROMPT_TEMPLATES["service_minted"],
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

    def publish_tweet(self, text: str) -> Generator[None, None, Dict]:
        """Publish tweet"""

        self.context.logger.info(f"Creating tweet with text: {text}")
        response = yield from self._create_tweet(
            text=text, credentials=self.params.twitter_credentials
        )

        if response.performative == TwitterMessage.Performative.ERROR:
            self.context.logger.error(
                f"Writing tweet failed with following error message: {response.message}"
            )
            return {"success": False, "tweet_id": None}

        self.context.logger.info(f"Posted tweet with ID: {response.tweet_id}")
        return {"success": True, "tweet_id": response.tweet_id}

    def publish_cast(self, text: str) -> Generator[None, None, Dict]:
        """Publish cast"""

        self.context.logger.info(f"Creating cast with text: {text}")

        response = yield from self._create_cast(text=text)
        response_data = json.loads(response.payload)

        if response.error:
            self.context.logger.error(
                f"Writing cast failed with following error message: {response.payload}"
            )
            return {"success": False, "cast_id": None}

        self.context.logger.info(f"Posted cast with ID: {response_data['cast_id']}")
        return {"success": True, "cast_id": response_data["cast_id"]}

    def _create_tweet(
        self,
        text: str,
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


class PrepareTweetsBehaviour(
    TsunamiBaseBehaviour
):  # pylint: disable=too-many-ancestors
    """PrepareTweetsBehaviour"""

    matching_round: Type[AbstractRound] = PrepareTweetsRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            tweets = yield from self.build_tweets()
            payload = PrepareTweetsPayload(
                sender=self.context.agent_address, tweets=json.dumps(tweets)
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def build_tweets(  # pylint: disable=too-many-locals
        self,
    ) -> Generator[None, None, List[str]]:  # pylint: disable=too-many-locals
        """Build tweets"""
        tweets = self.synchronized_data.tweets

        # If there are no tweets in the synchronized_data, this might be the first period.
        # We need to check the db
        if not tweets:
            response = yield from self._read_kv(keys=("tweets",))
            if response["tweets"]:
                tweets = json.loads(response["tweets"])
                self.context.logger.info(f"Loaded tweets from db: {tweets}")

        contract_id = str(OlasRegistriesContract.contract_id)

        # Chain loop
        for chain_id, contracts_data in self.tracked_events.items():
            # Get from block
            db_data = yield from self._read_kv(keys=(f"from_block_{chain_id}",))
            from_block = int(
                db_data.get(f"from_block_{chain_id}")
                or getattr(self.params, f"initial_block_{chain_id}")
            )

            # Get to block
            ledger_api_response = yield from self.get_ledger_api_response(
                performative=LedgerApiMessage.Performative.GET_STATE,
                ledger_callable="get_block_number",
                chain_id=chain_id,
            )

            latest_block = ledger_api_response.state.body["get_block_number_result"]

            self.context.logger.info(
                f"chaind_id: {chain_id} from_block: {from_block} to_block: {latest_block}"
            )

            # Contract loop
            for contract_name, contract_data in contracts_data.items():
                contract_address = contract_data["contract_address"]
                unit_type = "service" if contract_name == "service_registry" else "unit"

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

                        # Get unit data
                        self.context.logger.info("Getting token data...")
                        response = yield from self.get_http_response(
                            method="GET", url=uri
                        )

                        if response.status_code != HTTP_OK:
                            self.context.logger.info(
                                f"Failed to download token data: {response.status_code}"
                            )
                            continue  # TODO: retries

                        response_json = json.loads(response.body)
                        self.context.logger.info(f"Got token data: {response_json}")

                        unit_name = response_json["name"]
                        unit_description = response_json["description"]
                        user_prompt += f" The {unit_type}'s name is {unit_name}. Its description is: {unit_description}'"

                        tweet = yield from self.build_tweet(user_prompt)

                        if tweet:
                            tweets.append(
                                {
                                    "text": tweet,
                                    "twitter_published": False,
                                    "farcaster_published": False,
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

    def build_tweet(self, user_prompt: str) -> Generator[None, None, Optional[str]]:
        """Build tweet"""

        # Randomly select a personality
        # TODO: this only works for a single agent
        system_prompt_base = random.choice(SYSTEM_PROMPTS)  # nosec
        self.context.logger.info("Llama is building a tweet...")

        attempts = 0
        tweet = None
        while attempts < MAX_TWEET_ATTEMPTS:
            system_prompt = system_prompt_base

            # Summarize if we've been retrying for some time
            if attempts >= TWEET_ATTEMPTS_SUMMARIZE:
                system_prompt += SYSTEM_PROMPT_SUMMARIZER

            # Call llama conection
            response = yield from self._call_llama(
                system_prompt=system_prompt, user_prompt=user_prompt
            )
            tweet_attempt = json.loads(response.payload)["response"]

            # Check tweet length
            tweet_len = parse_tweet(tweet_attempt).asdict()["weightedLength"]
            if tweet_len < MAX_TWEET_CHARS:
                self.context.logger.info("Tweet is OK!")
                tweet = tweet_attempt
                break

            self.context.logger.error(
                f"Tweet is too long [{tweet_len}]: {tweet_attempt}"
            )

            attempts += 1

        if attempts >= MAX_TWEET_ATTEMPTS:
            self.context.logger.error("Too many attempts. Aborting tweet.")

        return tweet


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

                if self.params.publish_farcaster and not tweet["farcaster_published"]:
                    response = yield from self.publish_cast(tweet["text"])
                    tweet["farcaster_published"] = response["success"]

            # Remove published tweets
            tweets = [
                t for t in tweets if t["twitter_published"] and t["farcaster_published"]
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

    initial_behaviour_cls = PrepareTweetsBehaviour
    abci_app_cls = TsunamiAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [  # type: ignore
        PrepareTweetsBehaviour,
        PublishTweetsBehaviour,
    ]
