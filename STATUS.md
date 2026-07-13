# STATUS

Última revisión: 2026-07-13 (overhaul de producto final).

## Estado del producto

- **Pipeline**: 22 scrapers en `tools/`, orquestados por `tools/scrape_all.py` en
  subprocesos aislados con timeout duro, un reintento y conservación del último
  output bueno por fuente. El merge aplica dedupe multi-fuente, categorías
  normalizadas (18 canónicas), geocoding cacheado (Nominatim, máx. 150 lookups
  nuevos por ejecución) y emite feeds web slim y minificados.
- **Frontend** (`frontend_new/`, React + Vite + Tailwind 4): tres vistas (Planes,
  Mapa, Noticias) con buscador, filtros por fecha/categoría/fuente/zona (la zona
  filtra por distancia geográfica real), quiz de preferencias, agenda persistente,
  modal con "cómo llegar" y "añadir al calendario", y tema por franja horaria.
- **Imágenes**: foto real de la fuente cuando existe; cover determinista por
  categoría (gradiente + icono) cuando falta, falla o tarda >8 s. Se eliminaron
  los placeholders de Unsplash.
- **Automatización**: workflow diario de GitHub Actions (04:15 UTC) con tope de
  45 min y peor caso ~1.400 min/mes, dentro del presupuesto de GitHub Pro
  (3.000 min/mes). Commitea `eventos_web.json`, `noticias_web.json`,
  `pipeline_diario.json` y `geocode_cache.json`; los outputs por fuente se
  conservan entre ejecuciones con `actions/cache`.

## Última auditoría de fuentes (2026-07-13)

Todas las fuentes verificadas contra la web real:

| Fuente | Estado | Notas |
| --- | --- | --- |
| matadero, teatros_canal, circulo_bellas_artes, ifema, casa_mexico, telefonica, sala_el_sol | OK | volumen normal |
| museo_reina_sofia, biblioteca_nacional, fundacion_canal, fundacion_mapfre | OK | poca agenda en verano (1-8 items reales) |
| fever, eventbrite, wegow, ticketmaster, datos_madrid, rockthesport, meetup | OK | volumen alto |
| esmadrid | ARREGLADO | timeouts intermitentes → reintentos con backoff y descubrimiento tolerante a fallos |
| madrid_secreto | ARREGLADO | tardaba >10 min por renders de Playwright → render opcional vía `MAD_PLAN_RENDER_IMAGES` |
| timeout, gacetin_madrid (noticias) | OK | ~170 noticias recientes |

## Decisiones de producto vigentes

- Fuentes primarias de venue por delante de agregadores; los agregadores se
  quedan solo si su merge real enriquece precio, fecha, venue o categoría.
- Toda nueva fuente entra por `normalize_plan_records` y se juzga por su merge
  frente a Fever, Eventbrite, datos.madrid y Madrid Secreto.
- Candidatas de segunda ola: La Casa Encendida, CaixaForum Madrid.
- Descartadas tras validación: Sapos y Princesas, Somos Madrid, somoschueca.com,
  madridfree.com, madriddiario.es, guiadelocio.com, verydiferente.com.

## Cómo verificar

1. `python tools/scrape_all.py` (pipeline completo) o `--merge-only` para rehacer feeds.
2. `cd frontend_new && npm run build`
3. `python serve.py` → http://127.0.0.1:8000
4. `python tools/smoke_frontend.py` (E2E con Playwright).
