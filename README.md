# MadPlan

La agenda de Madrid en un solo sitio: un pipeline de scraping que agrega 22 fuentes
(venues, agregadores, datos abiertos y medios) y una web para explorar los planes
con buscador, filtros, mapa, agenda personal y noticias.

## Cómo funciona

```
tools/*.py  (22 scrapers) ──► outputs/eventos_<fuente>.json   (por fuente)
                                        │
                       tools/scrape_all.py  (merge + dedupe)
                                        │
             ┌──────────────────────────┼──────────────────────────┐
   categorías normalizadas       geocoding cacheado         limpieza imágenes
             └──────────────────────────┼──────────────────────────┘
                                        ▼
             outputs/eventos_web.json + noticias_web.json   (feeds slim para la web)
             outputs/pipeline_diario.json                   (manifest de la ejecución)
```

- **Robustez**: cada scraper corre en su propio subproceso con timeout duro y un
  reintento. Si una fuente falla o devuelve vacío, se conserva su último output
  bueno y el resto del pipeline sigue; el manifest registra el fallo.
- **Feeds web**: `eventos_web.json` y `noticias_web.json` van minificados, solo con
  planes vigentes, textos acotados y sin imágenes placeholder (~4 MB frente a los
  ~17 MB del feed completo).
- **Imágenes**: si la fuente trae foto real, se usa; si no, la web genera un cover
  determinista por categoría (gradiente + icono), con fallback automático si una
  imagen remota falla o tarda demasiado.

## Setup

```bash
python -m venv .venv
# PowerShell
.venv\Scripts\Activate.ps1
# bash
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Pipeline de datos

```bash
# Todo: scraping (paralelo) + merge + categorías + geocoding + feeds web
python tools/scrape_all.py

# Reconstruir feeds desde los outputs por fuente ya existentes (sin scrapear)
python tools/scrape_all.py --merge-only

# Saltarse el geocoding (más rápido para pruebas)
python tools/scrape_all.py --merge-only --no-geocode

# Una sola fuente (cada scraper escribe su propio output)
python tools/fever.py
python tools/esmadrid.py
```

Variables útiles:
- `MAD_PLAN_FEVER_MODE=fast` desactiva la resolución de coordenadas de Fever.
- `MAD_PLAN_RENDER_IMAGES=1` activa la extracción de imágenes con navegador en
  Madrid Secreto (lenta; por defecto va apagada porque el merge ya recupera esas
  imágenes desde Fever).

## Frontend

```bash
cd frontend_new
npm install
npm run dev        # desarrollo en http://127.0.0.1:5173
npm run build      # bundle de producción en frontend_new/dist
```

Servir el build con los datos en vivo de `outputs/`:

```bash
python serve.py    # http://127.0.0.1:8000
```

Smoke test end-to-end (requiere build previo):

```bash
python tools/smoke_frontend.py
```

## Despliegue (GitHub Pages)

La web es 100 % estática (bundle de Vite + dos JSON), así que **GitHub Pages es
suficiente** — no hace falta Vercel/Netlify. Pasos, una sola vez:

1. En GitHub: **Settings → Pages → Source: "GitHub Actions"**.
2. Lanza el workflow **"Desplegar web (GitHub Pages)"** desde la pestaña
   Actions (o haz cualquier push a `main`).

A partir de ahí la web se redespliega sola: con cada push de código y cada
madrugada tras la actualización de datos (el workflow nocturno incluye un job
de deploy, porque los commits del bot no disparan otros workflows). El build
usa `base: './'`, por lo que funciona igual en `usuario.github.io/mad_plan/`
que en local.

Nota: en un repo privado la web publicada es accesible para cualquiera con la
URL (la restricción de acceso a Pages solo existe en el plan Enterprise). Si
algún día quieres dominio propio o protegerla con contraseña, entonces sí:
Netlify/Vercel (gratis para proyectos personales) o Cloudflare Pages.

## Actualización automática (GitHub Actions)

`.github/workflows/nightly_scrape.yml` corre el pipeline **una vez al día**
(04:15 UTC) y commitea los feeds web actualizados al repo. Presupuesto pensado
para GitHub Pro (3.000 min/mes en repos privados):

- Tope duro de 45 min por ejecución → peor caso ~1.400 min/mes (~46% del límite).
- Ejecución típica: 12-20 min.
- Los outputs por fuente se conservan entre ejecuciones vía `actions/cache`,
  así una fuente caída no borra sus datos.
- También se puede lanzar a mano desde la pestaña Actions (workflow_dispatch).

Solo se versionan `eventos_web.json`, `noticias_web.json`, `pipeline_diario.json`
y `geocode_cache.json`; el resto de outputs intermedios están en `.gitignore`.

## Fuentes (22)

Fever, Eventbrite, datos.madrid.es, esMadrid, Madrid Secreto, Wegow, Ticketmaster,
Meetup, RockTheSport, IFEMA, Matadero, Teatros del Canal, Círculo de Bellas Artes,
Casa de México, Espacio Fundación Telefónica, Museo Reina Sofía, Biblioteca
Nacional, Fundación Canal, Fundación MAPFRE, Sala El Sol — y noticias de Time Out
Madrid y Gacetín Madrid.

## Contrato de datos (feed web)

Campos principales de cada plan en `eventos_web.json`:

- Identidad: `id`, `fuente`, `fuentes_relacionadas`
- Contenido: `titulo`, `subtitulo`, `resumen`, `descripcion`, `imagen`
- Clasificación: `categoria_principal_norm`, `categorias_normalizadas` (18 categorías canónicas)
- Lugar: `lugar`, `direccion`, `latitud`, `longitud`
- Precio: `precio`, `moneda`, `es_gratis`
- Fechas: `modo_fecha`, `estado_temporal`, `fecha_inicio`, `fecha_fin`,
  `datetime_inicio`, `proxima_fecha`, `proximo_datetime`, `sort_datetime`,
  `vigente_hasta`, `sesiones` (máx. 8 futuras)
- Enlaces: `url`, `url_compra`, `source_links` (comparativa entre fuentes)

La web recalcula en cliente la "próxima fecha relevante" contra el día actual,
de modo que un feed de hace unos días sigue mostrando fechas correctas.
