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

"""
This module contains the classes required for kv_storage dialogue management.

- KvStorageDialogue: The dialogue class maintains state of a dialogue and manages it.
- KvStorageDialogues: The dialogues class keeps track of all dialogues.
"""

from abc import ABC
from typing import Callable, Dict, FrozenSet, Type, cast

from aea.common import Address
from aea.protocols.base import Message
from aea.protocols.dialogue.base import Dialogue, DialogueLabel, Dialogues

from packages.dvilela.protocols.kv_storage.message import KvStorageMessage


class KvStorageDialogue(Dialogue):
    """The kv_storage dialogue class maintains state of a dialogue and manages it."""

    INITIAL_PERFORMATIVES: FrozenSet[Message.Performative] = frozenset(
        {
            KvStorageMessage.Performative.READ_REQUEST,
            KvStorageMessage.Performative.CREATE_OR_UPDATE_REQUEST,
        }
    )
    TERMINAL_PERFORMATIVES: FrozenSet[Message.Performative] = frozenset(
        {
            KvStorageMessage.Performative.READ_RESPONSE,
            KvStorageMessage.Performative.SUCCESS,
            KvStorageMessage.Performative.ERROR,
        }
    )
    VALID_REPLIES: Dict[Message.Performative, FrozenSet[Message.Performative]] = {
        KvStorageMessage.Performative.CREATE_OR_UPDATE_REQUEST: frozenset(
            {KvStorageMessage.Performative.SUCCESS, KvStorageMessage.Performative.ERROR}
        ),
        KvStorageMessage.Performative.ERROR: frozenset(),
        KvStorageMessage.Performative.READ_REQUEST: frozenset(
            {
                KvStorageMessage.Performative.READ_RESPONSE,
                KvStorageMessage.Performative.ERROR,
            }
        ),
        KvStorageMessage.Performative.READ_RESPONSE: frozenset(),
        KvStorageMessage.Performative.SUCCESS: frozenset(),
    }

    class Role(Dialogue.Role):
        """This class defines the agent's role in a kv_storage dialogue."""

        CONNECTION = "connection"
        SKILL = "skill"

    class EndState(Dialogue.EndState):
        """This class defines the end states of a kv_storage dialogue."""

        SUCCESSFUL = 0

    def __init__(
        self,
        dialogue_label: DialogueLabel,
        self_address: Address,
        role: Dialogue.Role,
        message_class: Type[KvStorageMessage] = KvStorageMessage,
    ) -> None:
        """
        Initialize a dialogue.

        :param dialogue_label: the identifier of the dialogue
        :param self_address: the address of the entity for whom this dialogue is maintained
        :param role: the role of the agent this dialogue is maintained for
        :param message_class: the message class used
        """
        Dialogue.__init__(
            self,
            dialogue_label=dialogue_label,
            message_class=message_class,
            self_address=self_address,
            role=role,
        )


class KvStorageDialogues(Dialogues, ABC):
    """This class keeps track of all kv_storage dialogues."""

    END_STATES = frozenset({KvStorageDialogue.EndState.SUCCESSFUL})

    _keep_terminal_state_dialogues = False

    def __init__(
        self,
        self_address: Address,
        role_from_first_message: Callable[[Message, Address], Dialogue.Role],
        dialogue_class: Type[KvStorageDialogue] = KvStorageDialogue,
    ) -> None:
        """
        Initialize dialogues.

        :param self_address: the address of the entity for whom dialogues are maintained
        :param dialogue_class: the dialogue class used
        :param role_from_first_message: the callable determining role from first message
        """
        Dialogues.__init__(
            self,
            self_address=self_address,
            end_states=cast(FrozenSet[Dialogue.EndState], self.END_STATES),
            message_class=KvStorageMessage,
            dialogue_class=dialogue_class,
            role_from_first_message=role_from_first_message,
        )
