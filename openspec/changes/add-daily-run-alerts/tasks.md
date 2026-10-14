# Tasks

## 1. Notifier

- [ ] 1.1 Add `ALERT_TOP_N = 10` and `TELEGRAM_MAX_MESSAGE_LEN = 4096` to `src/core/constants.py`, and `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` to `.env.example`; verify `uv run pytest tests/test_config.py` passes
- [ ] 1.2 Add sent-links state per session (`alerts_sent.json`, atomic write); verify a test that links persist across two loads and sessions do not share state
- [ ] 1.3 Add selection of new top listings (top `ALERT_TOP_N`, minus sent links); verify tests for "two new" and "nothing new"
- [ ] 1.4 Add message formatting (title, price, score, link; plain text) and splitting under 4096 chars without cutting a listing; verify a test with ten long titles
- [ ] 1.5 Add the Telegram send over httpx; verify tests with `httpx.MockTransport` for 200 (links recorded), 4xx/5xx and network error (nothing recorded, no exception, token absent from logs)

## 2. Pipeline

- [ ] 2.1 Add `--notify` to `main.py` and call the notifier after the analyze step; verify a test that without the flag no request is made and a missing token only warns (exit status unchanged)
- [ ] 2.2 Real check: with a test bot token and chat id in `.env`, run `./run.sh --analyze --notify` twice on an existing session; the first run sends the top 10, the second sends nothing

## 3. Docs

- [ ] 3.1 Add a "Daily runs" section to README.md and README.ru.md with the systemd user timer and the cron line; add `--notify` to CLAUDE.md "Common Operations" and a CHANGELOG entry
- [ ] 3.2 Run `uv run pytest`, `uv run ruff check .`, `uv run mypy src` and `openspec validate add-daily-run-alerts --strict`; all pass
