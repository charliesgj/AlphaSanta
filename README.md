# AlphaSanta Usage Guide

## Installation

```bash
# Assuming you are inside the repository root
pip install -e .
# Include AgentCard dependencies if you plan to run the HTTP servers
pip install -e '.[agentcard]'
```

Key environment variables (set in your shell or .env):

```bash
# LLM / tools
export DEEPSEEK_API_KEY=...
export TAVILY_API_KEY=...
export DESEARCH_API_KEY=...    # optional

# NeoFS (enable uploads)
export NEOFS_BASE_URL=...
export NEOFS_OWNER_ADDRESS=...
export NEOFS_PRIVATE_KEY_WIF=...
export NEOFS_CONTAINER_ID=...
export NEOFS_GATEWAY_URL=...   # optional public link

# Social channels (optional)
export TWITTER_CONSUMER_KEY=...
export TWITTER_CONSUMER_SECRET=...
export TWITTER_ACCESS_TOKEN=...
export TWITTER_ACCESS_TOKEN_SECRET=...
export TWITTER_USER_ID=...
export TELEGRAM_BOT_TOKEN=...
```

AlphaSanta-specific toggles:

```bash
export ALPHASANTA_LLM_PROVIDER=anthropic
export ALPHASANTA_LLM_MODEL=claude-haiku-4-5-20251001
export ALPHASANTA_QUEUE_MAXSIZE=0
export ALPHASANTA_RATE_LIMIT_PER_MIN=60
export ALPHASANTA_DATABASE_URL=sqlite:///alphasanta.db
# Switch to remote A2A AgentCards (requires google-a2a SDK)
export ALPHASANTA_ELF_TRANSPORT=a2a
export ALPHASANTA_A2A_MICRO_URL=http://localhost:13000
export ALPHASANTA_A2A_MOOD_URL=http://localhost:13001
export ALPHASANTA_A2A_MACRO_URL=http://localhost:13002
export ALPHASANTA_A2A_TIMEOUT_SECONDS=45
```

## Running the Council Locally

Use the direct CLI runner when you want a one-shot evaluation from the command line:

```bash
alphasanta-start --token BTC/USDT --thesis "ETF inflows accelerating"
```

The script prints each elf's structured report and Santa's final decision. `decision.meta.timeline`
captures every orchestration cue (letter received, elf dispatch/return, Santa synthesis) for frontend
visualizations. NeoFS/social posting respect the environment toggles (`ALPHASANTA_NEOFS_ENABLED`, etc.).

## AgentCard Servers

Launch individual agents:

```bash
alphasanta-micro-card --port 12001
alphasanta-mood-card  --port 12002
alphasanta-macro-card --port 12003
alphasanta-santa-card --port 12010
```

Or run all four AgentCard services together (default ports: 13000/13001/13002/13010):

```bash
alphasanta-run-all-cards
```

Each AgentCard expects a JSON payload like:

```json
{
  "token": "BTC/USDT",
  "thesis": "ETF supply crunch narrative",
  "source": "community"
}
```

Submit via any AgentCard-compatible client; the response contains the structured `ElfReport` (for elves) or `SantaDecision` (for Santa).

## Testing

Run the lightweight unit tests:

```bash
pytest tests
```

These tests focus on payload shapes and orchestration logic. They do not call external LLMs or APIs.

## NeoFS Upload Workflow

1. Configure `NEOFS_*` variables and ensure the container exists.
2. Enable NeoFS via `--neofs` for Santa (CLI or AgentCard).
3. On publish decisions, metadata and reports are uploaded. The resulting `object_id` and optional gateway link are stored in the decision payload.

## AlphaElf Always-On Mode

`AlphaElf` can be wired into automation to keep Santa active when community input is quiet. Provide your proprietary signal when calling Santa via `alphasanta-start --alpha-signal "..."`; Santa treats it as a special source and can publish after a single round of evaluation.

## Queue Worker (Optional)

Run a dedicated queue that feeds input to Santa sequentially.
Producers (AgentCards, schedulers, AlphaElf) call the queue helpers exposed via `AlphaSantaApplication`.

```bash
python -m alphasanta.cli.queue_worker  # future integration point
```

The queue guarantees FIFO processing; see `alphasanta/orchestrator/queue.py` for
custom integration hooks (e.g., result callbacks to persist outcomes).

### Wallet binding & Turnkey

- Frontend should associate each submission with a wallet address (and optional user ID).
- Populate `UserLetter.wallet_address` via the submission payload; it will be persisted alongside elf reports and Santa decisions.
- When Turnkey credentials (`TURNKEY_*`) are present, use `alphasanta.services.TurnkeyService` to verify signatures or trigger custodial actions.
- Persistence is handled via SQLite by default (`ALPHASANTA_DATABASE_URL`), but you can point it to a remote database in production.
