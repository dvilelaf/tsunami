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
from typing import cast, Dict, FrozenSet, Set, Mapping

from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AppState,
    BaseSynchronizedData,
    DegenerateRound,
    EventToTimeout,
    CollectSameUntilThresholdRound,
    get_name,
    CollectionRound
)

from packages.dvilela.skills.prepare_tweets_abci.payloads import (
    PrepareTweetsPayload,
)


class Event(Enum):
    """PrepareTweetsAbciApp Events"""

    DONE = "done"
    ERROR = "error"
    NO_MAJORITY = "no_majority"
    ROUND_TIMEOUT = "round_timeout"


class SynchronizedData(BaseSynchronizedData):
    """
    Class to represent the synchronized data.

    This data is replicated by the tendermint application.
    """

    @property
    def write_data(self) -> list:
        """Get the write_stream_id."""
        return cast(list, self.db.get_strict("write_data"))

    @property
    def participant_to_tweet_preparation(self) -> Mapping[str, PrepareTweetsPayload]:
        """Get the `participant_to_tweet_preparation`."""
        serialized = self.db.get_strict("participant_to_tweet_preparation")
        deserialized = CollectionRound.deserialize_collection(serialized)
        return cast(Mapping[str, PrepareTweetsPayload], deserialized)


class PrepareTweetsRound(CollectSameUntilThresholdRound):
    """PrepareTweetsRound"""

    payload_class = PrepareTweetsPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    none_event = Event.ERROR
    selection_key = get_name(SynchronizedData.write_data)
    collection_key = get_name(SynchronizedData.participant_to_tweet_preparation)


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
