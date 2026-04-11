# STATUS

## Proyecto

- Web para agregar eventos publicos y noticias de Madrid en dos vistas separadas.
- El repo prioriza scrapers pequenos, legibles y con salida JSON local.

## Estado actual

- Scrapers existentes: Fever, Eventbrite, datos.madrid.es.
- Scrapers anadidos en esta sesion: Madrid Secreto para planes y Time Out para noticias.
- Runner principal: `scrape_all.py`.

## Reglas de trabajo

- Cada prompt del agente debe dejar constancia en este archivo.
- Priorizar estrategias robustas sobre scraping visual fragil.
- Mantener el estilo actual del repo: una funcion principal por scraper, logging simple y salida JSON local.
- No hacer reestructuras grandes si no aportan valor inmediato.

## Hallazgos tecnicos

- Madrid Secreto expone WordPress REST API.
- La categoria `que-hacer` de Madrid Secreto tiene `id=112`.
- El archivo completo `que-hacer` de Madrid Secreto expone `3065` posts historicos via REST.
- Muchos posts recientes de `que-hacer` incluyen bloques `data-fever-plan-*` utiles para extraer planes.
- El post mensual `planes-abril` no lleva bloques Fever, pero si modulos con precio, ubicacion y fechas parseables.
- Time Out detalle sirve `NewsArticle` en JSON-LD con titulo, fecha, imagen, categoria y autor.
- Time Out permite descubrir todo su historico de noticias a traves del archivo mensual de `sitemaps`.
- Time Out endurece el acceso a articulos con verificacion humana; la estrategia mas estable ha sido discovery por navegador renderizado + extraccion hibrida (HTML directo cuando entra y fallback a `r.jina.ai` cuando bloquea).
- Para producto final no interesa el historico completo: Time Out queda fijado a una ventana reciente de `21` dias y Madrid Secreto a planes activos/futuros hasta `365` dias, con fallback de `45` dias para planes sin fecha explicita.
- En este entorno `curl` no resolvia esos hosts, pero `requests` desde el `.venv` si funciona.
- El instalador integrado de paquetes no reflejo cambios en el `.venv`; se resolvio con `python -m pip install ...` dentro del entorno real.

## Registro de trabajo

### 2026-04-10

- Se revisaron las scrapers existentes para copiar el estilo y el esquema de salida.
- Se exploro Time Out Madrid y Madrid Secreto con fetch remoto y pruebas reales desde Python.
- Se confirmo que Madrid Secreto es mejor via REST y Time Out mejor via listado HTML + JSON-LD en detalle.
- Se preparo la base del repo con `requirements.txt`, `.gitignore` y `README.md`.
- Se implemento `timeout.py` para noticias de Time Out con listado HTML + detalle `NewsArticle` JSON-LD.
- Se implemento `madrid_secreto.py` para planes de Madrid Secreto con REST + roundup mensual + bloques `data-fever-plan-*`.
- Validacion real de `timeout.py`: 8 noticias guardadas, 6 categorias utiles detectadas.
- Validacion real de `madrid_secreto.py`: 18 planes guardados, 16 con precio y 15 con fechas.
- `scrape_all.py` se actualizo para incluir Madrid Secreto en eventos y Time Out en una salida separada de noticias.
- El runner completo arranca correctamente; la fase lenta sigue siendo Fever, en concreto la resolucion de venues/coords.

### 2026-04-11

- Se reorganizo el repo para guardar las scrapers en `tools/`.
- Se centralizaron las salidas JSON en `outputs/`.
- Se ajustaron todas las rutas de salida y los comandos de `README.md` a la nueva estructura.
- `madrid_secreto.py` se amplio para recorrer todo el archivo `que-hacer`, no solo posts recientes.
- La salida final validada de Madrid Secreto es `3496` planes en `outputs/eventos_madrid_secreto.json`.
- De esos `3496` planes, `1198` llevan precio y `606` fechas parseadas.
- `timeout.py` se rehizo para discovery maximo del historico de Time Out a partir de `136` paginas mensuales de sitemap.
- Se validaron `11816` URLs unicas de noticias de Time Out descubiertas en ese historico.
- Para Time Out se anadio bootstrap con Playwright, fallback por `r.jina.ai` y checkpoints de salida para no perder progreso en ejecuciones largas.
- Se anadio `playwright` a `requirements.txt` y el paso `python -m playwright install chromium` al `README.md`.
- Se descarto el enfoque de base historica para producto: `timeout.py` ahora escanea solo `3` meses recientes de sitemap y conserva noticias de los ultimos `21` dias.
- Salida final validada de Time Out: `95` noticias en `outputs/noticias_timeout.json`, desde `2026-03-22` hasta `2026-04-11`.
- En la salida final de Time Out, las `95` noticias llevan autor y `85` incluyen secciones detectadas.
- `madrid_secreto.py` mantiene el rastreo amplio para no perder planes vigentes escondidos en roundups antiguos, pero el output final ya no es historico.
- Salida final validada de Madrid Secreto: `369` planes en `outputs/eventos_madrid_secreto.json`.
- En la salida final de Madrid Secreto, `274` planes llevan `fecha_inicio` y `255` llevan precio.
- El filtro final de Madrid Secreto conserva planes activos o futuros hasta `365` dias por delante y solo deja planes sin fecha si fueron publicados o actualizados en los ultimos `45` dias.
- Se anadio deduplicacion final orientada a feed para colapsar planes repetidos entre roundups, posts y embeds; solo quedan duplicados residuales muy puntuales.