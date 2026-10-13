# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-13

First public release.

### Added
- Async OLX.kz scraper with automatic price slicing past OLX's 1000-result cap.
- Brand and model detection for 22 brands, with Cyrillic spellings and common typos.
- Kimovil spec enrichment over curl_cffi + selectolax, cached in SQLite across runs.
- Value scoring against hand-maintained market prices for 102 models.
- Optional AI analysis via Gemini, Cerebras or OpenRouter.
- Any OLX.kz region (`--location`), shops (`--include-business`), Android and iPhone (`--phone-type`).

[1.0.0]: https://github.com/octrow/olx-almaty-phone-analyzer/releases/tag/v1.0.0
