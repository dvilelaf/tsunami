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

"""This package contains the rounds of PrepareTweetsAbciApp."""

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

from packages.dvilela.skills.prepare_tweets_abci.payloads import (
    PrepareTweetsPayload,
)


class Event(Enum):
    """PrepareTweetsAbciApp Events"""

    DONE = "done"
    ERROR = "error"
    NO_MAJORITY = "no_majority"
    RETRY = "retry"
    ROUND_TIMEOUT = "round_timeout"


class SynchronizedData(BaseSynchronizedData):
    """
    Class to represent the synchronized data.

    This data is replicated by the tendermint application.
    """


class PrepareTweetsRound(AbstractRound):
    """PrepareTweetsRound"""

    payload_class = PrepareTweetsPayload
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

    def check_payload(self, payload: PrepareTweetsPayload) -> None:
        """Check payload."""
        raise NotImplementedError

    def process_payload(self, payload: PrepareTweetsPayload) -> None:
        """Process payload."""
        raise NotImplementedError


class FinishedPrepareTweetsRound(DegenerateRound):
    """FinishedPrepareTweetsRound"""


class PrepareTweetsAbciApp(AbciApp[Event]):
    """PrepareTweetsAbciApp"""

    initial_round_cls: AppState = PrepareTweetsRound
    initial_states: Set[AppState] = {PrepareTweetsRound}
    transition_function: AbciAppTransitionFunction = {
        PrepareTweetsRound: {
            Event.DONE: FinishedPrepareTweetsRound,
            Event.ERROR: PrepareTweetsRound,
            Event.NO_MAJORITY: PrepareTweetsRound,
            Event.RETRY: PrepareTweetsRound,
            Event.ROUND_TIMEOUT: PrepareTweetsRound
        },
        FinishedPrepareTweetsRound: {}
    }
    final_states: Set[AppState] = {FinishedPrepareTweetsRound}
    event_to_timeout: EventToTimeout = {}
    cross_period_persisted_keys: FrozenSet[str] = frozenset()
    db_pre_conditions: Dict[AppState, Set[str]] = {
        PrepareTweetsRound: [],
    }
    db_post_conditions: Dict[AppState, Set[str]] = {
        FinishedPrepareTweetsRound: [],
    }
