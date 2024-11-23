#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2024 David Vilela Freire
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

"""Suno connection."""

import json
import time
from http.cookies import SimpleCookie
from threading import Thread
from typing import Any, Dict, List, Optional, Tuple, cast

import requests
from aea.configurations.base import PublicId
from aea.connections.base import BaseSyncConnection
from aea.mail.base import Envelope
from aea.protocols.base import Address, Message
from aea.protocols.dialogue.base import Dialogue

from packages.valory.protocols.srr.dialogues import SrrDialogue
from packages.valory.protocols.srr.dialogues import SrrDialogues as BaseSrrDialogues
from packages.valory.protocols.srr.message import SrrMessage


PUBLIC_ID = PublicId.from_str("dvilela/suno:0.1.0")

SUNO_BASE_URL = "https://studio-api.suno.ai"
SUNO_CLERK_URL = "https://clerk.suno.com/v1/client/sessions/{session_id}/tokens?_clerk_js_version=4.72.0-snapshot.vc141245"
SUNO_SONG_URL = "https://suno.com/song/{song_id}"
HTTP_OK = 200
COMMON_HEADERS = {
    "Content-Type": "text/plain;charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Referer": "https://suno.com",
    "Origin": "https://suno.com",
}


class SunoAuth:
    """Suno Cookie"""

    def __init__(self, session_id: str, cookie: str):
        """Init"""
        self._cookie: SimpleCookie = SimpleCookie()
        self._cookie.load(cookie)
        self._session_id: Optional[str] = session_id
        self._token: Optional[str] = None
        self.stop_flag: bool = False

        self.keep_alive_thread = Thread(target=self.keep_alive)
        self.keep_alive_thread.start()

    @property
    def cookie(self) -> Optional[str]:
        """Cookie"""
        return ";".join(
            [f"{i}={self._cookie.get(i).value}" for i in self._cookie.keys()]  # type: ignore
        )

    @cookie.setter
    def cookie(self, value: str) -> None:
        """Load cookie"""
        self._cookie.load(value)

    @property
    def session_id(self) -> Optional[str]:
        """Session id"""
        return self._session_id

    @session_id.setter
    def session_id(self, value: str) -> None:
        self._session_id = value

    @property
    def token(self) -> Optional[str]:
        """Token"""
        return self._token

    @token.setter
    def token(self, value: str) -> None:
        self._token = value

    def update_token(self) -> None:
        """Update token"""
        headers = {"cookie": self.cookie}
        headers.update(COMMON_HEADERS)

        response = requests.post(
            url=SUNO_CLERK_URL.format(session_id=self.session_id),
            headers=headers,
            timeout=60,
        )

        if response.status_code != HTTP_OK:
            print(
                f"Error {response.status_code} while updating the token: {response.json()}"
            )

        response_headers = dict(response.headers)
        cookie = response_headers.get("Set-Cookie")
        token = response.json().get("jwt")

        self.cookie = cookie
        self.token = token

    def keep_alive(self) -> None:
        """Keep alive"""
        print("Starting Suno keep alive...")
        while not self.stop_flag:
            try:
                self.update_token()
            except Exception as e:
                print(f"Exception updating the token: {e}")
            finally:
                time.sleep(5)
        print("Stopped keep alive")

    def stop(self) -> None:
        """Stop"""
        self.stop_flag = True
        self.keep_alive_thread.join()

    def __del__(self) -> None:
        """Destructor"""
        self.stop()


class SunoAPI:
    """Suno API"""

    def __init__(self, session_id: str, cookie: str) -> None:
        """Init"""
        self.auth = SunoAuth(session_id, cookie)

        # Await for the auth to be ready
        while not self.auth.token:
            time.sleep(1)

    def fetch(
        self, url: str, headers: Optional[dict] = None, data: Optional[dict] = None
    ) -> requests.Response:
        """Fetch API"""

        if headers is None:
            headers = {}

        headers.update(COMMON_HEADERS)
        return requests.post(url=url, json=data, headers=headers, timeout=60)

    def generate_songs(
        self,
        prompt: Optional[str] = None,
        title: Optional[str] = None,
        lyrics: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> Optional[List]:
        """Generate music"""

        data = {
            "title": title if title else "",
            "prompt": lyrics if lyrics else "",
            "tags": tags,
            "gpt_description_prompt": prompt if prompt else None,
            "make_instrumental": False,
            "continue_clip_id": None,
            "continue_at": None,
            "mv": "chirp-v3-5",
        }

        headers = {"Authorization": f"Bearer {self.auth.token}"}
        api_url = f"{SUNO_BASE_URL}/api/generate/v2/"
        response = self.fetch(api_url, headers, data)
        if response.status_code != HTTP_OK:
            print(f"Response {response.status_code}: {response.json()}")
            return None

        if "clips" not in response.json():
            print("No clips generated")
            return None

        return [
            SUNO_SONG_URL.format(song_id=song["id"])
            for song in response.json()["clips"]
        ]

    def stop(self) -> None:
        """Destructor"""
        self.auth.stop()


class SrrDialogues(BaseSrrDialogues):
    """A class to keep track of SRR dialogues."""

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize dialogues.

        :param kwargs: keyword arguments
        """

        def role_from_first_message(  # pylint: disable=unused-argument
            message: Message, receiver_address: Address
        ) -> Dialogue.Role:
            """Infer the role of the agent from an incoming/outgoing first message

            :param message: an incoming/outgoing first message
            :param receiver_address: the address of the receiving agent
            :return: The role of the agent
            """
            return SrrDialogue.Role.CONNECTION

        BaseSrrDialogues.__init__(
            self,
            self_address=str(kwargs.pop("connection_id")),
            role_from_first_message=role_from_first_message,
            **kwargs,
        )


class SunoConnection(BaseSyncConnection):
    """Proxy to the functionality of the Suno API."""

    MAX_WORKER_THREADS = 1

    connection_id = PUBLIC_ID

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
        """
        Initialize the connection.

        The configuration must be specified if and only if the following
        parameters are None: connection_id, excluded_protocols or restricted_to_protocols.

        Possible arguments:
        - configuration: the connection configuration.
        - data_dir: directory where to put local files.
        - identity: the identity object held by the agent.
        - crypto_store: the crypto store for encrypted communication.
        - restricted_to_protocols: the set of protocols ids of the only supported protocols for this connection.
        - excluded_protocols: the set of protocols ids that we want to exclude for this connection.

        :param args: arguments passed to component base
        :param kwargs: keyword arguments passed to component base
        """
        super().__init__(*args, **kwargs)
        suno_session_id = self.configuration.config.get("suno_session_id", None)
        suno_cookie = self.configuration.config.get("suno_cookie", None)

        # Temporarily removed
        # self.api = SunoAPI(suno_session_id, suno_cookie)
        self.api = None

        self.dialogues = SrrDialogues(connection_id=PUBLIC_ID)

    def main(self) -> None:
        """
        Run synchronous code in background.

        SyncConnection `main()` usage:
        The idea of the `main` method in the sync connection
        is to provide for a way to actively generate messages by the connection via the `put_envelope` method.

        A simple example is the generation of a message every second:
        ```
        while self.is_connected:
            envelope = make_envelope_for_current_time()
            self.put_enevelope(envelope)
            time.sleep(1)
        ```
        In this case, the connection will generate a message every second
        regardless of envelopes sent to the connection by the agent.
        For instance, this way one can implement periodically polling some internet resources
        and generate envelopes for the agent if some updates are available.
        Another example is the case where there is some framework that runs blocking
        code and provides a callback on some internal event.
        This blocking code can be executed in the main function and new envelops
        can be created in the event callback.
        """

    def on_send(self, envelope: Envelope) -> None:
        """
        Send an envelope.

        :param envelope: the envelope to send.
        """
        srr_message = cast(SrrMessage, envelope.message)

        dialogue = self.dialogues.update(srr_message)

        if srr_message.performative != SrrMessage.Performative.REQUEST:
            self.logger.error(
                f"Performative `{srr_message.performative.value}` is not supported."
            )
            return

        payload, error = self._get_response(
            payload=json.loads(srr_message.payload),
        )

        response_message = cast(
            SrrMessage,
            dialogue.reply(  # type: ignore
                performative=SrrMessage.Performative.RESPONSE,
                target_message=srr_message,
                payload=json.dumps(payload),
                error=error,
            ),
        )

        response_envelope = Envelope(
            to=envelope.sender,
            sender=envelope.to,
            message=response_message,
            context=envelope.context,
        )

        self.put_envelope(response_envelope)

    def _get_response(self, payload: dict) -> Tuple[Dict, bool]:
        """Get response from Llama."""

        self.logger.info(f"Calling Suno API: {payload}")

        try:
            song_urls = self.api.generate_songs(**payload)
            self.logger.info(f"Suno response: {song_urls}")
        except Exception as e:
            return {"error": f"Exception while calling Suno:\n{e}"}, True

        return {"response": song_urls}, False  # type: ignore

    def on_connect(self) -> None:
        """
        Tear down the connection.

        Connection status set automatically.
        """

    def on_disconnect(self) -> None:
        """
        Tear down the connection.

        Connection status set automatically.
        """
        self.api.stop()
