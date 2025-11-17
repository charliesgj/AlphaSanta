 AlphaSanta quick reference (English)

  - Purpose
    AlphaSanta builds on Spoon Core/Toolkits to run a multi-elf analysis council
    and a Santa decision agent for crypto “alpha.” The pipeline is: elves
    (Micro/Mood/Macro) → council → Santa → NeoFS/social broadcasting, plus a
    direct AlphaElf path.
  - Core package layout (alphasanta/)
      - agents/: MicroElf, MoodElf, MacroElf, AlphaElf inherit from ElfAgent
        and use Spoon Toolkits/Tavily/Desearch; AlphaElf handles proprietary
        signals.
      - santa/: SantaCoordinator runs elf tasks concurrently and returns a
        CouncilResult; SantaAgent consumes council or alpha input, persists
        results, uploads to NeoFS, posts to social channels, and optionally tags
        Turnkey use.
      - services/:
          - DisseminationService: NeoFS upload with retries + Twitter/Telegram.
          - PersistenceService: SQLite by default (configurable via
            ALPHASANTA_DATABASE_URL).
          - TurnkeyService: lazy wrapper around spoon_ai.turnkey.Turnkey.
      - orchestrator/:
          - ElfRunner: single agent instance with async lock to avoid
            reinitializing tool stacks.
          - SantaQueue: queues UserLetter submissions (full council) or
            alpha-only requests, with optional HealthMonitor and per-wallet
            RateLimiter.
      - app/: AlphaSantaApplication wires agents, queue, dissemination,
        persistence, Turnkey; reused by CLI and AgentCard entrypoints.
      - infra/monitoring.py: health snapshot and sliding-window rate limiter.
      - schema.py: UserLetter (token/thesis/wallet/user/source),
        CouncilResult, ElfReport, SantaDecision.
  - Configuration (alphasanta/config.py)
    Reads .env/environment variables (via python-dotenv):
      - LLM & tools: ALPHASANTA_LLM_PROVIDER, ALPHASANTA_LLM_MODEL,
        DEEPSEEK_API_KEY, TAVILY_API_KEY, DESEARCH_API_KEY, etc.
      - Storage/Queue: ALPHASANTA_QUEUE_MAXSIZE, ALPHASANTA_RATE_LIMIT_PER_MIN,
        ALPHASANTA_DATABASE_URL.
      - NeoFS: NEOFS_BASE_URL, NEOFS_OWNER_ADDRESS, NEOFS_PRIVATE_KEY_WIF,
        NEOFS_CONTAINER_ID, NEOFS_GATEWAY_URL.
      - Social media: TWITTER_*, TELEGRAM_BOT_TOKEN.
      - Turnkey: TURNKEY_*.
  - Entry points (pyproject.toml project.scripts)
      - alphasanta-start: single-run CLI using
        AlphaSantaApplication.run_single_letter (`alphasanta-run-council`
        remains as a deprecated alias).
      - alphasanta-micro-card / ...-mood-card / ...-macro-card / ...-santa-card:
        start AgentCard services.
      - alphasanta-run-all-cards: launches all four AgentCard servers, sharing
        one application instance.
      - All CLI scripts reuse the same AlphaSantaApplication; you do NOT spin up
        new agents per request.
  - Data flow
      1. Frontend submits UserLetter (token/thesis + wallet).
      2. AlphaSantaApplication.submit_letter enqueues the work; SantaQueue
         dispatches to SantaAgent.process_letter which orchestrates elves via
         the configured transport (local runners or A2A).
      3. AlphaSantaApplication.submit_alpha enqueues direct alpha tasks with
         SantaAgent.process_alpha_only.
      4. Santa decisions are persisted (SQLite by default), optionally uploaded
         to NeoFS and broadcast on social channels.
      6. Turnkey integration is optional; decisions include metadata noting
         whether Turnkey is enabled.
      - Every SantaDecision.meta now includes a `timeline` list describing each
        workflow cue (letter read, elf dispatch/return, Santa synthesis) to
        drive frontend animations.
  - Testing
      - pytest on tests/ covers schema, Santa parsing, queue order, transport
        behavior, dissemination retries (NeoFS test skipped if pydantic
        missing).
      - tests/conftest.py adds the repo root to sys.path.
  - Deployment suggestions
      - Run a long-lived process for AgentCard/HTTP endpoints (re-using
        AlphaSantaApplication).
      - Run queue workers (same process or separate) that feed Santa
        sequentially.
      - Point ALPHASANTA_DATABASE_URL to a managed DB in production (e.g.,
        Postgres).
      - Configure rate limiting per wallet and add health checks via
        AlphaSantaApplication.health().
      - Ensure .env is complete with DeepSeek/Tavily/NeoFS credentials; no need
        to modify core Spoon files.
  - Open extension points
      - Add a REST API (FastAPI/Starlette) for submissions and status queries.
      - Implement wallet signature verification / deeper Turnkey workflows.
      - Enhance logging/monitoring (Prometheus, distributed tracing).
      - Expand persistence for scoring/metrics dashboards.
      - Consider distributed queue (Redis/Kafka) if scaling beyond a single
        worker.
