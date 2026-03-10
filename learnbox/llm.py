import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:1.5b"

SYSTEM_PROMPT = (
    "You are LearnBox, a friendly educational assistant for students aged 8-18. "
    "Give clear, simple, accurate answers. Use examples and analogies. "
    "Only state facts you are confident are correct — do not add extra details that may be wrong. "
    "Keep answers concise — 2 to 3 sentences maximum."
)


def ask(prompt: str, timeout: float = 30.0) -> str:
    """Send a prompt to the model and return the full response as a string."""
    payload = {
        "model": MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
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
