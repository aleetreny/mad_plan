# STATUS

## Proyecto

- Web para agregar eventos publicos y noticias de Madrid en dos vistas separadas.
- El repo prioriza scrapers pequenos, legibles y con salida JSON local.

## Estado actual

- Scrapers existentes: Fever, Eventbrite, datos.madrid.es.
- Scrapers anadidos en esta sesion: Madrid Secreto para planes y Time Out para noticias.
- Runner principal: `scrape_all.py`.

## Roadmap de fuentes investigadas

- Candidatas prioridad alta para implementar: Matadero Madrid, Teatros del Canal, Circulo de Bellas Artes, IFEMA Madrid, Casa de Mexico, Espacio Fundacion Telefonica, Museo Reina Sofia, Biblioteca Nacional, Fundacion Canal, Sapos y Princesas, Somos Madrid y Gacetin Madrid.
- Estado de validacion actual del roadmap: Matadero Madrid, Teatros del Canal, Circulo de Bellas Artes, IFEMA Madrid, Casa de Mexico, Espacio Fundacion Telefonica, Museo Reina Sofia, Biblioteca Nacional, Fundacion Canal, Fundacion MAPFRE, Sala El Sol, Wegow, Ticketmaster Madrid y Gacetin Madrid quedan aceptadas para el pipeline; Sapos y Princesas y Somos Madrid quedan descartadas tras validacion real.
- Candidatas de segunda ola pendientes: La Casa Encendida, CaixaForum Madrid.
- Candidatas valiosas pero con mas friccion tecnica: Museo del Prado, Filmoteca Espanola y agendas heterogeneas de madrid.es / Comunidad de Madrid.
- Descartes o no prioritarias por baja calidad, rotura o poca senal: somoschueca.com, madridfree.com, madriddiario.es, guiadelocio.com, verydiferente.com, Sapos y Princesas y Somos Madrid.
- Regla de producto para nuevas fuentes: priorizar fuentes primarias de venue o institucion; usar agregadores solo como capa secundaria de discovery.
- Regla de deduplicacion para nuevas fuentes: cada nueva integracion debe entrar en la capa comun `normalize_plan_records` y juzgarse por su merge real frente a Fever, Eventbrite, datos.madrid y Madrid Secreto antes de quedarse en el pipeline diario.
- Regla de seleccion editorial: si una fuente aporta muchos planes repetidos sin enriquecer precio, fecha, venue o categoria, no debe quedarse en produccion aunque sea tecnicamente scrapeable.

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
- Se normalizaron todas las salidas de `tools/` con una capa comun para web: `fuente_id`, `tipo`, `slug`, `resumen`, `categoria_principal`, `modo_fecha`, `estado_temporal`, `proxima_fecha`, `proximo_datetime`, `sort_datetime`, `publicado_en`, `actualizado_en`, `sesiones`, `timezone` y `metadata`.
- Las fechas de dia completo ahora se distinguen de horas reales: timestamps placeholders como `00:00` o `23:59` ya no se exponen como horas en la capa web.
- Para planes recurrentes largos, las `sesiones` publicadas se recortan a fechas futuras/relevantes y el orden del feed usa la `proxima_fecha` en vez del inicio historico del evento.
- Se creo `tools/daily_trigger.py` como entrada de trigger habitual y se dejo `outputs/pipeline_diario.json` como manifiesto de la ultima ejecucion para la web.
- El trigger diario ya no usa Fever rapido por defecto: queda preparado para correr con Fever completo en ejecuciones nocturnas.
- Se dejo el trigger apto para GitHub Actions con configuracion por CLI/env (`MAD_PLAN_FEVER_MODE`, `MAD_PLAN_TRIGGER_SOURCE`, `MAD_PLAN_TRIGGER_SCHEDULE`, `MAD_PLAN_TRIGGER_TYPE`).
- Se anadio `.github/workflows/nightly_scrape.yml` para la ejecucion nocturna programada en GitHub Actions, instalando dependencias y Playwright antes del run.
- Fever rapido se mantiene solo como override explicito para pruebas locales o ejecuciones de humo.
- Se valido el ensamblado final de producto desde los outputs actualizados de fuente.
- Salidas finales listas para web: `outputs/eventos_madrid_all.json` con `2628` planes y `outputs/noticias_madrid_all.json` con `95` noticias.
- Validacion final de producto: sin errores en `pipeline_diario.json`, `0` IDs duplicados en noticias, `0` IDs duplicados en planes tras corregir el caso `madrid-secreto`, `51` planes fusionados entre multiples fuentes, `1771` planes con precio y `1739` con coordenadas.

### 2026-04-12

- Se hizo una investigacion extensa de nuevas fuentes de noticias, eventos, planes y actividades de Madrid con validacion tecnica real de accesos, APIs, RSS, WordPress REST, JSON:API y estructura HTML.
- Se dejo trazabilidad en este archivo de todas las fuentes investigadas, separando prioridad alta, segunda ola, fuentes restringidas y descartes.
- Se fijo el criterio de implementacion incremental: entrar fuente a fuente, observar output real, medir solape con el stack actual y decidir si se queda o no.
- Se fijo como primera fuente a implementar `Matadero Madrid` por combinar alto valor editorial, mucha variedad tematica y una JSON:API publica muy limpia.
- Se arranca la implementacion de `Matadero Madrid` como scraper primario de planes, con el objetivo de juzgar despues su deduplicacion y valor neto frente a `datos_madrid`, `Eventbrite`, `Fever` y `Madrid Secreto`.
- `Matadero Madrid` quedo integrado en `tools/matadero.py`, `tools/scrape_all.py` y en la prioridad de merge de `tools/normalization.py`.
- La consulta de Matadero se acoto con filtros reales de JSON:API para evitar archivo historico: `field_end_date >= hoy` y `field_init_date <= hoy + 180 dias`.
- Validacion real del output de Matadero: `143` planes normalizados en `outputs/eventos_matadero.json`, con `141` coordenadas y `53` precios.
- Juicio editorial y de deduplicacion: Matadero aporta `133` planes netos nuevos tras merge frente al stack actual (`Fever`, `Eventbrite`, `datos_madrid`, `Madrid Secreto`) y no introduce solapes detectados con esas fuentes.
- Decision: `Matadero Madrid` se queda en el pipeline diario como fuente primaria de venue por su valor neto, calidad de categorias, buena cobertura de coordenadas y variedad tematica (cine, infancia, pensamiento, danza y talleres).
- Ajuste de calidad aplicado tras observar el output: se evito asignar coordenadas de Matadero a eventos educativos que realmente indican un venue externo como `Movistar KOI`.
- Se continuo con `Teatros del Canal` como siguiente fuente primaria de venue, usando su API publica de The Events Calendar para discovery y HTML de detalle para enriquecer descripcion, sala y precio.
- Validacion real del output de Teatros del Canal tras el ajuste del parser: `20` planes normalizados en `outputs/eventos_teatros_canal.json`, con `16` precios y `0` coordenadas fiables.
- Ajuste de calidad aplicado tras observar el primer output de Teatros del Canal: se recorto el texto antes de bloques comerciales y se sustituyo el parser generico por uno de precios explicitos para evitar falsos `0.0` y `es_gratis=true`.
- Juicio editorial y de deduplicacion: Teatros del Canal aporta `20` planes netos nuevos tras merge frente al stack actual (`Fever`, `Eventbrite`, `datos_madrid`, `Madrid Secreto`, `Matadero`) y no introduce solapes detectados con esas fuentes.
- Decision: `Teatros del Canal` se queda en el pipeline diario como fuente primaria de venue por su valor neto, senal cultural propia y buena cobertura de precio, aunque sin coordenadas por falta de latitud/longitud fiables en la fuente.
- Se continuo con `Circulo de Bellas Artes` como siguiente fuente primaria de venue, usando la agenda publica HTML para discovery y las fichas de detalle para enriquecer descripcion, sesiones, sala, precio y enlaces de compra.
- Validacion real del output de Circulo de Bellas Artes tras los ajustes del parser: `45` planes normalizados en `outputs/eventos_circulo_bellas_artes.json`, con `25` precios y `12` coordenadas.
- Ajustes de calidad aplicados tras observar el output de Circulo de Bellas Artes: se corrigio la deteccion del titulo real frente al `h1` institucional del layout, se evito cortar el contenido antes de secciones utiles como `Precios` y `Abonos`, y se descartaron URLs de compra genericas o compartidas que estaban colapsando eventos distintos durante el merge.
- Juicio editorial y de deduplicacion: Circulo de Bellas Artes aporta `45` planes netos nuevos tras merge frente al stack actual (`Fever`, `Eventbrite`, `datos_madrid`, `Madrid Secreto`, `Matadero`, `Teatros del Canal`) y no introduce solapes detectados con esas fuentes.
- Decision: `Circulo de Bellas Artes` se queda en el pipeline diario como fuente primaria de venue por su alto valor neto, buena diversidad editorial (exposiciones, cine, talleres, escenicas y actividades) y una combinacion util de precio, sesiones y venue.
- Se continuo con `IFEMA Madrid` como siguiente fuente primaria de venue, usando `https://www.ifema.es/calendario/todos` como discovery HTML server-rendered con `Event` JSON-LD por tarjeta y enriquecimiento posterior desde cada ficha de detalle.
- Validacion real del output de IFEMA tras endurecer el filtro geografico: `52` planes normalizados en `outputs/eventos_ifema_madrid.json`, con `0` coordenadas y `0` precios.
- Ajustes de calidad aplicados tras observar el primer output de IFEMA: se descartaron falsos positivos de ferias externas publicadas bajo marca IFEMA (`SICON Mexico`, `ESS+ Colombia`) combinando filtro por `title/url` y descripciones con geografia no Madrid, y se recortaron bloques de navegacion/relacionados en el contenido de detalle.
- Juicio editorial y de deduplicacion: IFEMA aporta `52` planes netos nuevos tras merge frente al stack actual (`Fever`, `Eventbrite`, `datos_madrid`, `Madrid Secreto`, `Matadero`, `Teatros del Canal`, `Circulo de Bellas Artes`) y no introduce solapes detectados con esas fuentes.
- Decision: `IFEMA Madrid` se queda en el pipeline diario como fuente primaria de venue por su valor neto muy alto, su cobertura de grandes ferias y eventos singulares que no estaban entrando por otras vias y una salida suficientemente limpia para web pese a no traer precio ni coordenadas fiables.
- Se continuo con `Casa de Mexico` como siguiente fuente primaria de venue, usando el fragmento AJAX publico `rellenar-agenda.php` detras de `/agenda/` para discovery por vista mensual y verticales tematicos, con enriquecimiento posterior desde las fichas de detalle.
- Validacion real del output de Casa de Mexico tras ajustar discovery y limpieza: `74` planes normalizados en `outputs/eventos_casa_mexico.json`, con `71` precios y `0` coordenadas.
- Ajustes de calidad aplicados tras observar el output de Casa de Mexico: se amplio el selector de tarjetas para cubrir exposiciones y otros verticales, se eliminaron URLs privadas (`/privado/`) que no deben salir al feed publico, se deduplico discovery entre vistas y se neutralizaron enlaces de compra compartidos para evitar colisiones de merge si reaparecen.
- Juicio editorial y de deduplicacion: Casa de Mexico aporta `74` planes netos nuevos tras merge frente al stack actual (`Fever`, `Eventbrite`, `datos_madrid`, `Madrid Secreto`, `Matadero`, `Teatros del Canal`, `Circulo de Bellas Artes`, `IFEMA`) y no introduce solapes detectados con esas fuentes.
- Decision: `Casa de Mexico` se queda en el pipeline diario como fuente primaria de venue por su valor neto muy alto, su cobertura diferencial en cine, literatura, familia, academia y talleres, y una senal de precio especialmente buena para producto aunque no aporte coordenadas fiables.
- Se continuo con `Espacio Fundacion Telefonica` como siguiente fuente primaria de venue, usando la coleccion publica `wp-json/wp/v2/tribe_events` para discovery y las fichas HTML de detalle para enriquecer sesiones, descripcion y enlaces de reserva.
- Hallazgo tecnico relevante en Espacio Fundacion Telefonica: la raiz de la REST devuelve `401`, pero el tipo `tribe_events` si queda accesible y devuelve solo `12` items vigentes, lo que permite un discovery limpio sin arrastrar archivo historico.
- Validacion real del output de Espacio Fundacion Telefonica: `12` planes normalizados en `outputs/eventos_espacio_fundacion_telefonica.json`, con `12` precios, `12` sesiones publicadas y `0` coordenadas.
- Ajustes de calidad aplicados tras observar el output de Espacio Fundacion Telefonica: se parsearon las filas `.linea_reserva` para conservar la proxima sesion de talleres recurrentes, se usaron los bloques `Event` JSON-LD de detalle para titulo y fechas estructuradas, y se dejo proteccion para neutralizar URLs de reserva compartidas si el venue las reutiliza en el futuro.
- Juicio editorial y de deduplicacion: Espacio Fundacion Telefonica aporta `12` planes netos nuevos tras merge frente al stack actual (`Fever`, `Eventbrite`, `datos_madrid`, `Madrid Secreto`, `Matadero`, `Teatros del Canal`, `Circulo de Bellas Artes`, `IFEMA`, `Casa de Mexico`) y no introduce solapes detectados con esas fuentes.
- Decision: `Espacio Fundacion Telefonica` se queda en el pipeline diario como fuente primaria de venue por su senal propia en exposiciones, encuentros y programas formativos, aunque su volumen sea moderado y el precio `0.0` dependa de la politica publica de gratuidad del venue mas que de un campo itemizado en cada ficha.
- Se continuo con `Museo Reina Sofia` como siguiente fuente primaria de venue, usando el API publico del buscador `https://buscador.museoreinasofia.es/api/search` para discovery de actividades y `page-data` de Gatsby para enriquecer las fichas sin depender de scraping visual.
- Hallazgo tecnico relevante en Museo Reina Sofia: el listing `/busqueda` renderiza los resultados en cliente; la base del buscador sale del bundle JS (`https://buscador.museoreinasofia.es/api`) y permite paginar el archivo completo. Para no arrastrar historico, se filtro por actividades con `processedDates` futuras y se corto el rastreo tras una ventana larga de paginas sin senal viva.
- Validacion real del output de Museo Reina Sofia: `44` planes normalizados en `outputs/eventos_museo_reina_sofia.json`, con `43` precios, `31` planes multi-sesion y `0` coordenadas.
- Ajustes de calidad aplicados tras observar el output de Museo Reina Sofia: se uso `page-data` en vez del HTML final para extraer descripcion, sesiones, location y tickets; se conservaron actividades recurrentes largas si mantienen sesiones futuras; y se dejo proteccion para neutralizar enlaces de entrada compartidos si el museo los reutiliza mas adelante.
- Juicio editorial y de deduplicacion: Museo Reina Sofia aporta `44` planes netos nuevos tras merge frente al stack actual (`Fever`, `Eventbrite`, `datos_madrid`, `Madrid Secreto`, `Matadero`, `Teatros del Canal`, `Circulo de Bellas Artes`, `IFEMA`, `Casa de Mexico`, `Espacio Fundacion Telefonica`) y no introduce solapes detectados con esas fuentes.
- Decision: `Museo Reina Sofia` se queda en el pipeline diario como fuente primaria de venue por su alto valor neto, su gran densidad de programacion cultural propia y una combinacion muy util de sesiones, sedes internas y enlaces de acceso aunque no aporte coordenadas fiables.
- Se continuo con `Biblioteca Nacional` como siguiente fuente primaria de agenda institucional, usando el listado HTML server-rendered de `/es/agenda` y las fichas de detalle para extraer rangos, sesiones, lugar e informacion de acceso.
- Hallazgo tecnico relevante en Biblioteca Nacional: la agenda publica ya viene filtrada a partir de hoy y solo necesita discovery HTML; las fichas mezclan eventos presenciales con formaciones puramente digitales, por lo que se filtro `Modalidad Digital` para no contaminar el feed Madrid con actividades online sin sede fisica.
- Validacion real del output de Biblioteca Nacional: `6` planes normalizados en `outputs/eventos_biblioteca_nacional.json`, con `6` precios, `1` taller recurrente con sesiones futuras explicitadas y `0` coordenadas.
- Ajustes de calidad aplicados tras observar el output de Biblioteca Nacional: se descartaron la exposicion permanente y las paginas genericas sin fecha accionable, se generaron sesiones semanales futuras para `Construimos una imprenta` a partir del horario recurrente, y se evito incluir las formaciones digitales de consulta de salas y busqueda bibliografica por su baja adecuacion al producto local.
- Juicio editorial y de deduplicacion: Biblioteca Nacional aporta `6` planes netos nuevos tras merge frente al stack actual (`Fever`, `Eventbrite`, `datos_madrid`, `Madrid Secreto`, `Matadero`, `Teatros del Canal`, `Circulo de Bellas Artes`, `IFEMA`, `Casa de Mexico`, `Espacio Fundacion Telefonica`, `Museo Reina Sofia`) y no introduce solapes detectados con esas fuentes.
- Decision: `Biblioteca Nacional` se queda en el pipeline diario, pero solo con su franja presencial y fechada, porque asi aporta exposiciones, conferencias y un taller educativo utiles para la web sin arrastrar ruido formativo online ni paginas de servicio.
- Se continuo con `Fundacion Canal` como siguiente fuente primaria de venue, usando las paginas de archivo server-rendered de exposiciones, conferencias y musica en familia para discovery, mas la pagina del ciclo de musica de camara para capturar el proximo concierto destacado.
- Hallazgo tecnico relevante en Fundacion Canal: no hay un calendario unificado ni un tipo REST util para actividades; la senal fiable esta repartida entre archivos HTML por seccion (`/exposiciones/`, `/ciclo-de-conferencias/`, `/ciclo-musica-en-familia/`) y una landing especial en `ciclo-musica-camara` con el proximo concierto embebido en la propia pagina.
- Validacion real del output de Fundacion Canal: `4` planes normalizados en `outputs/eventos_fundacion_canal.json`, con `3` precios, `0` coordenadas y una mezcla limpia de exposiciones, conferencia y musica clasica.
- Ajustes de calidad aplicados tras observar el output de Fundacion Canal: se dejaron fuera los subeventos recurrentes ambiguos sin rango accionable (`durante el periodo expositivo`), se evito tomar como compra principal enlaces de visitas guiadas que no corresponden a la exposicion base, y se resumio el concierto de camara desde sus notas editoriales en vez de exponer el programa completo como descripcion principal.
- Juicio editorial y de deduplicacion: Fundacion Canal aporta `4` planes netos nuevos tras merge frente al stack actual (`Fever`, `Eventbrite`, `datos_madrid`, `Madrid Secreto`, `Matadero`, `Teatros del Canal`, `Circulo de Bellas Artes`, `IFEMA`, `Casa de Mexico`, `Espacio Fundacion Telefonica`, `Museo Reina Sofia`, `Biblioteca Nacional`) y no introduce solapes detectados con esas fuentes.
- Decision: `Fundacion Canal` se queda en el pipeline diario como fuente primaria de venue. Su volumen actual es bajo, pero la senal es propia, limpia y editorialmente diferencial en exposiciones y ciclos culturales que no estaban entrando por otras vias.
- Se valido `Sapos y Princesas` con prueba tecnica real sobre el listing de Madrid y las fichas con `Event` JSON-LD. El origen es scrapeable y en una muestra filtrada produjo `27` registros / `26` netos / `1` solapado, pero editorialmente queda dominado por ocio familiar evergreen, rutas y agregacion de terceros con ventanas larguisimas, por lo que no encaja con la regla de producto de priorizar venues e instituciones primarias.
- Decision: `Sapos y Princesas` queda descartada para produccion. Puede servir como discovery secundaria en investigacion futura, pero no como fuente diaria normalizada.
- Se valido `Somos Madrid` directamente y el dominio operativo `somosmadrid.es` resulto ser una web de casinos/bonos, no una fuente local de Madrid. Las rutas `/cultura/` y `/agenda/` devolvieron error `500` y no aparecio ninguna senal editorial util para el producto.
- Decision: `Somos Madrid` queda descartada por fuente equivocada y sin valor tecnico/editorial.
- Se reidentifico `Gacetin Madrid` como `gacetinmadrid.com` y se comprobo que expone WordPress REST y una seccion real de `Cultura y Ocio` en `/ocio/`. Sobre esa base se implemento `tools/gacetin_madrid.py` usando `wp-json/wp/v2/posts` filtrado por la categoria `ocio` (`id=7`), con filtro editorial para conservar solo noticias recientes con senal clara de plan/cultura/ocio en titular o sumario.
- Validacion real del output de Gacetin Madrid: `54` noticias normalizadas en `outputs/noticias_gacetin_madrid.json`. En comparacion con `Time Out`, el solape exacto de titulares es `0`, con solo proximidad tematica puntual en unos pocos temas muy visibles de la agenda madrilena.
- Juicio editorial de Gacetin Madrid: la fuente es mas institucional y basada en nota/reescritura que `Time Out`, pero aporta mucha agenda cultural local, distritos y senal de servicio publico que apenas estaba entrando por la capa de noticias actual.
- Decision: `Gacetin Madrid` se queda en el pipeline diario como segunda fuente de noticias local, complementaria a `Time Out`.
- Comprobacion general final del bloque de prioridad alta: todas las fuentes de venue aceptadas del bloque siguen aportando presencia exclusiva en el merge actual del stack completo. En la auditoria final aparecen `Matadero 133`, `Teatros del Canal 20`, `Circulo 45`, `IFEMA 52`, `Casa de Mexico 74`, `Espacio Fundacion Telefonica 12`, `Museo Reina Sofia 44`, `Biblioteca Nacional 6` y `Fundacion Canal 4` como contribuciones exclusivas tras merge, asi que no hay motivo para retirar ninguna de las aceptadas.
- Comprobacion general final de noticias del bloque: `Time Out 95` + `Gacetin Madrid 54` producen `149` noticias validadas sin errores en el merge comun, con reparto complementario entre lifestyle/cultura (`Time Out`) y agenda cultural/local institucional (`Gacetin`).

### 2026-04-13

- Se continuo la segunda ola con `Fundacion MAPFRE`, priorizandola sobre agregadores porque la senal util esta en una fuente primaria de venue con programacion propia en Madrid.
- Hallazgo tecnico relevante: `https://www.fundacionmapfre.org/agenda-madrid/` devuelve `404`; el discovery fiable para Madrid sale de `https://www.fundacionmapfre.org/arte-y-cultura/exposiciones/sala-recoletos/`, que lista solo las exposiciones vigentes de Recoletos y deja aparte el historico.
- `Fundacion MAPFRE` quedo integrada en `tools/fundacion_mapfre.py`, `tools/scrape_all.py` y en la prioridad de merge de `tools/normalization.py`.
- Ajustes de calidad aplicados tras observar la pagina real: se filtro discovery al CTA `DESCUBRE LA EXPOSICION` de las fichas vigentes para no arrastrar modales internos de compra ni subpaginas antiguas como `las-hermanas-brown`; se tomaron fechas, lugar, imagen y precio base desde `ExhibitionEvent` JSON-LD; y se neutralizo la URL de compra generica compartida para evitar colisiones en el merge.
- Ajuste adicional de producto: las fechas `00:00` / `23:59` del schema se trataron como rango de dia completo para no desplazar artificialmente el cierre al dia siguiente por efecto de timezone.
- Validacion real del output de Fundacion MAPFRE: `2` planes normalizados en `outputs/eventos_fundacion_mapfre.json`, ambos con precio y `0` coordenadas.
- Juicio editorial y de deduplicacion: Fundacion MAPFRE aporta `2` planes netos nuevos tras merge frente al stack actual (`Fever`, `Eventbrite`, `datos_madrid`, `Madrid Secreto` y el resto de venues aceptados). La simulacion de merge pasa de `2817` a `2819` planes y mantiene validacion `OK`.
- Decision: `Fundacion MAPFRE` se queda en el pipeline diario. Su volumen actual es bajo, pero la senal es primaria, limpia y exclusiva, con exposiciones de alto valor cultural que no estaban entrando por otras vias.
- Se continuo la segunda ola con `Sala El Sol`, priorizandola por delante de agregadores como `Wegow`, `Ticketmaster` o `Meetup` porque la sala expone agenda propia y aporta programacion musical/clubbing primaria en Madrid.
- Hallazgo tecnico relevante en Sala El Sol: `wp-json` esta accesible, pero no expone un tipo REST reutilizable para eventos; el discovery fiable sale de `https://salaelsol.com/agenda/` a traves de tarjetas HTML server-rendered `.agenda.gran-contenedor-agenda`, y el detalle util vive en `main.site-main.event` dentro de cada ficha `/eventos/<slug>/`.
- `Sala El Sol` quedo integrada en `tools/sala_el_sol.py`, `tools/scrape_all.py` y en la prioridad de merge de `tools/normalization.py`.
- Ajustes de calidad aplicados tras observar la web real: se ignoro el calendario historico de la cabecera y solo se tomaron tarjetas de agenda futuras; el ano se infirio secuencialmente a partir del orden cronologico del listing para cubrir el salto de diciembre a enero; los eventos nocturnos con hora de cierre menor que la de apertura se trataron como rangos que cruzan medianoche; y se neutralizaron URLs de ticketing compartidas cuando una misma compra servia para dos fechas distintas.
- Ajuste adicional de producto: la categoria `Familia` se restringio a senales realmente infantiles o familiares (`edad recomendada`, `entrada/anticipada infantil`, etc.) para no contaminar conciertos normales que mencionan ninos en otros contextos editoriales.
- Validacion real del output de Sala El Sol: `48` planes normalizados en `outputs/eventos_sala_el_sol.json`, con `47` precios y `48` coordenadas a partir del venue publicado por la propia sala (`Calle de los Jardines 3`, coordenadas del embed de contacto).
- Juicio editorial y de deduplicacion: Sala El Sol aporta `47` planes netos nuevos tras merge frente al stack actual; la simulacion pasa de `2820` a `2867` planes y mantiene validacion `OK`. Solo aparece `1` solape real (`Joshua Idehen`, tambien presente en `Fever` y `Madrid Secreto`).
- Decision: `Sala El Sol` se queda en el pipeline diario. Aporta una senal propia, densa y muy poco solapada en conciertos y clubbing, con buen precio, venue consistente y cobertura de ticketing suficientemente limpia para web.
- Se abrio el bloque de fuentes de volumen con `Wegow` y, en paralelo, se hizo una auditoria de limpieza del feed web completo para detectar deuda real en categorias, ubicacion e imagen.
- Hallazgo tecnico relevante en Wegow: las rutas publicas de la web no sirven como discovery fiable de Madrid, pero el frontend Nuxt expone un API publico en `https://api.wegow.com/api`. La resolucion correcta sale de `location-search/?query=madrid`, el filtro de ciudad usa `cities=3117735` y no `city=...`, los tipos de evento son numericos (`0=concerts`, `1=festivals`) y el enriquecimiento bueno sale de `events/<slug>/`.
- `Wegow` quedo integrado en `tools/wegow.py`, `tools/scrape_all.py` y en la prioridad de merge de `tools/normalization.py` como agregador secundario por debajo de fuentes primarias y por delante de la capa editorial pura.
- Ajustes de calidad aplicados tras observar el output real: se descartaron fichas internas/de prueba (`prueba`, `redirections`, etc.), se filtro senal no Madrid incluso cuando el backend devolvia slugs contaminados, y se neutralizaron URLs de compra compartidas para evitar colisiones futuras de merge.
- Hallazgo tecnico adicional del runner: `tools/scrape_all.py` fallaba si se invocaba como modulo porque importaba scrapers hermanos sin prefijo de paquete. Se corrigio `_import_callable` con `importlib` para que funcione tanto al ejecutar el script como al importarlo desde `tools.`.
- Validacion real del output de Wegow: `108` planes normalizados en `outputs/eventos_wegow.json`, con `29` precios, `106` coordenadas y `0` huecos de categoria, imagen o ubicacion.
- Juicio editorial y de deduplicacion: Wegow aporta `108` planes netos nuevos tras merge frente al stack actual; la simulacion pasa de `2860` a `2968` planes y no aparece ningun solape real en el merge actual (`108` clusters exclusivos, `0` compartidos).
- Decision: `Wegow` se queda en el pipeline diario como capa secundaria de discovery musical. No sustituye a venues primarios, pero su aporte neto actual es demasiado alto y su salida ha quedado suficientemente limpia para web.
- Auditoria de limpieza tras recomponer el merge actual desde outputs validados: `outputs/eventos_madrid_all.json` queda en `2968` planes validos y `outputs/noticias_madrid_all.json` en `147` noticias validas. Persisten `3` planes sin `categoria_principal` (todos de `Museo Reina Sofia`), `55` planes sin `lugar`/`direccion` (`52` de `Madrid Secreto`, `3` de `Fever`) y `1175` planes sin imagen (`1167` de `datos_madrid`, `5` de `Eventbrite`, `3` de `Madrid Secreto`).
- Se cerraron los dos focos de higiene abiertos tras la auditoria: `Museo Reina Sofia` paso de `3` a `0` planes sin categoria principal, `Madrid Secreto` paso de `52` a `0` planes sin ubicacion tras inferencia y poda de `7` registros debiles sin sede util, y `Fever` paso de `3` a `0` planes sin ubicacion tras corregir la decodificacion del detalle y el fallback visible de `Lugar` / `Como llegar`.
- Se endurecio `merge_news_records` para filtrar noticias fuera de la ventana de producto al recomponer desde outputs ya generados. Con esa proteccion, la recomposicion manual de higiene deja `outputs/eventos_madrid_all.json` en `2969` planes validos y `outputs/noticias_madrid_all.json` en `145` noticias validas, con `0` huecos de categoria y `0` huecos de ubicacion en planes; la deuda pendiente sigue concentrada en imagen (`1175`, dominada por `datos_madrid`).
- Se continuo la segunda ola con `Ticketmaster Madrid` como agregador secundario de ticketing. Hallazgo tecnico relevante: la ruta util no es `/city/...`, sino `https://www.ticketmaster.es/discover/madrid`, que expone `__NEXT_DATA__` server-rendered con el query `cityEvents(...)`; ademas, los eventos nativos se pueden enriquecer via `api/eventinfo/<event_id>`.
- `Ticketmaster Madrid` quedo implementado en `tools/ticketmaster.py` y conectado al runner en `tools/scrape_all.py`, pero se mantiene como fuente secundaria por debajo de venues primarios, `Fever`, `Eventbrite` y `Wegow`.
- Ajustes de calidad aplicados en Ticketmaster: se colapsaron sesiones repetidas del mismo plan agrupando por `titulo + venue + url`, se redujeron tandas horarias densas a fechas unicas cuando el mismo plan publica muchas sesiones, y se conservaron `99` eventos nativos de Ticketmaster frente a `44` partner events de `Universe` como senal de origen en metadata.
- Validacion real del output de Ticketmaster: `980` filas crudas de discovery repartidas en `49` paginas utiles se redujeron a `143` planes normalizados en `outputs/eventos_ticketmaster.json`, con `0` huecos de categoria, `0` huecos de ubicacion y `1` imagen ausente.
- Juicio editorial y de deduplicacion: en la simulacion actual Ticketmaster aporta `143` planes exclusivos y `0` solapes exactos frente al merge vigente, asi que entra como capa secundaria de discovery por su valor neto actual, aun siendo una fuente agregadora.
- Recomposicion final tras integrar Ticketmaster en el runner: `outputs/eventos_madrid_all.json` queda en `3112` planes validos y `outputs/noticias_madrid_all.json` en `145` noticias validas. El merge se mantiene en `0` huecos de categoria y `0` huecos de ubicacion en planes; la deuda restante se concentra en imagen (`1176`, todavia dominada por `datos_madrid`).
- Se ataco la deuda de imagen de `datos_madrid`: el JSON crudo no expone campos de media y la unica via parcialmente util pasa por paginas `madrid.es` bloqueadas en acceso directo. Se probo enriquecimiento via `r.jina.ai` sobre la ficha principal y la URL `references`, pero el proveedor externo rate-limita fuerte y no da una solucion suficientemente robusta para produccion. Decision: dejar el enriquecimiento como via opt-in (`DATOS_MADRID_IMAGE_ENRICHMENT=1`) y no activarlo en el pipeline diario por defecto.
- Se continuo la segunda ola con `esMadrid Agenda`, usando `https://www.esmadrid.com/agenda-madrid` y sus verticales tematicos para discovery. La validacion real encontro `275` URLs de detalle unicas y produjo `241` planes normalizados en `outputs/eventos_esmadrid.json`.
- Ajustes de calidad aplicados en `esMadrid`: se descartaron CTAs globales de `https://www.esmadrid.com/compras-madrid`, se anadio proteccion para no usar URLs de `esMadrid` como clave primaria de merge, y se infirieron ubicaciones genericas de Madrid en los pocos casos multi-sede donde el schema venia vacio.
- Validacion final de `esMadrid`: `241` planes, `241` con imagen, `241` con ubicacion y `0` con precio. Frente al stack previo (`3112` planes) aporta `234` candidatos aproximadamente exclusivos por `titulo + fecha + lugar`, con `7` solapes semanticos aproximados.
- Decision: `esMadrid` se queda en el pipeline diario como agenda oficial secundaria. Aporta mucho discovery limpio y visualmente completo, aunque su merge comun todavia conserva un pequeno riesgo de duplicado semantico mientras el dedupe global del producto siga priorizando URL en el resto de fuentes.
- Recomposicion manual de planes tras integrar `esMadrid`: `outputs/eventos_madrid_all.json` queda en `3352` planes validos, con `0` huecos de categoria, `0` huecos de ubicacion y la misma deuda absoluta de imagen (`1176`, aun concentrada en `datos_madrid`).

### 2026-04-13 (continuacion)

- Se implementaron las dos ultimas fuentes de la segunda ola: `RockTheSport` (deportes) y `Meetup` (comunidad).
- Hallazgo tecnico relevante en RockTheSport: la web publica (`web.rockthesport.com`) es una SPA Next.js; el backend real es `publicservice.rockthesport.com` con Swagger docs y 84 endpoints REST. Todos requieren `X-API-Key` que se encontro embebida en los chunks JS del frontend: `rts_public_web_2024_a8f3d9e1c4b7`. Espana es `countryId=65` y Madrid `provinceId=61`.
- `RockTheSport` quedo integrado en `tools/rockthesport.py`, `tools/scrape_all.py` y en `SOURCE_PRIORITY` de `tools/normalization.py` como agregador secundario de deportes (prioridad 4, misma que Ticketmaster).
- Validacion real del output de RockTheSport: `13` planes normalizados en `outputs/eventos_rockthesport.json`, con `13` coordenadas, `0` precios (la API no expone precio en el listado/detalle publico) y categorias automaticas de deporte (Running, Trail Running, Triatlon, Ciclismo).
- Hallazgo tecnico relevante en Meetup: la web usa Next.js con Apollo cache SSR que expone ~31 eventos en `__NEXT_DATA__`. El GraphQL endpoint real es `https://www.meetup.com/gql2` con query `recommendedEvents` (no `rankedEvents`). El tipo `Venue` usa `lon` (no `lng`). Se requiere warm-up de cookies via la pagina de busqueda antes de hacer requests al GQL.
- `Meetup` quedo integrado en `tools/meetup.py`, `tools/scrape_all.py` y en `SOURCE_PRIORITY` de `tools/normalization.py` como agregador de comunidad (prioridad 5, misma que Madrid Secreto).
- Ajustes de calidad aplicados en Meetup: se filtro events con `lat` lejana a Madrid (>2 grados, tipicamente eventos online globales), se infirieron categorias automaticas (Tecnologia, Networking, Idiomas, Deportes, Baile, Musica, Arte y Cultura, Bienestar, Ocio, Social) a partir de titulo y grupo, y se limpio el HTML de descripciones.
- Validacion real del output de Meetup: `407` planes normalizados en `outputs/eventos_meetup.json`, con `363` coordenadas, `35` con precio y `0` gratuitos declarados.
- Se creo la primera version del frontend web en `frontend/index.html`: SPA estatica con dark theme, grid de tarjetas filtrables, sidebar con filtros de categoria/fuente/precio/fecha, buscador de texto, vista de mapa Leaflet con tiles Carto oscuros, tab de noticias, paginacion incremental y boton scroll-to-top.
- Se creo `serve.py` como servidor de desarrollo local que sirve `frontend/` y `outputs/` bajo un mismo origen para evitar problemas de CORS.
- El frontend lee directamente `outputs/eventos_madrid_all.json` y `outputs/noticias_madrid_all.json` y renderiza todo en cliente con JS vanilla, sin dependencias de build.
- Estado del frontend v1: funcional y visualmente atractivo en desktop y movil, con ~3400 eventos cargados y filtros interactivos. Pendiente: integrar los nuevos scrapers en el merge `all` regenerando `scrape_all.py`.

### 2026-04-13 (frontend v2 y recompocision)

- Se rediseño por completo `frontend/` hacia un flujo de discovery mas orientado a producto: hero editorial, presets por mood, shelves rapidos (`Para hoy`, `Este finde`, `Gratis o muy faciles`, `Con senal de grupo`), vista de tarjetas + mapa, shortlist persistente en `localStorage` y modal de detalle para cada plan.
- La nueva UI se reorganizo en assets separados (`frontend/index.html`, `frontend/styles.css`, `frontend/app.js`, `frontend/favicon.svg`) para simplificar iteracion y validacion sin meter tooling de build.
- La decision de producto elegida para esta iteracion fue un explorador por `moods + shortlist`, porque oculta mejor la fragmentacion real de categorias y deja preparada la futura capa de comparacion entre amigos sin imponer todavia embeddings ni matching complejo en el frontend.
- Se anadio compatibilidad de favicon al servidor local: `serve.py` ahora responde tambien a `/favicon.ico` sirviendo `frontend/favicon.svg`, eliminando el `404` que salia en las pruebas del navegador.
- Se detecto una inconsistencia de entorno en Windows/Python 3.13: `ZoneInfo("Europe/Madrid")` fallaba sin base IANA local. Se soluciono a nivel de dependencia anadiendo `tzdata==2026.1` a `requirements.txt` e instalando el paquete en la `.venv`.
- Se anadio `tools/rebuild_feeds.py` para recomponer `outputs/eventos_madrid_all.json`, `outputs/noticias_madrid_all.json` y `outputs/pipeline_diario.json` a partir de los JSON de fuente ya existentes, sin necesidad de re-scrapear todo el stack.
- Se anadio `tools/smoke_frontend.py` como smoke test minimo de runtime: levanta un servidor temporal y valida `index.html`, `app.js`, `styles.css`, `favicon.ico` y ambos feeds web.
- Se regeneraron las fuentes afectadas por la auditoria reciente: `RockTheSport` paso de `68` a `61` planes validos tras filtrar mejor formaciones/online, y `Meetup` quedo en `401` planes aceptados tras descartar `82` nodos online o fuera de Madrid. `esMadrid` se intento refrescar tambien, pero mantuvo ejecucion larga con algunos `403` puntuales en detalle; para el merge final se reutilizo el output validado ya presente (`241` planes).
- Recompocision final de feeds web con `tools/rebuild_feeds.py`: `outputs/eventos_madrid_all.json` queda en `3832` planes validos y `outputs/noticias_madrid_all.json` en `137` noticias validas.
- Verificacion de cobertura tras la recompocision: el feed final ya expone `20` fuentes de planes, incluyendo `398` planes de `Meetup` y `61` de `RockTheSport`, que antes no estaban presentes en la capa `all` usada por la web.
- Validacion automatica del frontend v2: `tools/smoke_frontend.py` devolvio `ok=true`, `3832` planes y `137` noticias. En verificacion visual adicional, la home cargo correctamente, renderizo `4` shelves editoriales, mostro `24` tarjetas iniciales, activo la shortlist y dibujo `2646` marcadores en el mapa.
- Ajuste de copy posterior en frontend: se retiraron del hero los contadores publicos (`planes listos`, `gratis`, etc.) y los bloques que explicaban decisiones internas de producto o pasos futuros; ese contexto queda documentado en `STATUS.md` y no en la interfaz publica.

### 2026-04-13 (madplan pulse ux)

- Se reoriento la interfaz publica a `MadPlan | Madrid en vivo`: `frontend/app.js` se reemplazo por un controller nuevo con theming por franja (`morning`, `afternoon`, `night`), ranking por cercania temporal y estado compartible via query params (`q`, `mood`, `day`, `pulse`, `source`, `category`, `price`, `sort`, `view`).
- Se reforzo la idea de relevancia temporal en la UI con filtros Madrid-native (`Hoy`, `Esta noche`, `Este finde`, `De mananeo`, `Al fresquito`, `Gratis total`), nuevos shelves rapidos, randomizador `Tirada de dados`, shortlist persistente y boton `Copiar vista`.
- Se audito la calidad geografica del feed final y aparecieron `87` outliers de coordenadas (dominados por `Eventbrite` y `RockTheSport`). En vez de mutar el feed origen, el frontend ahora aplica una envolvente estricta de Madrid ciudad y solo usa puntos city-safe para tarjetas y mapa.
- Se activaron smart cards reales para planes mergeados: `tools/normalization.py` ya conservaba `metadata.source_links`, se recompusieron los feeds con `tools/rebuild_feeds.py` y `outputs/eventos_madrid_all.json` pasa a exponer enlaces por fuente en el `100%` de los planes (`3783` con `1` acceso, `48` con `2`, `1` con `3`).
- La capa visual se amplio en `frontend/styles.css` con acentos por fuente, badges de confianza (`Fuente oficial`, `Agenda publica`, `Varias fuentes`, `Agregador`), comparacion de accesos, portadas generadas para planes sin imagen y pulso visual distinto por manana, tarde y noche.
- Se completo la capa mapa con `leaflet.markercluster`, clusters reales, tarjetas de pulso por barrio (`Lavapies`, `Legazpi`, `Malasana`, `La Latina`, `Salamanca`, etc.) y listado lateral sincronizado con los puntos geocodificados limpios.
- Se alineo la validacion automatica con el rebrand: `tools/smoke_frontend.py` ya comprueba `MadPlan` y `share-view`; el smoke paso de nuevo tras la recomposicion con `3832` planes y `136` noticias.
- Validacion final en navegador sobre `http://127.0.0.1:8000/`: el estado inicial mostro `3745` planes city-safe y `2559` puntos limpios de mapa; tambien se validaron `Gratis total`, `De mananeo`, `Tirada de dados`, la vista de mapa clusterizada y un caso real de tarjeta mergeada (`Museo de la Felicidad`) con comparacion `Madrid Secreto 14 EUR` frente a `Fever 16 EUR`.