# Spec Delta

## Purpose

Lets a scheduled run tell the user about new good deals: after the analysis, listings that newly entered the
top of the ranking are sent to a Telegram chat once.

## ADDED Requirements

### Requirement: Notify about new top listings
When run with `--notify`, the system SHALL, after the analysis step, send to the configured Telegram chat every
listing in the top 10 of the ranking whose link has not been sent before for the same session. Each listing in
the message SHALL show its title, price in KZT, value score and link.

#### Scenario: Two new listings in the top
- **WHEN** a run with `--notify` ranks 10 listings and 8 of their links were sent in earlier runs of this session
- **THEN** one Telegram notification lists the other 2 listings with title, price, score and link

#### Scenario: Nothing new
- **WHEN** every top-10 link was already sent for this session
- **THEN** no Telegram message is sent

#### Scenario: Without the flag
- **WHEN** the pipeline runs without `--notify`
- **THEN** no Telegram request is made and nothing is recorded as sent

### Requirement: Remember sent listings per session
The system SHALL record a listing's link as sent only after Telegram accepted the message containing it, and
SHALL keep this record per session, so sessions with different settings notify independently.

#### Scenario: Different sessions
- **WHEN** a link was sent for session `alma-ata_90k-380k_android`
- **THEN** a run of session `alm_15k-80k_both` still sends it if it is in that session's top 10

### Requirement: Notification failures do not fail the run
If the Telegram token or chat id is missing, or Telegram rejects or does not answer the request, the system
SHALL log a warning without the token, finish the pipeline with its normal exit status, and leave the affected
links unrecorded so the next run retries them.

#### Scenario: Token not configured
- **WHEN** `--notify` is passed and `TELEGRAM_BOT_TOKEN` is not set
- **THEN** the run completes successfully, a warning names the missing variable, and no link is recorded as sent

#### Scenario: Telegram unavailable
- **WHEN** the Telegram request fails with a network error or a non-2xx status
- **THEN** the run completes successfully and the same listings are offered again on the next run

### Requirement: Long notifications are split
The system SHALL split a notification into several messages when it exceeds Telegram's 4096-character limit,
without cutting a listing across two messages.

#### Scenario: Ten long titles
- **WHEN** the new listings' text totals more than 4096 characters
- **THEN** they are sent as several messages, each under the limit, with every listing whole in one message
