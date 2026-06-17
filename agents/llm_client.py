import os
import requests

VLLM_URL = os.environ.get(
    "LLM_API_URL", "http://localhost:8000/v1/chat/completions"
)
MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "Qwen/Qwen2-7B-Instruct")


def call_llm(prompt, max_tokens=2500, temperature=0.1, timeout=180):
    """
    Raises on HTTP errors / connection errors so callers can catch
    and fall back gracefully.
    """
    response = requests.post(
        VLLM_URL,
        json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected LLM response shape: {data}") from exc