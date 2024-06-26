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

"""This module contains the transaction payloads of the TsunamiAbciApp."""

from dataclasses import dataclass

from packages.valory.skills.abstract_round_abci.base import BaseTxPayload


@dataclass(frozen=True)
class TrackChainEventsPayload(BaseTxPayload):
    """Represent a transaction payload for the TrackChainEventsRound."""

    tweets: str


@dataclass(frozen=True)
class TrackReposPayload(BaseTxPayload):
    """Represent a transaction payload for the TrackReposRound."""

    tweets: str


@dataclass(frozen=True)
class TrackOmenPayload(BaseTxPayload):
    """Represent a transaction payload for the TrackOmenRound."""

    tweets: str


@dataclass(frozen=True)
class SunoPayload(BaseTxPayload):
    """Represent a transaction payload for the SunoRound."""

    tweets: str


@dataclass(frozen=True)
class GovernancePayload(BaseTxPayload):
    """Represent a transaction payload for the GovernanceRound."""

    tweets: str


@dataclass(frozen=True)
class PublishTweetsPayload(BaseTxPayload):
    """Represent a transaction payload for the PublishTweetsRound."""

    tweets: str
