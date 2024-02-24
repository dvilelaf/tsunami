# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2024 dvilela
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

"""Test messages module for kv_storage protocol."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,redefined-builtin
from typing import List

from aea.test_tools.test_protocol import BaseProtocolMessagesTestCase

from packages.dvilela.protocols.kv_storage.message import KvStorageMessage


class TestMessageKvStorage(BaseProtocolMessagesTestCase):
    """Test for the 'kv_storage' protocol message."""

    MESSAGE_CLASS = KvStorageMessage

    def build_messages(self) -> List[KvStorageMessage]:  # type: ignore[override]
        """Build the messages to be used for testing."""
        return [
            KvStorageMessage(
                performative=KvStorageMessage.Performative.READ_REQUEST,
                keys=("some str",),
            ),
            KvStorageMessage(
                performative=KvStorageMessage.Performative.READ_RESPONSE,
                data={"some str": "some str"},
            ),
            KvStorageMessage(
                performative=KvStorageMessage.Performative.CREATE_OR_UPDATE_REQUEST,
                data={"some str": "some str"},
            ),
            KvStorageMessage(
                performative=KvStorageMessage.Performative.SUCCESS,
                message="some str",
            ),
            KvStorageMessage(
                performative=KvStorageMessage.Performative.ERROR,
                message="some str",
            ),
        ]

    def build_inconsistent(self) -> List[KvStorageMessage]:  # type: ignore[override]
        """Build inconsistent messages to be used for testing."""
        return [
            KvStorageMessage(
                performative=KvStorageMessage.Performative.READ_REQUEST,
                # skip content: keys
            ),
            KvStorageMessage(
                performative=KvStorageMessage.Performative.READ_RESPONSE,
                # skip content: data
            ),
            KvStorageMessage(
                performative=KvStorageMessage.Performative.CREATE_OR_UPDATE_REQUEST,
                # skip content: data
            ),
            KvStorageMessage(
                performative=KvStorageMessage.Performative.SUCCESS,
                # skip content: message
            ),
            KvStorageMessage(
                performative=KvStorageMessage.Performative.ERROR,
                # skip content: message
            ),
        ]
