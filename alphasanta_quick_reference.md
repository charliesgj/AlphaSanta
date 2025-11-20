 AlphaSanta quick reference (English)

  - Purpose
    AlphaSanta builds on Spoon Core/Toolkits to run a Santa mission planner
    and three specialist elves (Micro/Mood/Macro). The pipeline is: user letter
    → Santa plans missions → elves respond → Santa averages/confirms → NeoFS/social + DB.
  - Core package layout (alphasanta/)
      - agents/: MicroElf, MoodElf, MacroElf inherit from ElfAgent and use
        Spoon Toolkits/Tavily/Desearch to generate technical/sentiment/macro intel.
      - santa/: SantaAgent plans missions, aggregates elf responses, scores the
        submission, uploads to NeoFS, and emits a final verdict.
      - services/:
          - DisseminationService: NeoFS upload with retries + Twitter/Telegram.
          - PersistenceService: writes to Supabase (`SUPABASE_URL` +
            `SUPABASE_ANON_KEY`) and requires `ALPHASANTA_AGENT_ID_MAP`.
      - orchestrator/:
          - ElfRunner: single agent instance with async lock to avoid
            reinitializing tool stacks.
          - SantaQueue: queues submissions with optional HealthMonitor and
            per-user RateLimiter; every task carries a submission_id.
      - app/: AlphaSantaApplication wires agents, queue, dissemination, persistence;
        reused by CLI and AgentCard entrypoints.
      - infra/monitoring.py: health snapshot and sliding-window rate limiter.
      - schema.py: UserLetter (token/thesis/user/source + metadata), ElfReport,
        SantaDecision.
  - Configuration (alphasanta/config.py)
    Reads .env/environment variables (via python-dotenv):
      - LLM & tools: ALPHASANTA_LLM_PROVIDER, ALPHASANTA_LLM_MODEL,
        DEEPSEEK_API_KEY, TAVILY_API_KEY, DESEARCH_API_KEY, etc.
      - Storage/Queue: ALPHASANTA_QUEUE_MAXSIZE, ALPHASANTA_RATE_LIMIT_PER_MIN.
      - NeoFS: NEOFS_BASE_URL, NEOFS_OWNER_ADDRESS, NEOFS_PRIVATE_KEY_WIF,
        NEOFS_CONTAINER_ID, NEOFS_GATEWAY_URL.
      - Social media: TWITTER_*, TELEGRAM_BOT_TOKEN.
      - Supabase: SUPABASE_URL, SUPABASE_ANON_KEY, ALPHASANTA_AGENT_ID_MAP
        (maps elf IDs → agents.agent_id UUIDs).
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
      1. Frontend sends token/thesis/user_id; `PersistenceService.create_submission`
         writes a pending row and returns the submission_id.
      2. Submission (letter + metadata + submission_id) is enqueued; SantaQueue
         drains FIFO and calls `SantaAgent.process_letter`.
      3. Santa plans tailored missions per elf, dispatches via local runners or
         A2A, and gathers each elf's response JSON.
      4. Santa averages confidences → SantaScore, sets pass/not_pass, stores
         `elf_responses` + missions + Santa decision in Supabase, and updates
         `submission_agents` rows (one per elf + Santa) once the run completes.
      - `SantaDecision.meta.timeline` captures mission dispatch + synthesis for
        frontend playback.
  - Testing
      - pytest on tests/ covers schema, Santa parsing, queue order, transport
        behavior, dissemination retries (NeoFS test skipped if pydantic
        missing).
      - tests/conftest.py adds the repo root to sys.path.
  - Deployment suggestions
      - Run a long-lived process for AgentCard/HTTP endpoints (re-using
        AlphaSantaApplication).
      - Run queue workers (same process or separate) that feed Santa sequentially.
      - Configure rate limiting per user and add health checks via
        AlphaSantaApplication.health().
      - Ensure .env is complete with DeepSeek/Tavily/NeoFS credentials; no need
        to modify core Spoon files.
  - Open extension points
      - Add a REST API (FastAPI/Starlette) for submissions and status queries.
      - Enhance logging/monitoring (Prometheus, distributed tracing).
      - Expand persistence for scoring/metrics dashboards.
      - Consider distributed queue (Redis/Kafka) if scaling beyond a single
        worker.
