# Madrid Plan Scrapers

Small scraping toolkit for a Madrid events and news aggregator.

Current sources:
- Fever
- Eventbrite
- datos.madrid.es
- Madrid Secreto (plans)
- Time Out Madrid (news)

## Setup

Create the environment if needed:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Run

Run all scrapers:

```bash
python tools/scrape_all.py
```

Run a single source:

```bash
python tools/fever.py
python tools/eventbrite.py
python tools/datos_madrid.py
python tools/madrid_secreto.py
python tools/timeout.py
```

## Outputs

- `outputs/eventos_fever.json`
- `outputs/eventos_eventbrite.json`
- `outputs/eventos_datos_madrid.json`
- `outputs/eventos_madrid_secreto.json`
- `outputs/eventos_madrid_all.json`
- `outputs/noticias_timeout.json`
- `outputs/noticias_madrid_all.json`

## Notes

- Event sources keep the shared event schema used by the repo.
- News sources are saved separately to support a dedicated news view.
- Scrapers live in `tools/` and generated JSON lives in `outputs/`.
- `tools/timeout.py` boots a browser session with Playwright before scraping, because Time Out blocks plain HTTP clients.
- `tools/timeout.py` is tuned for a daily recent-news feed: it scans only the latest sitemap months and keeps the last `21` days of news.
- `tools/madrid_secreto.py` is tuned for a daily plans feed: it keeps active/future plans up to `365` days ahead, plus undated editorial plans refreshed in the last `45` days.
- `STATUS.md` is the running project log and should be updated on each prompt.