#!/usr/bin/env python3
"""
Normalize event categories into a fixed taxonomy for MadPlan.

Canonical categories (a plan can belong to more than one):
  - Música y Conciertos
  - Arte y Exposiciones
  - Teatro y Danza
  - Cine
  - Gastronomía
  - Deportes y Aventura
  - Vida Nocturna
  - Familia e Infantil
  - Talleres y Cursos
  - Conferencias y Charlas
  - Naturaleza y Aire Libre
  - Bienestar y Salud
  - Visitas y Rutas
  - Ciencia y Tecnología
  - Mercados y Ferias
  - Comunidad y Social
  - Lectura y Literatura
  - Ocio y Entretenimiento

On first run: processes ALL records.
On subsequent runs: only processes records without `categorias_normalizadas`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS_FILE = ROOT / "outputs" / "eventos_madrid_all.json"
NEWS_FILE = ROOT / "outputs" / "noticias_madrid_all.json"

CANONICAL_CATEGORIES = [
    "Música y Conciertos",
    "Arte y Exposiciones",
    "Teatro y Danza",
    "Cine",
    "Gastronomía",
    "Deportes y Aventura",
    "Vida Nocturna",
    "Familia e Infantil",
    "Talleres y Cursos",
    "Conferencias y Charlas",
    "Naturaleza y Aire Libre",
    "Bienestar y Salud",
    "Visitas y Rutas",
    "Ciencia y Tecnología",
    "Mercados y Ferias",
    "Comunidad y Social",
    "Lectura y Literatura",
    "Ocio y Entretenimiento",
]

# Mapping rules: keyword patterns -> canonical categories
# Each rule is (compiled_regex, canonical_category)
# Order matters: more specific rules first
_RULES: list[tuple[re.Pattern, str]] = []


def _add(pattern: str, category: str):
    _RULES.append((re.compile(pattern, re.IGNORECASE), category))


# ── Music ──
_add(r"\b(m[uú]sica|concierto|concert|live music|festival\b.*music|candlelight|sinf[oó]ni|orquest|jazz|blues|rock|pop|hip.?hop|rap|electr[oó]ni|techno|dj\b|disco\b|reggae|flamenco|fado|coral|coro\b|ac[uú]stic|karaoke|open\s*mic|jam\s*session|recital(?!\s*(liter|poes)))", "Música y Conciertos")
_add(r"\b(wegow|sala_el_sol|rockthesport)\b", "Música y Conciertos")
_add(r"\bconciertos?\s+candlelight\b", "Música y Conciertos")

# ── Art & Exhibitions ──
_add(r"\b(arte|exposici[oó]n|exhibiti|galer[ií]a|museum|museo|pintura|escultura|fotograf[ií]a|instalaci[oó]n art|muestra|retrospectiva|obra\b.*arte|artes\s+visuales|grabado|cer[aá]mica|dibujo|ilustraci[oó]n|art\b)", "Arte y Exposiciones")

# ── Theatre & Dance ──
_add(r"\b(teatro|danza|ballet|performance|escen|comedia|drama|monólogo|mon[oó]logo|impro|circo|zarzuela|[oó]pera|espect[aá]culo|coreograf|contempor[aá]ne|musical\b)", "Teatro y Danza")

# ── Cinema ──
_add(r"\b(cine|pel[ií]cula|film|cortometraje|documental|audiovisual|cinemat|proyecci[oó]n)", "Cine")

# ── Gastronomy ──
_add(r"\b(gastronom|cocina|comida|tapas?|ruta\s*(gastro|tapa)|restaurante|chef|cata\b|cena|degustaci|brunch|mercado\s*gastro|wine|vino|cervez|maridaje|food|bebida|gastr|culinari|sabor)", "Gastronomía")

# ── Sports & Adventure ──
_add(r"\b(deporte|sport|f[uú]tbol|baloncesto|tenis|padel|running|marat[oó]n|ciclism|bici|escala|senderism|trail|athletic|nataci|fitness|yoga(?!.*medit)|crossfit|boxe|mma|artes?\s*marcial|aventura|kayak|surf|patinaj)", "Deportes y Aventura")

# ── Nightlife ──
_add(r"\b(fiesta|party|noctur|noche\b|clubbing|discoteca|afterwork|ocio\s*nocturno|nightlife|after\s*party|verbena)", "Vida Nocturna")

# ── Family & Kids ──
_add(r"\b(famili|infantil|ni[ñn]o|cuentacuento|t[ií]tere|marioneta|magi[ac]|parque\s*infantil|animaci[oó]n|bebé|maternal|pediatr|ludoteca|circo\s*infantil)", "Familia e Infantil")

# ── Workshops & Courses ──
_add(r"\b(taller|curso|workshop|formaci[oó]n|masterclass|clase\b|apren|seminario|tutorial|handmade|manualidad|bricolaj|crafts?)", "Talleres y Cursos")

# ── Conferences & Talks ──
_add(r"\b(conferencia|charla|coloquio|debate|ponencia|mesa\s*redonda|simposio|congreso|foro|keynote|ted\b|presentaci[oó]n\s*(libro|libr))", "Conferencias y Charlas")

# ── Nature & Outdoors ──
_add(r"\b(naturaleza|aire\s*libre|outdoor|jard[ií]n|parque(?!\s*infantil)|retiro|excursi[oó]n|campo|bot[aá]nic|sierr|monta[ñn]|ruta\s*(verde|natural|senderis)|picnic|observaci[oó]n\s*(aves|estrellas))", "Naturaleza y Aire Libre")

# ── Wellness & Health ──
_add(r"\b(bienestar|salud|wellness|meditaci[oó]n|mindful|spa\b|relax|terap|holistic|pilates|reiki|masaje|belleza|nutrici)", "Bienestar y Salud")

# ── Tours & Visits ──
_add(r"\b(visita|ruta(?!\s*(gastro|tapa|verde|natural|senderis))|itinerari|tour\b|paseo|guid|recorrid|patrimon|monumental|histori)", "Visitas y Rutas")

# ── Science & Technology ──
_add(r"\b(ciencia|tecnolog|tech|innova|startup|hacker|program|c[oó]dig|robot|inteligencia\s*artificial|ia\b|machine\s*learn|data|digital|maker|stem\b|laborat|experiment)", "Ciencia y Tecnología")

# ── Markets & Fairs ──
_add(r"\b(mercad(?!o\s*gastro)|feria|pop\s*up|vintage|rastro|mercadillo|expositor|stand\b|showroom|bazar)", "Mercados y Ferias")

# ── Community & Social ──
_add(r"\b(comunidad|social|volunteer|solidari|ong\b|asociaci|network|meetup|encuentro|intercambio|idiom)", "Comunidad y Social")

# ── Reading & Literature ──
_add(r"\b(lectura|literatur|libro|poes[ií]a|poet|cuentos?(?!\s*cuento)|narrati|escritor|autor|novela|editorial|bibliote|club\s*de\s*lectura|recital\s*(liter|poes))", "Lectura y Literatura")

# ── Catch-all for source-specific ──
_add(r"\b(programacion\s*destacada|1ciudad21distritos|que\s*hacer)\b", "Ocio y Entretenimiento")
_add(r"\b(actividad|event|ocio|entretenimiento|espectáculo|show)\b", "Ocio y Entretenimiento")


MAX_CATEGORIES = 3


def classify_event(event: dict) -> list[str]:
    """Return list of canonical categories for an event (max MAX_CATEGORIES).

    Uses a two-tier approach:
      - Tier 1 (strong): title, subtitle, original categories, tags, source
      - Tier 2 (weak): resumen + descripcion (only used to fill if tier 1 < 2)
    """
    # Tier 1: strong-signal text
    strong_parts = [
        event.get("titulo", ""),
        event.get("subtitulo", ""),
        event.get("lugar", ""),
    ]
    for c in event.get("categorias", []):
        strong_parts.append(c)
    for t in event.get("etiquetas", []):
        strong_parts.append(t)
    cp = event.get("categoria_principal", "")
    if cp:
        strong_parts.append(cp)
    fuente = event.get("fuente", "")
    strong_parts.append(fuente)
    strong_blob = " ".join(str(p) for p in strong_parts if p)

    # Tier 2: weak-signal text (description/summary)
    weak_blob = " ".join(
        str(event.get(k, "")) for k in ("resumen", "descripcion")
    )

    matched: list[str] = []
    seen: set[str] = set()

    # Pass 1: match on strong blob
    for pattern, category in _RULES:
        if category in seen:
            continue
        if pattern.search(strong_blob):
            matched.append(category)
            seen.add(category)

    # Pass 2: if we have < 2 categories, try weak blob
    if len(matched) < 2 and weak_blob.strip():
        for pattern, category in _RULES:
            if category in seen:
                continue
            if pattern.search(weak_blob):
                matched.append(category)
                seen.add(category)
            if len(matched) >= 2:
                break

    # Fallback
    if not matched:
        matched.append("Ocio y Entretenimiento")

    # Remove "Ocio y Entretenimiento" if there are more specific categories
    if len(matched) > 1 and "Ocio y Entretenimiento" in matched:
        matched = [c for c in matched if c != "Ocio y Entretenimiento"]

    return matched[:MAX_CATEGORIES]


def normalize_categories(events: list[dict], *, force_all: bool = False) -> int:
    """Normalize categories on events. Returns count of modified events."""
    count = 0
    for event in events:
        if not force_all and event.get("categorias_normalizadas"):
            continue
        cats = classify_event(event)
        event["categorias_normalizadas"] = cats
        event["categoria_principal_norm"] = cats[0]
        count += 1
    return count


def run(force_all: bool = False):
    # Events
    events = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    n_events = normalize_categories(events, force_all=force_all)
    EVENTS_FILE.write_text(
        json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Events: normalized {n_events}/{len(events)}")

    # News
    news = json.loads(NEWS_FILE.read_text(encoding="utf-8"))
    n_news = normalize_categories(news, force_all=force_all)
    NEWS_FILE.write_text(
        json.dumps(news, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"News: normalized {n_news}/{len(news)}")


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    run(force_all=force)
