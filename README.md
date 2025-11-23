# AlphaSanta --Rebuild the Signal

alphasanta.com • https://docs.alphasanta.com

<img src="santa.png" width="160" alt="AlphaSanta mascot"/>

---

## Overview
AlphaSanta is an intelligence-coordination system designed to turn scattered signals into structured insight.

Rather than simply running agents, AlphaSanta **choreographs** them — routing tasks, capturing context, and assembling conclusions into a coherent decision pipeline.

At the center is the **Submission Worker**, responsible for:
- Reading incoming letters from Supabase
- Coordinating specialized Elf Agents
- Consolidating their perspectives
- Producing Santa’s final decision

The worker abstracts away multi-agent orchestration complexity and exposes a clean, predictable interface.

---

## Intelligent Orchestration
Every submission flows through a structured multi-agent decision cycle.

Technical elves, sentiment elves, macro elves, context elves — each contributes a focused angle of intelligence. Santa synthesizes these perspectives into one validated decision.

This transforms AlphaSanta from a simple tool into a growing ecosystem of cognitive capabilities.

---

## Future-Ready Communication Layer
AlphaSanta includes an extensible **A2A communication layer** inspired by Google ADK.

It currently operates in a controlled internal environment, but is engineered to eventually support:
- Remote agent collaboration
- External agent ecosystems
- Distributed intelligence networks

The infrastructure is quiet; the ambition is not.

---

## Vision
AlphaSanta’s long-term mission is to **elevate human judgment at scale**, not replace it.

By filtering noise, structuring context, and routing intelligence precisely where needed, AlphaSanta aims to evolve from "letter processing" into coordinated insight across entire ecosystems.

> Today it sorts letters. Tomorrow it sorts the world’s signals.

---

## Quick Links
- Website: https://alphasanta.com
- Docs: https://docs.alphasanta.com
- X: https://x.com/Your_AlphaSanta
- Telegram: https://t.me/AlphaSanta_Signals

---

## Prerequisites
- Python 3.12+

---

## Install
### Reproducible install (locked versions)
```bash
git clone <repo-url>
cd AlphaSanta
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.lock
```

### Editable install for local development
```bash
pip install -e .
```

---

## Configuration
Create a `.env` file in the repo root (or export these values):

```env
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

**Notes:**
- Keep quotes around `ALPHASANTA_AGENT_ID_MAP`.
- Set `ALPHASANTA_NEOFS_ENABLED=true` only when NeoFS credentials are valid.

---

## Running the Worker
Process pending Supabase submissions continuously:
```bash
alphasanta-process-submissions --interval 3
```

The worker will:
1. Poll `status=pending`
2. Mark items as `processing`
3. Dispatch all elves + Santa
4. Write consolidated results to `result`
5. Write per-agent outputs to `submission_agents`

---

## Testing
Run test suite:
```bash
pytest tests
```

Tests cover payload shapes and orchestration logic (no external API calls).