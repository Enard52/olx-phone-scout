# Design

## Context

See proposal.md - Why. `main.py` runs scrape → recategorize → analyze and already prints the top 5 from the
analyzer result; the session directory (`config.get_session_dir()`) is named after the run's settings, which is
the natural scope for "already sent".

## Goals / Non-Goals

**Goals:** one flag that makes any scheduled run useful; safe to run unattended.

**Non-Goals:** a built-in scheduler or daemon; other channels (email, Slack); per-user subscriptions; price-drop
alerts on listings already sent.

## Decisions

- **Telegram Bot API over httpx** (`POST https://api.telegram.org/bot<token>/sendMessage`). Alternative:
  `python-telegram-bot`. Rejected: one endpoint does not justify a dependency.
- **Plain text, no `parse_mode`.** Listing titles carry `*`, `_` and `<`; Markdown or HTML mode would need
  escaping and fail on a missed character. Telegram auto-links bare URLs.
- **State in `<session>/alerts_sent.json`**, a list of links written atomically (temp file + rename) after each
  accepted message. Alternative: a table in a global SQLite. Rejected: the state is per session and small.
- **Top 10, constant `ALERT_TOP_N` in `src/core/constants.py`.** The report has 50; ten keeps a daily message
  readable.
- **Scheduling is documented, not built:** a systemd user timer (`OnCalendar=*-*-* 09:00`, `Persistent=true` to
  catch up after sleep) and an equivalent cron line, both calling `./run.sh --notify`.
- **Token never logged:** errors log the HTTP status and Telegram's `description`, not the URL (it contains the
  token).

## Risks / Trade-offs

- [The first `--notify` run sends the whole current top 10] → acceptable and bounded by `ALERT_TOP_N`.
- [A listing that drops out of the top and returns is not re-sent] → intended: "new" means never sent.
- [OLX blocks the unattended run (403)] → the run fails as today, nothing is sent; the log shows why.

## Migration Plan

Opt-in flag, no migration. Rollback = drop the flag from the timer.
