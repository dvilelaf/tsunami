# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2023 Valory AG
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

"""This module contains the class to connect to the wveolas contract."""
import logging
from typing import Optional

from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea_ledger_ethereum import EthereumApi


PUBLIC_ID = PublicId.from_str("dvilela/olas_registries:0.1.0")

_logger = logging.getLogger(
    f"aea.packages.{PUBLIC_ID.author}.contracts.{PUBLIC_ID.name}.contract"
)


# pylint: disable=too-many-arguments,invalid-name
class OlasRegistriesContract(Contract):
    """The olas registries contract."""

    contract_id = PUBLIC_ID

    @classmethod
    def get_events(
        cls,
        ledger_api: EthereumApi,
        contract_address: str,
        event_name: str,
        from_block: int = "earliest",
        to_block: int = "latest",
    ) -> Optional[JSONLike]:
        """Get events."""
        contract_instance = cls.get_instance(ledger_api, contract_address)

        # Avoid parsing too many blocks at a time. This might take too long and
        # the connection could time out.
        MAX_BLOCKS = 300000

        to_block = (
            ledger_api.api.eth.get_block_number() - 1
            if to_block == "latest"
            else to_block
        )
        ranges = list(range(from_block, to_block, MAX_BLOCKS)) + [to_block]

        event = getattr(contract_instance.events, event_name)
        events = []
        for i in range(len(ranges) - 1):
            from_block = ranges[i]
            to_block = ranges[i + 1]

            new_events = event.create_filter(
                fromBlock=from_block,  # exclusive
                toBlock=to_block,  # inclusive
            ).get_all_entries()  # limited to 10k entries for now
            events += new_events

        return dict(
            events=events,
            latest_block=int(to_block),
        )

    @classmethod
    def get_token_uri(
        cls, ledger_api: EthereumApi, contract_address: str, unit_id: int
    ) -> Optional[JSONLike]:
        """Get events."""
        contract_instance = cls.get_instance(ledger_api, contract_address)

        result = ledger_api.contract_method_call(
            contract_instance=contract_instance,
            method_name="tokenURI",
            unitId=unit_id,
        )

        return {"result": result}
