# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2024 Valory AG
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

"""This package contains round behaviours of PrepareTweetsAbciApp."""

from abc import ABC
from typing import Generator, Set, Type, cast, List, Any

from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.dvilela.skills.prepare_tweets_abci.models import Params
from packages.dvilela.skills.prepare_tweets_abci.rounds import (
    SynchronizedData,
    PrepareTweetsAbciApp,
    PrepareTweetsRound,
)
from packages.dvilela.skills.prepare_tweets_abci.rounds import (
    PrepareTweetsPayload,
)
from packages.dvilela.contracts.service_registry.contract import (
    ServiceRegistryContract,
)
from packages.dvilela.protocols.kv_storage.message import KvStorageMessage
from packages.dvilela.skills.prepare_tweets_abci.dialogues import (
    KvStorageDialogue,
    KvStorageDialogues,
)
from packages.dvilela.connections.kv_store.connection import (
    PUBLIC_ID as KV_STORE_CONNECTION_PUBLIC_ID,
)
from packages.valory.skills.abstract_round_abci.models import Requests

GNOSISSCAN_TX_BASE = "https://gnosisscan.io/tx/"


class PrepareTweetsBaseBehaviour(BaseBehaviour, ABC):
    """Base behaviour for the prepare_tweets_abci skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)


class PrepareTweetsBehaviour(PrepareTweetsBaseBehaviour):
    """PrepareTweetsBehaviour"""

    matching_round: Type[AbstractRound] = PrepareTweetsRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            tweets = self.prepare_tweets()
            write_data = [
                {
                    "text": t,
                    "credentials": self.params.twitter_credentials
                }
                for t in tweets
            ]
            sender = self.context.agent_address
            payload = PrepareTweetsPayload(sender=sender, write_data=write_data)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def prepare_tweets(self) -> Generator[None, None, List[str]]:
        """Prepare tweets"""

        # Get the latest parsed block
        latest_parsed_gnosis_block = self.db_interact(
            performative=KvStorageMessage.Performative.READ_REQUEST,
            keys=["latest_parsed_gnosis_block"]
        )

        # Check for new CreateService events
        contract_api_msg = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=self.params.dynamic_contribution_contract_address,
            contract_id=str(ServiceRegistryContract.contract_id),
            contract_callable="get_create_events",
            from_block=latest_parsed_gnosis_block,
        )
        if contract_api_msg.performative != ContractApiMessage.Performative.STATE:
            self.context.logger.info(
                f"Error retrieving the CreateService events [{contract_api_msg.performative}]"
            )
            return []

        latest_parsed_gnosis_block = cast(dict, contract_api_msg.state.body["last_parsed_block"])
        create_service_events = cast(int, contract_api_msg.state.body["create_service_events"])

        # Build the tweets
        tweets = [
            f"A new autonomous service with id {e['service_id']}has been minted on the Olas Service registry: {GNOSISSCAN_TX_BASE + e['tx_hash']}"
            for e in create_service_events
        ]

        # Write the latest parsed block
        success = self.db_interact(
            performative=KvStorageMessage.Performative.CREATE_OR_UPDATE_REQUEST,
            data={"latest_parsed_gnosis_block": latest_parsed_gnosis_block}
        )

        return tweets


    def db_interact(
        self,
        **kwargs: Any
    ) -> Generator[None, None, KvStorageMessage]:
        """Send an http request message from the skill context."""

        # Initiate a new dialogue with a READ_REQUEST message
        kv_storage_dialogues = cast(KvStorageDialogues, self.context.kv_storage_dialogues)
        twitter_message, twitter_dialogue = kv_storage_dialogues.create(
            counterparty=str(KV_STORE_CONNECTION_PUBLIC_ID),
            performative=kwargs.pop("performative"),
            **kwargs
        )
        kv_storage_message = cast(KvStorageMessage, twitter_message)
        kv_storage_dialogue = cast(KvStorageDialogue, twitter_dialogue)

        # Put the message in the outbox
        self.context.outbox.put_message(message=kv_storage_message)
        request_nonce = self._get_request_nonce_from_dialogue(kv_storage_dialogue)
        cast(Requests, self.context.requests).request_id_to_callback[
            request_nonce
        ] = self.get_callback_request()

        # Await for the response
        response = yield from self.wait_for_message(timeout=None)
        return response


class PrepareTweetsRoundBehaviour(AbstractRoundBehaviour):
    """PrepareTweetsRoundBehaviour"""

    initial_behaviour_cls = PrepareTweetsBehaviour
    abci_app_cls = PrepareTweetsAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [
        PrepareTweetsBehaviour
    ]
