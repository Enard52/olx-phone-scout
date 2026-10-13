# OLX Almaty Phone Analyzer

[![CI](https://github.com/octrow/olx-almaty-phone-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/octrow/olx-almaty-phone-analyzer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)

[English](README.md) | **Русский**

Консольная утилита, которая ищет самые выгодные б/у телефоны на OLX.kz. Она собирает все объявления в
заданном ценовом диапазоне и разбирает бренд и модель по неаккуратным заголовкам. Затем добавляет
характеристики с Kimovil, сравнивает цену с рыночной ценой модели и пишет отчёт с рейтингом.

Сделана для Алматы, но работает с любым регионом OLX.kz.

## Что умеет

- **Проходит весь ценовой диапазон.** OLX отдаёт не больше 1000 результатов на поиск, поэтому диапазон
  режется на ценовые срезы, пока каждый не уложится в этот лимит. Страницы загружаются параллельно,
  с паузами и повторами.
- **Понимает неаккуратные заголовки.** 22 бренда, кириллица и частые опечатки («xioami», «techno»,
  «poko», «z фолд»). Телефон, который хотят получить *в обмен* («обмен на iphone 13»), не считается
  продаваемым.
- **Добавляет характеристики с Kimovil.** Экран, процессор, AnTuTu, аккумулятор, зарядка и DxOMark.
  Кэшируются в SQLite между запусками.
- **Оценивает выгоду.** Скидка от рыночной цены (102 модели), год выпуска, класс, память, ОЗУ, камера
  и состояние. Неправдоподобные скидки ограничиваются, объявления из пригородов и от магазинов
  помечаются.
- **Необязательный AI-анализ.** Gemini, Cerebras или OpenRouter читают описание (и по желанию фото)
  и ищут дефекты и бонусы. Остальной пайплайн работает без API-ключей.

## Установка

Нужны Python 3.12+ и [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/octrow/olx-almaty-phone-analyzer.git
cd olx-almaty-phone-analyzer
uv sync
```

Для AI-анализа скопируйте `.env.example` в `.env` и впишите ключ нужного провайдера.

## Запуск

```bash
./run.sh                    # весь пайплайн: сбор → перекатегоризация → анализ
./run.sh --scrape           # только сбор с OLX
./run.sh --recategorize     # заново определить бренды у сохранённых объявлений
./run.sh --analyze          # только анализ сохранённых объявлений
./run.sh --show-config      # показать настройки и выйти
```

`./run.sh` — тонкая обёртка над `uv run main.py`, флаги у них одинаковые.

```bash
./run.sh --min-price 150000 --max-price 300000 --max-pages 10 --days-back 14
./run.sh --min-price 15000 --max-price 80000 --phone-type both   # Android + iPhone
./run.sh --location alm --include-business   # Алматы с областью, и магазины тоже (метки 📍 / 🏪)
./run.sh --gemini           # AI-анализ через Gemini (--gemini-photos, --gemini-top-n N)
./run.sh --cerebras         # или --openrouter
```

`--location` принимает слаг любого региона OLX.kz (`astana`, `shymkent`, `karaganda`, ...), список в `--help`.

## Результаты

Каждый запуск пишет в папку сессии, названную по настройкам, например
`data/sessions/alma-ata_90k-380k_android/`:

- `results/`: `all_listings.json`, `androids.json`, `iphones.json`, `unknown.json`,
  `androids_analyzed.json`, `TOP_50_ANDROID.json`
- `reports/TOP_RECOMMENDATIONS_{timestamp}.txt`: отчёт с рейтингом для чтения
- `logs/`: по логу на каждый шаг

Сокращённая запись из реального отчёта (15–80 тыс. ₸, Алматы с областью, проанализировано 6557 объявлений):

```
📱 iPhone 11 Pro Max (iPhone 11 Pro Max 256GB Gold)
💰 PRICE: 80,000 KZT
📅 RELEASE YEAR: 2019
📍 LOCATION: Гульдала - 27 сентября 2026 г.
⚠️  📍 OUTSIDE АЛМАТЫ: Гульдала, you'll need to travel

⭐ VALUE FACTORS:
   ⭐⭐⭐ Ultra Flagship
   💾 Good 256GB storage
   ✨ Excellent condition
   🔋 Excellent battery (95%+)
```

Характеристики Kimovil кэшируются для всех сессий в `data/cache/kimovil_specs.db`.

## Настройки

Значения по умолчанию лежат в `src/core/config.py`, флаги CLI их переопределяют.

| Параметр | По умолчанию |
|----------|--------------|
| `LOCATION` | `alma-ata` |
| `MIN_PRICE` / `MAX_PRICE` | 90 000 / 380 000 ₸ |
| `MAX_PAGES` | 25 на ценовой срез (максимум OLX) |
| `DAYS_BACK` | 25 |
| `PHONE_TYPE_FILTER` | `android` (`--phone-type android\|iphone\|both`) |
| `REQUEST_DELAY` | 1,5 с между запросами к OLX |

Темп запросов к Kimovil задан в `src/core/constants.py`: `KIMOVIL_MAX_CONCURRENT = 2`,
`KIMOVIL_REQUEST_DELAY = 2.5` с. Каждая модель запрашивается не больше одного раза за запуск.

## Как устроено

```
main.py
 ├─ scrape        страницы поиска OLX → all_listings.json      (src/core/async_scraper.py)
 ├─ recategorize  определение бренда и модели → androids/iphones/unknown.json   (src/detection/)
 └─ analyze       детали объявлений, Kimovil, оценка, AI по желанию → отчёт   (src/analysis/)
```

OLX и Kimovil закрыты защитой от ботов, которая смотрит на TLS-отпечаток, а не только на заголовки.
Запросы идут через [curl_cffi](https://github.com/lexiforest/curl_cffi) с отпечатком Chrome, паузы и
повторы берутся из [market-sources](https://github.com/octrow/market-sources). Страницы Kimovil
разбираются selectolax, браузер не нужен.

Заметки об архитектуре для контрибьюторов и coding-агентов — в [CLAUDE.md](CLAUDE.md).

## Если что-то не работает

- **OLX отвечает 403 на каждую страницу.** CloudFront блокирует по TLS-отпечатку. Попробуйте другую
  цель `IMPERSONATE` в `src/core/browser_transport.py` или обновите `curl_cffi`.
- **Kimovil отвечает 429 почти на все телефоны.** Это блокировка Cloudflare на ваш IP после всплеска
  запросов, а не обычный лимит. Подождите несколько часов и снова запустите `./run.sh --analyze`:
  найденные характеристики кэшируются, и каждый запуск добирает ещё.

## Ограничения

- Рыночные цены ведутся вручную (`src/analysis/market_data.py`, 102 модели).
- Только OLX.kz; текст объявлений ожидается на русском или казахском.

## Разработка

```bash
uv run pytest               # тесты (+ отчёт о покрытии в htmlcov/)
uv run ruff check . && uv run ruff format --check .
```

См. [CONTRIBUTING.ru.md](CONTRIBUTING.ru.md).

## Лицензия

[MIT](LICENSE)
