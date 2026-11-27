# Local AI Agent Stack

`llm_router.py` is a small, dependency-free router that sends a chat to **Ollama (local)**, **OpenRouter** or **Gemini** and falls back to the next provider if one fails. Other tools in this repo import it.

## Background
I run local models (Qwen, DeepSeek) with Ollama on Windows (RTX 4060, 16 GB RAM), run Git-hosted AI apps in Docker, use MCP tools with agents, and use free OpenRouter and Gemini API keys for cloud models. This router is the common layer I use to switch between them.

## Use
```
copy .env.example .env      # add your own keys and model ids
python llm_router.py "Explain MCP in two sentences"
python llm_router.py "Hi" --providers openrouter,gemini
```
In Python: `from llm_router import ask; provider, reply = ask("Hi", system="Be brief")`

Docker (Ollama stays on the host so it can use the GPU): `docker compose up`

## Tests
`python -m unittest discover -s tests` (uses a local mock server, no keys needed)

## Limitations
- Non-streaming, text only
- Free tiers have rate limits; the fallback order is configurable with `--providers`
- Model ids are set in `.env`, since free model lists change often

## Architecture
```
app / agent -> llm_router -> Ollama (local) | OpenRouter | Gemini
      \-> MCP servers (tools)
```
