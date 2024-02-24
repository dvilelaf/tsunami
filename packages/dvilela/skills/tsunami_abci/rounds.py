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

"""This package contains the rounds of TsunamiAbciApp."""

from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AbstractRound,
    AppState,
    BaseSynchronizedData,
    DegenerateRound,
    EventToTimeout,
)

from packages.dvilela.skills.tsunami_abci.payloads import (
    GetEventsPayload,
    PublishTweetsPayload,
)


class Event(Enum):
    """TsunamiAbciApp Events"""

    ERROR = "error"
    DONE = "done"
    NO_MAJORITY = "no_majority"
    ROUND_TIMEOUT = "round_timeout"
    RETRY = "retry"


class SynchronizedData(BaseSynchronizedData):
    """
    Class to represent the synchronized data.

    This data is replicated by the tendermint application.
    """


class GetEventsRound(AbstractRound):
    """GetEventsRound"""

    payload_class = GetEventsPayload
    payload_attribute = ""  # TODO: update
    synchronized_data_class = SynchronizedData

    # TODO: replace AbstractRound with one of CollectDifferentUntilAllRound,
    # CollectSameUntilAllRound, CollectSameUntilThresholdRound,
    # CollectDifferentUntilThresholdRound, OnlyKeeperSendsRound, VotingRound,
    # from packages/valory/skills/abstract_round_abci/base.py
    # or implement the methods

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        raise NotImplementedError

    def check_payload(self, payload: GetEventsPayload) -> None:
        """Check payload."""
        raise NotImplementedError

    def process_payload(self, payload: GetEventsPayload) -> None:
        """Process payload."""
        raise NotImplementedError


class PublishTweetsRound(AbstractRound):
    """PublishTweetsRound"""

    payload_class = PublishTweetsPayload
    payload_attribute = ""  # TODO: update
    synchronized_data_class = SynchronizedData

    # TODO: replace AbstractRound with one of CollectDifferentUntilAllRound,
    # CollectSameUntilAllRound, CollectSameUntilThresholdRound,
    # CollectDifferentUntilThresholdRound, OnlyKeeperSendsRound, VotingRound,
    # from packages/valory/skills/abstract_round_abci/base.py
    # or implement the methods

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        raise NotImplementedError

    def check_payload(self, payload: PublishTweetsPayload) -> None:
        """Check payload."""
        raise NotImplementedError

    def process_payload(self, payload: PublishTweetsPayload) -> None:
        """Process payload."""
        raise NotImplementedError


class FinishedPublishRound(DegenerateRound):
    """FinishedPublishRound"""


class TsunamiAbciApp(AbciApp[Event]):
    """TsunamiAbciApp"""

    initial_round_cls: AppState = GetEventsRound
    initial_states: Set[AppState] = {GetEventsRound}
    transition_function: AbciAppTransitionFunction = {
        GetEventsRound: {
            Event.DONE: PublishTweetsRound,
            Event.ERROR: GetEventsRound,
            Event.NO_MAJORITY: GetEventsRound,
            Event.RETRY: GetEventsRound,
            Event.ROUND_TIMEOUT: GetEventsRound
        },
        PublishTweetsRound: {
            Event.DONE: FinishedPublishRound,
            Event.ERROR: PublishTweetsRound,
            Event.NO_MAJORITY: PublishTweetsRound,
            Event.RETRY: PublishTweetsRound,
            Event.ROUND_TIMEOUT: PublishTweetsRound
        },
        FinishedPublishRound: {}
    }
    final_states: Set[AppState] = {FinishedPublishRound}
    event_to_timeout: EventToTimeout = {}
    cross_period_persisted_keys: FrozenSet[str] = frozenset()
    db_pre_conditions: Dict[AppState, Set[str]] = {
        GetEventsRound: [],
    }
    db_post_conditions: Dict[AppState, Set[str]] = {
        FinishedPublishRound: [],
    }
