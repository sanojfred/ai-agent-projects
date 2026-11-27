"""Provider-agnostic chat router: Ollama (local), OpenRouter and Gemini (free cloud tiers).

Standard library only. Tries providers in order and falls back on failure.
Configure through environment variables (see .env.example).

    python llm_router.py "Explain MCP in two sentences" --providers ollama,openrouter,gemini
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_ORDER = ["ollama", "openrouter", "gemini"]


class ProviderError(Exception):
    pass


def _post(url, payload, headers=None, timeout=120):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise ProviderError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:200]}")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise ProviderError(str(e))


def _ollama(messages):
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
    data = _post(f"{host}/api/chat", {"model": model, "messages": messages, "stream": False})
    try:
        return data["message"]["content"]
    except KeyError:
        raise ProviderError(f"unexpected Ollama response: {str(data)[:200]}")


def _openrouter(messages):
    key = os.environ.get("OPENROUTER_API_KEY")
    model = os.environ.get("OPENROUTER_MODEL")
    if not key or not model:
        raise ProviderError("OPENROUTER_API_KEY and OPENROUTER_MODEL must be set")
    base = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    data = _post(
        f"{base}/chat/completions",
        {"model": model, "messages": messages},
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise ProviderError(f"unexpected OpenRouter response: {str(data)[:200]}")


def _gemini(messages):
    key = os.environ.get("GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL")
    if not key or not model:
        raise ProviderError("GEMINI_API_KEY and GEMINI_MODEL must be set")
    base = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    system = [m["content"] for m in messages if m["role"] == "system"]
    contents = [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
        for m in messages
        if m["role"] != "system"
    ]
    payload = {"contents": contents}
    if system:
        payload["systemInstruction"] = {"parts": [{"text": "\n".join(system)}]}
    data = _post(f"{base}/models/{model}:generateContent", payload, headers={"x-goog-api-key": key})
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise ProviderError(f"unexpected Gemini response: {str(data)[:200]}")


PROVIDERS = {"ollama": _ollama, "openrouter": _openrouter, "gemini": _gemini}


def chat(messages, order=None):
    """Return (provider_name, reply). Raises ProviderError if every provider fails."""
    errors = []
    for name in order or DEFAULT_ORDER:
        fn = PROVIDERS.get(name)
        if fn is None:
            errors.append(f"{name}: unknown provider")
            continue
        try:
            return name, fn(messages)
        except ProviderError as e:
            errors.append(f"{name}: {e}")
    raise ProviderError("all providers failed -> " + " | ".join(errors))


def ask(prompt, system=None, order=None):
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    return chat(messages, order)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("prompt")
    p.add_argument("--system")
    p.add_argument("--providers", default=",".join(DEFAULT_ORDER))
    args = p.parse_args(argv)
    try:
        name, reply = ask(args.prompt, args.system, [x.strip() for x in args.providers.split(",") if x.strip()])
    except ProviderError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"[{name}]\n{reply}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
