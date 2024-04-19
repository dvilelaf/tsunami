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

"""This module contains the shared state for the abci skill of TsunamiAbciApp."""

import json
from typing import Any

from packages.dvilela.skills.tsunami_abci.rounds import TsunamiAbciApp
from packages.valory.skills.abstract_round_abci.models import ApiSpecs, BaseParams
from packages.valory.skills.abstract_round_abci.models import (
    BenchmarkTool as BaseBenchmarkTool,
)
from packages.valory.skills.abstract_round_abci.models import Requests as BaseRequests
from packages.valory.skills.abstract_round_abci.models import (
    SharedState as BaseSharedState,
)


class SharedState(BaseSharedState):
    """Keep the current shared state of the skill."""

    abci_app_cls = TsunamiAbciApp


Requests = BaseRequests
BenchmarkTool = BaseBenchmarkTool


class RandomnessApi(ApiSpecs):
    """A model that wraps ApiSpecs for randomness api specifications."""


class Params(BaseParams):  # pylint: disable=too-many-instance-attributes
    """Parameters."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the parameters object."""
        self.publish_twitter = self._ensure("publish_twitter", kwargs, bool)
        self.publish_farcaster = self._ensure("publish_farcaster", kwargs, bool)
        self.publish_telegram = self._ensure("publish_telegram", kwargs, bool)
        self.telegram_token = self._ensure("telegram_token", kwargs, str)
        self.telegram_chat_id = self._ensure("telegram_chat_id", kwargs, int)
        self.service_registry_address_ethereum = self._ensure(
            "service_registry_address_ethereum", kwargs, str
        )
        self.agent_registry_address_ethereum = self._ensure(
            "agent_registry_address_ethereum", kwargs, str
        )
        self.component_registry_address_ethereum = self._ensure(
            "component_registry_address_ethereum", kwargs, str
        )
        self.service_registry_address_gnosis = self._ensure(
            "service_registry_address_gnosis", kwargs, str
        )
        self.initial_block_ethereum = self._ensure(
            "initial_block_ethereum", kwargs, int
        )
        self.initial_block_gnosis = self._ensure("initial_block_gnosis", kwargs, int)
        self.twitter_credentials = json.loads(
            self._ensure("twitter_credentials", kwargs, str)
        )
        self.event_tracking_enabled = self._ensure(
            "event_tracking_enabled", kwargs, bool
        )
        self.repo_tracking_enabled = self._ensure("repo_tracking_enabled", kwargs, bool)
        self.omen_tracking_enabled = self._ensure("omen_tracking_enabled", kwargs, bool)
        self.suno_enabled = self._ensure("suno_enabled", kwargs, bool)
        super().__init__(*args, **kwargs)
