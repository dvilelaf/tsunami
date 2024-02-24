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

"""Test dialogues module for kv_storage protocol."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,redefined-builtin
from aea.test_tools.test_protocol import BaseProtocolDialoguesTestCase

from packages.dvilela.protocols.kv_storage.dialogues import (
    KvStorageDialogue,
    KvStorageDialogues,
)
from packages.dvilela.protocols.kv_storage.message import KvStorageMessage


class TestDialoguesKvStorage(BaseProtocolDialoguesTestCase):
    """Test for the 'kv_storage' protocol dialogues."""

    MESSAGE_CLASS = KvStorageMessage

    DIALOGUE_CLASS = KvStorageDialogue

    DIALOGUES_CLASS = KvStorageDialogues

    ROLE_FOR_THE_FIRST_MESSAGE = KvStorageDialogue.Role.CONNECTION  # CHECK

    def make_message_content(self) -> dict:
        """Make a dict with message contruction content for dialogues.create."""
        return dict(
            performative=KvStorageMessage.Performative.READ_REQUEST,
            keys=("some str",),
        )
