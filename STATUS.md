# STATUS

Última revisión: 2026-07-14 (web pública en GitHub Pages + fixes post-lanzamiento).

## Producción

- Web publicada: https://aleetreny.github.io/mad_plan/ (GitHub Pages, fuente
  "GitHub Actions"). Se redespliega con cada push a main y tras el scrape
  nocturno de las 04:15 UTC.
- Primer run nocturno en CI: OK (12,5 min, 19/22 fuentes). eventbrite,
  ticketmaster y biblioteca_nacional bloquean IPs de datacenter → pasan a
  cloudscraper y su último scrape bueno queda versionado como respaldo, así
  el feed no los pierde aunque CI no pueda scrapearlos.
- Fix post-lanzamiento: el modal de detalle se abría detrás del mapa
  (z-index de Leaflet vs overlays) — contenedor del mapa con `isolate` y
  overlays a z-1100/1200; reproducido en la web publicada y verificado.

## QA 2026-07-14 — fallos encontrados y corregidos

- **Fechas**: los planes de rango "en curso" se ordenaban por su fecha de
  clausura; la hora mostrada podía venir de una sesión ya caducada; los
  programas municipales eternos decían "hasta 2032"; los planes editoriales
  sin fecha decían "Fecha por confirmar" (ahora "Cuando quieras"); los eventos
  puntuales con hora sobrevivían hasta medianoche tras empezar (ahora caducan
  a las 3 h). `resolveEventDates` es ahora consciente de `modo_fecha`.
- **Mapa**: 137 eventos con dirección genérica apilados en Puerta del Sol
  (geocoding genérico eliminado y coords sin venue concreto anuladas); 67
  eventos con coordenadas fuera de Madrid (anuladas); venues con 50+ eventos
  bajo un marcador que solo abría uno (ahora un marcador por sitio con lista
  de planes en el popup).
- **Variedad**: ~320 tarjetas duplicadas fusionadas — mismo evento recurrente
  en fechas distintas (una tarjeta con sesiones), títulos reordenados o
  subconjunto el mismo día, variantes de nombre del mismo venue, duplicados
  inglés/español de Matadero (scraper filtra `/schedule/`); portada
  diversificada (máx. 2 tarjetas seguidas de la misma categoría).
- **Búsqueda**: insensible a acentos ("musica" = "música") y multi-palabra
  con AND ("jazz retiro").
- **Otros**: 147 títulos EN MAYÚSCULAS pasados a sentence-case; el quiz ya
  ordena resultados también con solo un vibe elegido; los destacados excluyen
  artículos editoriales sin fecha; contador de agenda coherente con los planes
  aún vigentes.

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
