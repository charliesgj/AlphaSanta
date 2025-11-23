alphasanta.com | https://docs.alphasanta.com

# AlphaSanta Submission Worker

![AlphaSanta mascot](santa.png)

Built on the `alphasanta-process-submissions` flow, this worker reads pending letters from Supabase, dispatches the elf agents, and writes back Santa's decision. The architecture also includes a Google ADK-based A2A protocol layer for remote agent communication, ready to be enabled to collaborate with external agents when needed.

## Quick links
- X: https://x.com/Your_AlphaSanta
- Telegram: https://t.me/AlphaSanta_Signals

## Prerequisites
- Python 3.12+

## Install
```bash
git clone <repo-url>
cd AlphaSanta
python -m venv .venv && source .venv/bin/activate
# Reproducible install (pins all versions)
pip install -r requirements.lock
# Editable install for local development / CLI entrypoints
pip install -e .
```

## Configure `.env`
Create a `.env` in the repo root (or export these in your shell). Defaults/placeholder values:

```bash
SUPABASE_URL=
SUPABASE_ANON_KEY=
TAVILY_API_KEY=
ANTHROPIC_API_KEY=
ANTHROPIC_MAX_TOKENS=
DESEARCH_API_KEY=
ALPHASANTA_NEOFS_ENABLED=false
NEOFS_CONTAINER_ID=
NEOFS_GATEWAY_URL=
ALPHASANTA_AGENT_ID_MAP="micro:1547e941-2e1b-4953-b53b-d5db4ac869c1,mood:b7b272a5-c33b-48ac-bacc-7653b4249382,macro:3a221876-3b6b-414a-8621-ac24236bba67,santa:a472e4a2-ac08-4a66-adca-55acc8792059"
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=
TWITTER_USER_ID=
TWITTER_BEARER_TOKEN=
TELEGRAM_BOT_TOKEN=
TELEGRAM_DEFAULT_CHAT_ID=
```

Notes:
- Keep the quotes around `ALPHASANTA_AGENT_ID_MAP`; it must stay a single-line string.
- Set `ALPHASANTA_NEOFS_ENABLED=true` only if NeoFS uploads are desired and the container values are valid.

## Run the submission worker
Process pending Supabase rows continuously:

```bash
alphasanta-process-submissions --interval 3
```

The worker polls `status=pending`, marks rows as `processing`, runs all elves plus Santa, then writes the final JSON to `result` and one row per agent to `submission_agents`.

## Testing

```bash
pytest tests
```

Unit tests cover payload shapes and orchestration logic; external APIs/LLMs are not called during the suite.
