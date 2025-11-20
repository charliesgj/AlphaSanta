# AlphaSanta Usage Guide

## Installation

Clone the repo, enter it, and install all dependencies (including Spoon Toolkits/Twitter/Telegram tooling) in one shot:

```bash
git clone <repo-url>
cd AlphaSanta
pip install -e .
```

> 从 v0.1.0 起，AgentCard/A2A 依赖默认就包含在核心安装里，不再需要额外的可选 extras。

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

# Supabase persistence
export SUPABASE_URL=...
export SUPABASE_ANON_KEY=...
export SUPABASE_SERVICE_ROLE_KEY=...  # backend worker requires service role privileges
# Map each elf/santa identifier to its agents.agent_id UUID
export ALPHASANTA_AGENT_ID_MAP="micro:uuid,mood:uuid,macro:uuid,santa:uuid"

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
alphasanta-start --token BTC/USDT --thesis "ETF inflows accelerating" --user-id demo-user
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
  "user_id": "demo-user-123",
  "source": "community"
}
```

Submit via any AgentCard-compatible client; the response contains the structured `ElfReport` (for elves) or `SantaDecision` (for Santa).

## Task Workflow & Queueing

When integrating with your own backend/API:

1. Collect `token`, `thesis`, and `user_id` from the frontend.
2. Call `AlphaSantaApplication.submit_letter(UserLetter(...))`; it creates a Supabase `submissions` row with status `pending`, returns the `submission_id`, and enqueues the work.
3. SantaQueue runs tasks sequentially. For each task Santa plans missions for Micro/Mood/Macro (based on the thesis), gathers their "Elf's response" JSON, averages confidences into `SantaScore`, and emits `pass/not_pass`.
4. Once all elves plus Santa finish, `submissions` is updated to `completed`, the final JSON (missions, elf responses, Santa decision) is stored in `result`, and one row per agent is written to `submission_agents` (only after Santa finishes, as required for downstream analytics).

Use the returned `submission_id` to show pending entries in the UI and to poll for completion.

For quick manual verification (including Supabase writes), use:

```bash
python scripts/manual_submit.py --token BTC/USDT --thesis "Momentum building" --user-id demo-user
```

The script queues a submission, prints the `submission_id`, waits for Santa to finish, and exits once the queue drains.

### Processing pending Submissions from Supabase

If your frontend writes directly into the Supabase `submissions` table, run the long-lived worker so each pending row gets processed:

```bash
alphasanta-process-submissions --interval 3
```

The worker polls for `status = pending`, marks it as `processing`, runs Santa, and writes the final payload + `submission_agents` rows. It requires the `SUPABASE_SERVICE_ROLE_KEY` so it can bypass RLS.

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

## Supabase Persistence & User Binding

Every deployment writes submissions and per-agent outputs to the Supabase schema
(`users`, `agents`, `submissions`, `submission_agents`, `evaluations`). The runner:

1. Inserts a pending row into `submissions` as soon as `submit_letter` is called.
2. Once Santa finishes, the same row is updated with `agent_confidence`, `santa_score`, `santa_decision`,
   the summarized analysis, and a `result` JSON containing missions, elf responses, and Santa's verdict.
3. Exactly one row per elf plus Santa is written to `submission_agents` (after completion) using UUIDs from
   `ALPHASANTA_AGENT_ID_MAP` so downstream analytics can compare each agent to Santa's final call.

- Frontend should associate each submission with a `user_id`. If you still need to attach a wallet, place it inside
  `UserLetter.metadata["wallet_address"]`.
- Ensure `.env` (or AWS Secrets on EC2) includes `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `ALPHASANTA_AGENT_ID_MAP`
  so every elf/Santa run maps to the correct `agents.agent_id`.
