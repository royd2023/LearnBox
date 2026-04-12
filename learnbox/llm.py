import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:0.5b"

SYSTEM_PROMPT = (
    "You are LearnBox, a friendly educational assistant for students aged 8-18. "
    "Answer in 1-2 sentences maximum. Be direct — no examples, no analogies, no elaboration unless asked. "
    "Only state facts you are confident are correct."
)


def ask(prompt: str, timeout: float = 30.0) -> str:
    """Send a prompt to the model and return the full response as a string."""
    payload = {
        "model": MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 150},
    }
    try:
        response = httpx.post(OLLAMA_URL, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()["response"].strip()
    except httpx.ConnectError:
        raise RuntimeError(
            "Cannot reach Ollama. Make sure it is running (check system tray)."
        )
    except httpx.TimeoutException:
        raise RuntimeError("Ollama request timed out. Try a shorter prompt or increase timeout.")


def stream_ask(prompt: str, timeout: float = 60.0):
    """Yield response tokens one at a time as they arrive."""
    payload = {
        "model": MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": True,
        "options": {"num_predict": 150},
    }
    try:
        with httpx.stream("POST", OLLAMA_URL, json=payload, timeout=timeout) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                import json
                chunk = json.loads(line)
                token = chunk.get("response", "")
                if token:
                    yield token
                if chunk.get("done"):
                    break
    except httpx.ConnectError:
        raise RuntimeError(
            "Cannot reach Ollama. Make sure it is running (check system tray)."
        )
