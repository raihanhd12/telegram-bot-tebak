You are an expert full‑stack developer. Build a complete, tested, deployable Telegram "Tebak Kata" (guess-the-word) bot using Python. Deliver a Git repo with clear commits, docs, and deployment setup. Do not commit any secrets. Ask before I share any tokens or server credentials.

Requirements:
- Tech stack: Python 3.10+, python-telegram-bot v20+, python-dotenv, SQLite for persistence. Use async handlers.
- Features:
  - Commands: /tebak (start), /skip, /skor (leaderboard), /hint (optional), /addsoal (admin add question).
  - Per-chat active game state. Only one active question per chat.
  - Correct answers award points stored per user+chat. Leaderboard returns top 5.
  - Timeout: active question expires after 60 seconds.
  - Hint reduces points and reveals a character or word length.
  - Admin-only commands protected by chat admin check.
  - Load questions from JSON and allow adding via command while validating input.
- Nonfunctional:
  - Write unit tests for game logic and DB functions.
  - Provide Dockerfile and a simple docker-compose for local dev.
  - Provide CI config (GitHub Actions) that runs lint and tests.
  - Provide README with setup, env vars, run, and deploy steps.
  - Provide sample .env.example (no real tokens).
  - Use logging and handle errors gracefully.
- Deliverables:
  - Git repo with code, tests, Dockerfile, .env.example, README, and deployment instructions for Railway.
  - A single script to initialize DB (if needed).
  - Instructions to run locally and to deploy on Railway with environment variables.
- Security and ops:
  - Never write tokens into code or commit them. Use environment vars or secret manager.
  - If you need my BOT_TOKEN or GitHub access, request explicit permission and wait.
  - Provide step‑by‑step deploy and verification checklist I can follow to confirm bot works in my group.

Acceptance criteria:
- I can clone the repo, set BOT_TOKEN in .env, run docker-compose up and the bot responds to /tebak in a group where the bot is added.
- Tests pass in CI.
- README contains commands to promote the bot to admin and disable BotFather privacy setting.

Start by scaffolding the repo and implementing core game flow. After the core works, implement timeout, hint, admin add, tests, Dockerfile, and CI. Ask clarifying questions only if needed.