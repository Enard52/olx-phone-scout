# Proposal

## Why

Good deals on OLX.kz go within hours, and today someone has to remember to run `./run.sh` and read the report.
The roadmap lists "Automated daily runs with alerts"; the pipeline already ranks listings, it only lacks a way
to tell the user when a new one enters the top.

## What Changes

- New `--notify` flag: after the analysis, listings that entered the top N since the last notification are sent
  to a Telegram chat.
- The links already sent are remembered per session, so a daily run only reports what is new.
- A failed or unconfigured notification never fails the run; unsent listings are retried next time.
- README gets a scheduling section with a systemd user timer and a cron line. No scheduler is built in.

## Capabilities

### New Capabilities
- `deal-alerts`: picking new top listings after a run, sending them to Telegram, and remembering what was sent.

### Modified Capabilities
<!-- none: openspec/specs/ is empty -->

## Impact

- `main.py` (flag, call after the analyze step), a new notifier module, `src/core/constants.py`.
- `.env.example`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
- Per-session state file `alerts_sent.json` in the session directory (git-ignored with `data/`).
- No new dependencies: the Bot API is called with httpx, already a dependency.
