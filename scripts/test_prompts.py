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


from llama_cpp import Llama

from packages.dvilela.skills.tsunami_abci.prompts import (
    REPO_USER_PROMPT_RELEASE,
    SYSTEM_PROMPTS,
)


llm = Llama.from_pretrained(
    # repo_id="Qwen/Qwen1.5-0.5B-Chat-GGUF",
    repo_id="TheBloke/CapybaraHermes-2.5-Mistral-7B-GGUF",
    filename="*Q2_K.gguf",
    verbose=False,
)

output = llm.create_chat_completion(
    messages=[
        {"role": "system", "content": SYSTEM_PROMPTS[0]},
        {
            "role": "user",
            "content": REPO_USER_PROMPT_RELEASE.format(
                version="v0.1.0", repo="dvilelaf/tsunami"
            ),
        },
    ],
    temperature=0.8,
)

print(output["choices"][0]["message"]["content"])
