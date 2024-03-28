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
