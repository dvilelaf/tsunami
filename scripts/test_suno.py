#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2024 Valory AG
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


import os
import time
from http.cookies import SimpleCookie
from threading import Thread
from typing import List, Optional

import requests
from dotenv import load_dotenv


load_dotenv()


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


SUNO_SESSION_ID = os.getenv("SUNO_SESSION_ID")
SUNO_COOKIE = os.getenv("SUNO_COOKIE")
api = SunoAPI(SUNO_SESSION_ID, SUNO_COOKIE)
api.generate_songs(
    prompt="Generate a rap metal song about black holes",
)
