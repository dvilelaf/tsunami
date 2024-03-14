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

"""This package contains round behaviours of TsunamiAbciApp."""

from abc import ABC
from typing import Generator, Set, Type, cast, Optional
import json
from packages.dvilela.skills.tsunami_abci.models import Params
from packages.dvilela.skills.tsunami_abci.rounds import (
    PrepareTweetsPayload,
    PrepareTweetsRound,
    PublishTweetsPayload,
    PublishTweetsRound,
    SynchronizedData,
    TsunamiAbciApp,
)
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)
from packages.valory.protocols.srr.dialogues import SrrDialogue, SrrDialogues
from packages.valory.skills.abstract_round_abci.models import Requests
from packages.valory.protocols.srr.message import SrrMessage
from packages.valory.connections.farcaster.connection import (
    PUBLIC_ID as FARCASTER_CONNECTION_PUBLIC_ID,
)
from packages.valory.connections.twitter.connection import (
    PUBLIC_ID as TWITTER_CONNECTION_PUBLIC_ID,
)
from packages.valory.protocols.twitter.message import TwitterMessage
from packages.valory.skills.twitter_write_abci.dialogues import (
    TwitterDialogue,
    TwitterDialogues,
)


class TsunamiBaseBehaviour(BaseBehaviour, ABC):
    """Base behaviour for the tsunami_abci skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)


class PrepareTweetsBehaviour(TsunamiBaseBehaviour):
    """PrepareTweetsBehaviour"""

    matching_round: Type[AbstractRound] = PrepareTweetsRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            payload = PrepareTweetsPayload(sender=sender, content=...)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


    def get_events(self) -> Generator:
        """Get registries events"""

        # Loop chains

            # Loop registries


class PublishTweetsBehaviour(TsunamiBaseBehaviour):
    """PublishTweetsBehaviour"""

    matching_round: Type[AbstractRound] = PublishTweetsRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():

            tweets = self.synchronized_data.tweets

            # Publish tweets
            for tweet in tweets:

                if not tweet["twitter"]:
                    tweet["twitter"] = yield from self.publish_tweet(tweet["text"])

                if not tweet["farcaster"]:
                    tweet["farcaster"] = yield from self.publish_cast(tweet["text"])

            # Remove published tweets
            tweets = [t for t in tweets if t["twitter"] and t["farcaster"]]

            payload = PublishTweetsPayload(
                sender=self.context.agent_address,
                tweets=tweets
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


    def publish_tweet(self, text) -> Generator:
        """Publish tweet"""

        self.context.logger.info(f"Creating tweet with text: {text}")
        response = yield from self._create_tweet(text=text, credentials=self.params.twitter_credentials)

        if response.performative == TwitterMessage.Performative.ERROR:
            self.context.logger.error(
                f"Writing tweet failed with following error message: {response.message}"
            )
            return {"success": False, "tweet_id": None}
        else:
            self.context.logger.info(f"Posted tweet with ID: {response.tweet_id}")
            return {"success": True, "tweet_id": response.tweet_id}


    def publish_cast(self, text) -> Generator:
        """Publish cast"""

        self.context.logger.info(f"Creating cast with text: {text}")

        response = yield from self._create_cast(text=text)
        response_data = json.loads(response.payload)

        if response.error:
            self.context.logger.error(
                f"Writing cast failed with following error message: {response.payload}"
            )
            return {"success": False, "cast_id": None}
        else:
            self.context.logger.info(f"Posted cast with ID: {response_data['cast_id']}")
            return {"success": True, "cast_id": response_data["cast_id"]}


    def _create_tweet(
        self,
        text: str,
        credentials: dict,
    ) -> Generator[None, None, TwitterMessage]:
        """Send an http request message from the skill context."""
        twitter_dialogues = cast(TwitterDialogues, self.context.twitter_dialogues)
        twitter_message, twitter_dialogue = twitter_dialogues.create(
            counterparty=str(TWITTER_CONNECTION_PUBLIC_ID),
            performative=TwitterMessage.Performative.CREATE_TWEET,
            text=json.dumps(
                {"text": text, "credentials": credentials}
            ),  # temp hack: we need to update the connection and protocol
        )
        twitter_message = cast(TwitterMessage, twitter_message)
        twitter_dialogue = cast(TwitterDialogue, twitter_dialogue)
        response = yield from self._do_twitter_request(
            twitter_message, twitter_dialogue
        )
        return response


    def _create_cast(
        self,
        text: str,
    ) -> Generator[None, None, SrrMessage]:
        """Send an http request message from the skill context."""
        srr_dialogues = cast(SrrDialogues, self.context.srr_dialogues)
        farcaster_message, srr_dialogue = srr_dialogues.create(
            counterparty=str(FARCASTER_CONNECTION_PUBLIC_ID),
            performative=SrrMessage.Performative.REQUEST,
            payload=json.dumps(
                {"method": "post_cast", "args": {"text": text}}
            ),
        )
        farcaster_message = cast(SrrMessage, farcaster_message)
        srr_dialogue = cast(SrrDialogue, srr_dialogue)
        response = yield from self._do_farcaster_request(
            farcaster_message, srr_dialogue
        )
        return response


    def _do_twitter_request(
        self,
        message: TwitterMessage,
        dialogue: TwitterDialogue,
        timeout: Optional[float] = None,
    ) -> Generator[None, None, TwitterMessage]:
        """Do a request and wait the response, asynchronously."""

        self.context.outbox.put_message(message=message)
        request_nonce = self._get_request_nonce_from_dialogue(dialogue)
        cast(Requests, self.context.requests).request_id_to_callback[
            request_nonce
        ] = self.get_callback_request()
        response = yield from self.wait_for_message(timeout=timeout)
        return response


    def _do_farcaster_request(
        self,
        message: SrrMessage,
        dialogue: SrrDialogue,
        timeout: Optional[float] = None,
    ) -> Generator[None, None, SrrMessage]:
        """Do a request and wait the response, asynchronously."""

        self.context.outbox.put_message(message=message)
        request_nonce = self._get_request_nonce_from_dialogue(dialogue)
        cast(Requests, self.context.requests).request_id_to_callback[
            request_nonce
        ] = self.get_callback_request()
        response = yield from self.wait_for_message(timeout=timeout)
        return response


class TsunamiRoundBehaviour(AbstractRoundBehaviour):
    """TsunamiRoundBehaviour"""

    initial_behaviour_cls = PrepareTweetsBehaviour
    abci_app_cls = TsunamiAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [PrepareTweetsBehaviour, PublishTweetsBehaviour]
