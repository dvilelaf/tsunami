# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2024 David Vilela Freire
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
from typing import Dict, FrozenSet, cast, Optional, Set, Tuple

from packages.dvilela.skills.tsunami_abci.payloads import (
    PrepareTweetsPayload,
    PublishTweetsPayload,
)
from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    CollectSameUntilThresholdRound,
    AppState,
    BaseSynchronizedData,
    DegenerateRound,
    EventToTimeout,
    get_name
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

    @property
    def tweets(self) -> list:
        """Get the tweets."""
        return cast(list, self.db.get("tweets", []))


class PrepareTweetsRound(CollectSameUntilThresholdRound):
    """PrepareTweetsRound"""

    payload_class = PrepareTweetsPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_preparation)
    selection_key = get_name(SynchronizedData.tweets)


class PublishTweetsRound(CollectSameUntilThresholdRound):
    """PublishTweetsRound"""

    payload_class = PublishTweetsPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_publication)
    selection_key = get_name(SynchronizedData.tweets)



class FinishedPublishRound(DegenerateRound):
    """FinishedPublishRound"""


class TsunamiAbciApp(AbciApp[Event]):
    """TsunamiAbciApp"""

    initial_round_cls: AppState = PrepareTweetsRound
    initial_states: Set[AppState] = {PrepareTweetsRound}
    transition_function: AbciAppTransitionFunction = {
        PrepareTweetsRound: {
            Event.DONE: PublishTweetsRound,
            Event.ERROR: PrepareTweetsRound,
            Event.NO_MAJORITY: PrepareTweetsRound,
            Event.RETRY: PrepareTweetsRound,
            Event.ROUND_TIMEOUT: PrepareTweetsRound,
        },
        PublishTweetsRound: {
            Event.DONE: FinishedPublishRound,
            Event.ERROR: PublishTweetsRound,
            Event.NO_MAJORITY: PublishTweetsRound,
            Event.RETRY: PublishTweetsRound,
            Event.ROUND_TIMEOUT: PublishTweetsRound,
        },
        FinishedPublishRound: {},
    }
    final_states: Set[AppState] = {FinishedPublishRound}
    event_to_timeout: EventToTimeout = {}
    cross_period_persisted_keys: FrozenSet[str] = frozenset()
    db_pre_conditions: Dict[AppState, Set[str]] = {
        PrepareTweetsRound: [],
    }
    db_post_conditions: Dict[AppState, Set[str]] = {
        FinishedPublishRound: [],
    }
