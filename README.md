# Telegram Bot Tebak Kata

Bot Telegram game tebak kata Bahasa Indonesia dengan soal dari LLM Agent API.

## Kenapa `src/bot` tidak digabung ke `app/services`?
Secara arsitektur, **sebaiknya tetap dipisah**.

- `src/bot` = interface/adaptor ke Telegram (transport layer).
- `src/app/services` = business logic murni (aturan game, skor, hint, validasi).

Kalau digabung, service jadi terikat ke Telegram SDK dan sulit di-reuse (misalnya nanti mau tambah Discord/Web/API). Jadi desain sekarang sudah tepat: handler tipis, logic berat di service.

## Fitur Utama
- Command game: `/start`, `/help`, `/tebak`, `/skip`, `/hint`, `/skor`
- Refresh bank soal dari LLM: `/refresh` (admin only)
- Kategori soal: `lucu` dan `mind_blowing`
- Satu game aktif per chat
- Timeout game
- Hint dengan penalty poin
- Leaderboard top pemain
- Persistensi data dengan SQLAlchemy + Alembic

## Arsitektur Singkat
- `src/bot/` -> handler Telegram
- `src/app/services/` -> use-case/game logic
- `src/app/repositories/` -> akses DB
- `src/app/models/` -> model SQLAlchemy
- `src/database/migrations/` -> skema DB (Alembic)

## End-to-End Flow

### 1) Flow `/tebak`
1. User kirim `/tebak [kategori]` di Telegram.
2. `CommandHandler` di `src/bot/handlers/commands.py` memanggil `GameService.start_game()`.
3. Service validasi kategori, cek game aktif, ambil soal fresh dari `QuestionRepository`.
4. Service membuat game baru + player/game_player bila perlu.
5. Bot balas soal acak (scrambled word), poin, kategori, durasi.

### 2) Flow jawaban text biasa
1. User kirim text biasa (bukan command).
2. `MessageHandler` di `src/bot/main.py` ambil game aktif per chat.
3. `GameService.submit_answer()` validasi jawaban.
4. Jika benar:
- update `game_players` (score, answered_at)
- update statistik `players` (score, streak, win)
- set game status `COMPLETED`
5. Bot kirim feedback benar/salah + poin.

### 3) Flow `/hint`
1. Handler panggil `GameService.use_hint()`.
2. Service cek game aktif, belum expired, dan limit hint.
3. Service naikkan `current_hint_count`, hitung penalty poin.
4. Bot kirim hint.

### 4) Flow `/refresh` (LLM)
1. Handler cek user admin group.
2. Handler panggil `LLMService.refresh_questions()`.
3. `LLMGenerateService` call endpoint:
   - `POST {LLM_URL}/api/v1/agents/{LLM_AGENT_ID}/execute`
   - Header: `x-api-key: {LLM_HEADER_API_KEY}` (service key)
   - Payload utama: `{ "user_prompt": "...prompt...", "api_key": "{LLM_MODEL_API_KEY}" }` (model key)
4. Response diparse, divalidasi, dinormalisasi.
5. Soal disimpan ke DB via `QuestionRepository.bulk_create_questions()`.
6. Bot kirim hasil jumlah soal yang berhasil ditambah.

## Struktur Folder
```text
.
├── main.py
├── src/
│   ├── bot/
│   │   ├── main.py
│   │   ├── handlers/
│   │   └── utils/
│   ├── app/
│   │   ├── models/
│   │   ├── repositories/
│   │   └── services/
│   │       ├── game/
│   │       └── llm/
│   ├── config/
│   └── database/
│       ├── session.py
│       └── migrations/
└── tests/
```

## Setup Lokal

### 1. Install dependency
```bash
poetry install
```

### 2. Siapkan environment
```bash
cp .env.example .env
```

Minimal isi variabel berikut di `.env`:
- `BOT_TOKEN`
- `DATABASE_URL`
- `GAME_TIMEOUT`
- `HINT_PENALTY`
- `MAX_HINTS`
- `MAX_USED_COUNT`

Untuk fitur refresh LLM:
- `LLM_URL`
- `LLM_API_KEY`
- `LLM_AGENT_ID`
- `LLM_REFRESH_COUNT`
- `LLM_REFRESH_COOLDOWN_SECONDS` (anti-spam `/refresh`, default 120 detik)

### 3. Jalankan migrasi
```bash
poetry run alembic upgrade head
```

### 4. Jalankan bot
```bash
poetry run python main.py
```

## Command Bot
- `/start-tebak` -> pesan pembuka
- `/help` -> panduan command
- `/tebak` -> mulai game (default kategori `lucu`)
- `/tebak lucu`
- `/tebak mindblowing`
- `/skip` -> lewati game aktif
- `/hint` -> minta hint
- `/skor` -> leaderboard
- `/refresh` -> generate soal dari LLM (admin)

## Testing dan Quality
```bash
poetry run pytest
poetry run ruff check src tests
poetry run black src tests
poetry run isort src tests
```

## Setup BotFather (Wajib untuk Group)
1. Buat bot di `@BotFather` (`/newbot`).
2. Ambil token lalu set ke `BOT_TOKEN`.
3. Nonaktifkan privacy mode (`/setprivacy` -> Disable).
4. Tambahkan bot ke group.
5. Promote bot jadi admin group.

## Catatan Operasional
- Jangan commit token/API key ke git.
- Handler Telegram harus tipis; logic utama tetap di service.
- Jika menambah env baru: update `src/config/env.py` + `.env.example` + README ini.
