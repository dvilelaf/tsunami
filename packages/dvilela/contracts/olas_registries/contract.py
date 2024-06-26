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
from typing import List, Optional, Union, cast

from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea_ledger_ethereum import EthereumApi
from web3 import Web3
from web3.exceptions import MismatchedABI


PUBLIC_ID = PublicId.from_str("dvilela/olas_registries:0.1.0")

_logger = logging.getLogger(
    f"aea.packages.{PUBLIC_ID.author}.contracts.{PUBLIC_ID.name}.contract"
)

EVENT_ABIS = {
    "ethereum": [
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "uint256",
                    "name": "serviceId",
                    "type": "uint256",
                }
            ],
            "name": "CreateService",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "unitId",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "enum UnitRegistry.UnitType",
                    "name": "uType",
                    "type": "uint8",
                },
                {
                    "indexed": False,
                    "internalType": "bytes32",
                    "name": "unitHash",
                    "type": "bytes32",
                },
            ],
            "name": "CreateUnit",
            "type": "event",
        },
    ],
    "gnosis": [
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "uint256",
                    "name": "serviceId",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "bytes32",
                    "name": "configHash",
                    "type": "bytes32",
                },
            ],
            "name": "CreateService",
            "type": "event",
        },
    ],
}


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
        from_block: int,
        to_block: Union[int, str] = "latest",
        chain_name: str = "ethereum",
    ) -> Optional[JSONLike]:
        """Get events."""
        contract_instance = ledger_api.api.eth.contract(
            Web3.to_checksum_address(contract_address), abi=EVENT_ABIS[chain_name]
        )

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
