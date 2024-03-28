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

import json
from enum import Enum
from typing import Dict, FrozenSet, Set, cast

from packages.dvilela.skills.tsunami_abci.payloads import (
    PublishTweetsPayload,
    TrackChainEventsPayload,
    TrackOmenPayload,
    TrackReposPayload,
)
from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AppState,
    BaseSynchronizedData,
    CollectSameUntilThresholdRound,
    CollectionRound,
    DegenerateRound,
    DeserializedCollection,
    EventToTimeout,
    get_name,
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

    def _get_deserialized(self, key: str) -> DeserializedCollection:
        """Strictly get a collection and return it deserialized."""
        serialized = self.db.get_strict(key)
        return CollectionRound.deserialize_collection(serialized)

    @property
    def tweets(self) -> list:
        """Get the tweets."""
        return cast(list, json.loads(cast(str, self.db.get("tweets", "[]"))))

    @property
    def participant_to_events(self) -> DeserializedCollection:
        """Get the participants to the event tracking round."""
        return self._get_deserialized("participant_to_events")

    @property
    def participant_to_repos(self) -> DeserializedCollection:
        """Get the participants to the repo tracking round."""
        return self._get_deserialized("participant_to_repos")

    @property
    def participant_to_publication(self) -> DeserializedCollection:
        """Get the participants to the tweet publication round."""
        return self._get_deserialized("participant_to_publication")


class TrackChainEventsRound(CollectSameUntilThresholdRound):
    """TrackChainEventsRound"""

    payload_class = TrackChainEventsPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_events)
    selection_key = get_name(SynchronizedData.tweets)

    # Event.ROUND_TIMEOUT  # this needs to be mentioned for static checkers


class TrackReposRound(CollectSameUntilThresholdRound):
    """TrackReposRound"""

    payload_class = TrackReposPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_repos)
    selection_key = get_name(SynchronizedData.tweets)

    # Event.ROUND_TIMEOUT  # this needs to be mentioned for static checkers


class TrackOmenRound(CollectSameUntilThresholdRound):
    """TrackOmenRound"""

    payload_class = TrackOmenPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_repos)
    selection_key = get_name(SynchronizedData.tweets)

    # Event.ROUND_TIMEOUT  # this needs to be mentioned for static checkers


class PublishTweetsRound(CollectSameUntilThresholdRound):
    """PublishTweetsRound"""

    payload_class = PublishTweetsPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_publication)
    selection_key = get_name(SynchronizedData.tweets)

    # Event.ROUND_TIMEOUT  # this needs to be mentioned for static checkers


class FinishedPublishRound(DegenerateRound):
    """FinishedPublishRound"""


class TsunamiAbciApp(AbciApp[Event]):
    """TsunamiAbciApp"""

    initial_round_cls: AppState = TrackChainEventsRound
    initial_states: Set[AppState] = {TrackChainEventsRound}
    transition_function: AbciAppTransitionFunction = {
        TrackChainEventsRound: {
            Event.DONE: TrackReposRound,
            Event.NO_MAJORITY: TrackChainEventsRound,
            Event.ROUND_TIMEOUT: TrackChainEventsRound,
        },
        TrackReposRound: {
            Event.DONE: TrackOmenRound,
            Event.NO_MAJORITY: TrackReposRound,
            Event.ROUND_TIMEOUT: TrackReposRound,
        },
        TrackOmenRound: {
            Event.DONE: PublishTweetsRound,
            Event.NO_MAJORITY: TrackOmenRound,
            Event.ROUND_TIMEOUT: TrackOmenRound,
        },
        PublishTweetsRound: {
            Event.DONE: FinishedPublishRound,
            Event.NO_MAJORITY: PublishTweetsRound,
            Event.ROUND_TIMEOUT: PublishTweetsRound,
        },
        FinishedPublishRound: {},
    }
    final_states: Set[AppState] = {FinishedPublishRound}
    event_to_timeout: EventToTimeout = {}
    cross_period_persisted_keys: FrozenSet[str] = frozenset()
    db_pre_conditions: Dict[AppState, Set[str]] = {
        TrackChainEventsRound: set(),
    }
    db_post_conditions: Dict[AppState, Set[str]] = {
        FinishedPublishRound: set(),
    }
