# MadPlan

Madrid events and news aggregation stack plus the static discovery frontend used to explore plans in Madrid.

Current sources:
- Fever
- Eventbrite
- datos.madrid.es
- Madrid Secreto (plans)
- Time Out Madrid (news)
- Matadero Madrid
- Teatros del Canal
- Círculo de Bellas Artes
- IFEMA Madrid
- Casa de México
- Espacio Fundación Telefónica
- Museo Reina Sofía
- Biblioteca Nacional
- Fundación Canal
- Fundación MAPFRE
- Sala El Sol
- Wegow
- Ticketmaster Madrid
- esMadrid Agenda
- Gacetín Madrid (news)
- RockTheSport (sports events)
- Meetup (community events)

## Setup

Create the environment if needed:

```bash
python -m venv .venv
# PowerShell
.venv\Scripts\Activate.ps1
# bash
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Run Data Pipeline (Backend)

Run all scrapers:

```bash
python tools/scrape_all.py
```

Then, run the processing pipeline to normalize and enhance the data:

```bash
# Merge feeds
python tools/rebuild_feeds.py
# Normalize categories to 18 canonical buckets
python tools/normalize_categories.py
# Geocode missing coordinates (safe/rate-limited)
python tools/geocode_events.py
# Fix missing photos with deterministic Unsplash placeholders
python tools/fix_missing_photos.py
```

## Run Frontend

```bash
cd frontend_new
npm install
npm run dev
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
python tools/rockthesport.py
python tools/meetup.py
```

Rebuild the merged web feeds from the existing per-source outputs without scraping again:

```bash
python tools/rebuild_feeds.py
```

## Frontend

Start the local dev server:

```bash
python serve.py
```

Then open http://127.0.0.1:8000 in a browser. The frontend reads from `outputs/` and shows:
- **Pulse-driven discovery**: day-part theming, quick filters like `Hoy`, `Esta noche`, `De mananeo`, `Al fresquito`, `Gratis total`, editorial shelves, search, shortlist saving, and shareable URL state.
- **Smart plan cards**: merged plans render once, compare multiple access links per source, show trust badges, and generate covers when an image is missing.
- **Madrid-native map view**: Leaflet map with marker clustering, barrio pulse cards, side list sync, and city-safe coordinate clipping so out-of-city points do not pollute the UI.
- **Radar cultural**: latest news from Time Out and Gacetin Madrid alongside the plan explorer.

Run the frontend smoke test:

```bash
python tools/smoke_frontend.py
```

## Outputs

- `outputs/eventos_fever.json`
- `outputs/eventos_eventbrite.json`
- `outputs/eventos_datos_madrid.json`
- `outputs/eventos_madrid_secreto.json`
- `outputs/eventos_madrid_all.json`
- `outputs/eventos_rockthesport.json`
- `outputs/eventos_meetup.json`
- `outputs/noticias_timeout.json`
- `outputs/noticias_madrid_all.json`
- `outputs/pipeline_diario.json`

`outputs/eventos_madrid_all.json` and `outputs/noticias_madrid_all.json` are the web-ready feeds.

Merged plan records also expose `metadata.source_links` so the frontend can compare official, aggregator, and editorial access links inside a single deduplicated card.

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
- `metadata.source_links`: merged access links kept per source, including URL, link kind, and price signal when available.

## Notes

- Event sources keep the shared event schema used by the repo.
- News sources are saved separately to support a dedicated news view.
- Scrapers live in `tools/` and generated JSON lives in `outputs/`.
- `tools/timeout.py` boots a browser session with Playwright before scraping, because Time Out blocks plain HTTP clients.
- `tools/timeout.py` is tuned for a daily recent-news feed: it scans only the latest sitemap months and keeps the last `21` days of news.
- `tools/madrid_secreto.py` is tuned for a daily plans feed: it keeps active/future plans up to `365` days ahead, plus undated editorial plans refreshed in the last `45` days.
- `tools/daily_trigger.py` is the scheduled entry point and now defaults to full Fever mode.
- `tools/rebuild_feeds.py` recomposes `eventos_madrid_all.json` and `noticias_madrid_all.json` from the latest source JSON files already present in `outputs/`.
- `tools/smoke_frontend.py` starts a temporary local server and validates the main frontend assets plus both merged JSON feeds.
- The public frontend brand is `MadPlan`; the repo still keeps the scraper and normalization stack that feeds it.
- The nightly GitHub Actions workflow lives in `.github/workflows/nightly_scrape.yml` and runs the scheduled trigger with `MAD_PLAN_FEVER_MODE=full`.
- GitHub Actions `schedule.cron` is expressed in UTC. The workflow is configured at `0 1 * * *`, which is an overnight run for Madrid.
- Fast Fever mode is still available as an explicit override for local smoke tests via `--fever-mode fast` or `MAD_PLAN_FEVER_MODE=fast`.
- `STATUS.md` is the running project log and should be updated on each prompt.