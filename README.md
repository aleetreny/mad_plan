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

Simulate the scheduled daily trigger:

```bash
python tools/daily_trigger.py
```

Run the same trigger in explicit fast mode for local smoke tests:

```bash
python tools/daily_trigger.py --fever-mode fast --trigger-source local-smoke
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
- `outputs/pipeline_diario.json`

`outputs/eventos_madrid_all.json` and `outputs/noticias_madrid_all.json` are the web-ready feeds.

## Normalized Contract

All source outputs now keep their original source fields and also expose a shared normalized layer for the web.

Shared plan fields used by the web:
- `id`, `fuente`, `fuente_id`, `tipo`, `slug`
- `titulo`, `subtitulo`, `resumen`, `descripcion`, `contenido`
- `categorias`, `categoria_principal`, `etiquetas`, `autor`
- `url`, `url_articulo`, `url_compra`, `imagen`
- `lugar`, `direccion`, `latitud`, `longitud`
- `precio`, `moneda`, `es_gratis`
- `modo_fecha`, `estado_temporal`
- `fecha_inicio`, `fecha_fin`, `datetime_inicio`, `datetime_fin`
- `proxima_fecha`, `proximo_datetime`, `sort_datetime`, `vigente_hasta`
- `fechas_disponibles`, `sesiones`
- `publicado_en`, `actualizado_en`, `scraped_en`, `timezone`, `metadata`

Shared news fields used by the web:
- `id`, `fuente`, `fuente_id`, `tipo`, `slug`
- `titulo`, `subtitulo`, `resumen`, `descripcion`, `contenido`
- `categorias`, `categoria_principal`, `etiquetas`, `autor`
- `url`, `imagen`
- `publicado_en`, `actualizado_en`, `sort_datetime`
- `estado_temporal`, `scraped_en`, `timezone`, `metadata`

Date semantics for plans:
- `fecha_inicio` / `fecha_fin`: normalized local dates for the plan window.
- `datetime_inicio` / `datetime_fin`: only populated when the source carries a real hour.
- `modo_fecha`: `puntual`, `puntual_con_hora`, `rango`, `multiple`, `sin_fecha`.
- `proxima_fecha` / `proximo_datetime`: next relevant date used to sort the feed for the web.
- `sesiones`: normalized future-facing session list; long recurring histories are trimmed so the web only sees relevant upcoming dates.

## Notes

- Event sources keep the shared event schema used by the repo.
- News sources are saved separately to support a dedicated news view.
- Scrapers live in `tools/` and generated JSON lives in `outputs/`.
- `tools/timeout.py` boots a browser session with Playwright before scraping, because Time Out blocks plain HTTP clients.
- `tools/timeout.py` is tuned for a daily recent-news feed: it scans only the latest sitemap months and keeps the last `21` days of news.
- `tools/madrid_secreto.py` is tuned for a daily plans feed: it keeps active/future plans up to `365` days ahead, plus undated editorial plans refreshed in the last `45` days.
- `tools/daily_trigger.py` is the scheduled entry point and now defaults to full Fever mode.
- The nightly GitHub Actions workflow lives in `.github/workflows/nightly_scrape.yml` and runs the scheduled trigger with `MAD_PLAN_FEVER_MODE=full`.
- GitHub Actions `schedule.cron` is expressed in UTC. The workflow is configured at `0 1 * * *`, which is an overnight run for Madrid.
- Fast Fever mode is still available as an explicit override for local smoke tests via `--fever-mode fast` or `MAD_PLAN_FEVER_MODE=fast`.
- `STATUS.md` is the running project log and should be updated on each prompt.