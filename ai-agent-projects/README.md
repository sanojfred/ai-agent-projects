# AI Agent Projects

Hands-on projects building AI agents on a Windows PC: local LLMs (Ollama), free cloud models, MCP tools, Docker, and open-source GitHub apps.

> Status labels are honest. "Tested" means unit tests pass (`python -m unittest discover -s tests` in each folder). Nothing here needs third-party packages.

| Project | What it is | Status |
|---|---|---|
| [local-ai-agent-stack](./local-ai-agent-stack) | Router that sends chats to local Ollama, OpenRouter or Gemini with automatic fallback | Working, tested |
| [fo-trading-agent](./fo-trading-agent) | Strategy agents + backtester + super-agent that outputs a trade setup (analysis only) | Working prototype, tested on synthetic data |
| [business-outreach-bot](./business-outreach-bot) | Filters businesses without websites and drafts quotes (never sends) | Working, tested |

## Tech used
Ollama (Qwen, DeepSeek), Claude Code, Docker, Git, MCP, OpenRouter, Gemini API, Groq API, PowerShell

## Setup note
No API keys are committed. Copy `.env.example` to `.env` in a project and add your own keys.
