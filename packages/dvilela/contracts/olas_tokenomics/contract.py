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

"""This module contains the class to connect to the tokenomics contract."""
import logging
from typing import List, Optional, Union, cast

from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea_ledger_ethereum import EthereumApi
from web3.exceptions import MismatchedABI


PUBLIC_ID = PublicId.from_str("dvilela/olas_tokenomics:0.1.0")

_logger = logging.getLogger(
    f"aea.packages.{PUBLIC_ID.author}.contracts.{PUBLIC_ID.name}.contract"
)


# pylint: disable=too-many-arguments,invalid-name
class OlasTokenomicsContract(Contract):
    """The olas tokenomics contract."""

    contract_id = PUBLIC_ID

    @classmethod
    def get_events(
        cls,
        ledger_api: EthereumApi,
        contract_address: str,
        event_name: str,
        from_block: int,
        to_block: Union[int, str] = "latest",
    ) -> Optional[JSONLike]:
        """Get events."""
        contract_instance = cls.get_instance(ledger_api, contract_address)

        # Avoid parsing too many blocks at a time. This might take too long and
        # the connection could time out.
        MAX_BLOCKS = 5000

        to_block = (
            ledger_api.api.eth.get_block_number() - 1
            if to_block == "latest"
            else to_block
        )

        ranges: List[int] = list(range(from_block, cast(int, to_block), MAX_BLOCKS)) + [
            cast(int, to_block)
        ]

        event = getattr(contract_instance.events, event_name)
        events = []
        for i in range(len(ranges) - 1):
            from_block = ranges[i]
            to_block = ranges[i + 1]
            new_events = []

            while True:
                try:
                    new_events = event.create_filter(
                        fromBlock=from_block,  # exclusive
                        toBlock=to_block,  # inclusive
                    ).get_all_entries()  # limited to 10k entries for now
                    break
                # Gnosis RPCs sometimes returns:
                # ValueError: Filter with id: x does not exist
                # MismatchedABI: The event signature did not match the provided ABI
                # Retrying several times makes it work
                except ValueError as e:
                    _logger.error(e)
                except MismatchedABI as e:
                    _logger.error(e)

            events += new_events

        return dict(
            events=events,
            latest_block=int(to_block),
        )
