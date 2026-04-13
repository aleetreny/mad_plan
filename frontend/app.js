(function () {
  "use strict";

  const DATA_URL = "outputs/eventos_madrid_all.json";
  const NEWS_URL = "outputs/noticias_madrid_all.json";
  const PAGE_SIZE = 24;
  const SHELF_SIZE = 8;
  const TOP_CATEGORY_CHIPS = 16;
  const TOP_SOURCE_CHIPS = 18;
  const NEWS_ITEMS = 6;
  const STORAGE_KEY = "madPlanShortlistV2";
  const DAY_MS = 24 * 60 * 60 * 1000;
  const MADRID_CENTER = [40.4168, -3.7038];
  const MADRID_CITY_BOUNDS = {
    latMin: 40.3,
    latMax: 40.57,
    lonMin: -3.84,
    lonMax: -3.54
  };

  const SOURCE_LABELS = {
    datos_madrid: "Datos Madrid",
    esmadrid: "esMadrid",
    fever: "Fever",
    eventbrite: "Eventbrite",
    wegow: "Wegow",
    ticketmaster: "Ticketmaster",
    madrid_secreto: "Madrid Secreto",
    timeout: "Time Out",
    matadero: "Matadero",
    teatros_canal: "Teatros del Canal",
    circulo_bellas_artes: "Circulo",
    ifema_madrid: "IFEMA",
    casa_mexico: "Casa de Mexico",
    espacio_fundacion_telefonica: "Fundacion Telefonica",
    museo_reina_sofia: "Reina Sofia",
    biblioteca_nacional: "BNE",
    fundacion_canal: "Fundacion Canal",
    fundacion_mapfre: "Mapfre",
    sala_el_sol: "Sala El Sol",
    gacetin_madrid: "El Gacetin",
    rockthesport: "RockTheSport",
    meetup: "Meetup"
  };

  const SOURCE_META = {
    matadero: { color: "#3c8a57", type: "official" },
    teatros_canal: { color: "#d45b3f", type: "official" },
    circulo_bellas_artes: { color: "#2d6f95", type: "official" },
    ifema_madrid: { color: "#0f766e", type: "official" },
    casa_mexico: { color: "#d06a2f", type: "official" },
    espacio_fundacion_telefonica: { color: "#1f5f9a", type: "official" },
    museo_reina_sofia: { color: "#c93c3c", type: "official" },
    biblioteca_nacional: { color: "#8f6a2a", type: "official" },
    fundacion_canal: { color: "#267c74", type: "official" },
    fundacion_mapfre: { color: "#bf4f2f", type: "official" },
    sala_el_sol: { color: "#202a5f", type: "official" },
    datos_madrid: { color: "#536d83", type: "public" },
    esmadrid: { color: "#0a7b79", type: "public" },
    fever: { color: "#eb6b4b", type: "aggregator" },
    eventbrite: { color: "#f16843", type: "aggregator" },
    wegow: { color: "#264f88", type: "aggregator" },
    ticketmaster: { color: "#3557a1", type: "aggregator" },
    rockthesport: { color: "#2f9d6f", type: "aggregator" },
    meetup: { color: "#d6434f", type: "aggregator" },
    madrid_secreto: { color: "#6a5d44", type: "editorial" },
    timeout: { color: "#ad5530", type: "editorial" },
    gacetin_madrid: { color: "#7d5e2d", type: "editorial" }
  };

  const PRIMARY_SOURCES = new Set([
    "matadero",
    "teatros_canal",
    "circulo_bellas_artes",
    "ifema_madrid",
    "casa_mexico",
    "espacio_fundacion_telefonica",
    "museo_reina_sofia",
    "biblioteca_nacional",
    "fundacion_canal",
    "fundacion_mapfre",
    "sala_el_sol"
  ]);

  const PUBLIC_SOURCES = new Set(["datos_madrid", "esmadrid"]);

  const BARRIO_ZONES = [
    { id: "malasana", label: "Malasana", center: [40.4266, -3.7043], radiusKm: 0.85, color: "#eb6b4b", copy: "conciertos, salas y agenda al salir de trabajar" },
    { id: "lavapies", label: "Lavapies", center: [40.4088, -3.7003], radiusKm: 0.95, color: "#0e7490", copy: "cine, escena, comida y mezcla de barrio" },
    { id: "latina", label: "La Latina", center: [40.4101, -3.711], radiusKm: 0.8, color: "#d6a13f", copy: "paseo, tapeo cultural y plan facil de cuadrar" },
    { id: "chamberi", label: "Chamberi", center: [40.4342, -3.7016], radiusKm: 1.1, color: "#3b82f6", copy: "charlas, expos y agenda de tarde" },
    { id: "salamanca", label: "Salamanca", center: [40.4258, -3.6845], radiusKm: 1.0, color: "#2f9d6f", copy: "expo, museo y plan tranquilo" },
    { id: "usera", label: "Usera", center: [40.3876, -3.7072], radiusKm: 1.35, color: "#1f7a63", copy: "festivales, deporte y barrios con pulso propio" },
    { id: "legazpi", label: "Legazpi", center: [40.3917, -3.6948], radiusKm: 1.0, color: "#c95d40", copy: "Matadero, exterior y plan cultural con aire" }
  ];

  const SLOT_CONFIG = {
    morning: { label: "Dawn Gold", eyebrow: "Madrid en vivo · manana", accent: "#d6a13f" },
    afternoon: { label: "Retiro Green", eyebrow: "Madrid en vivo · tarde", accent: "#2f9d6f" },
    night: { label: "Gran Via Neon", eyebrow: "Madrid en vivo · noche", accent: "#1aa8d8" }
  };

  const MOODS = [
    {
      id: "visual",
      label: "Ver algo bonito",
      blurb: "Exposiciones, museos, foto y diseno.",
      short: "Visual",
      accent: "#eb6b4b",
      categories: ["exposiciones", "arte", "artes", "museo", "museos", "fotografia", "diseno", "arquitectura", "ferias y congresos"],
      keywords: ["expo", "exposicion", "museo", "galeria", "fotografia", "instalacion", "diseno", "comisariada"]
    },
    {
      id: "afterwork",
      label: "Salir con amigos",
      blurb: "Conciertos, comunidad, clubs y social.",
      short: "Grupo",
      accent: "#0e7490",
      categories: ["musica", "conciertos", "ocio", "comunidad", "social", "actividades"],
      keywords: ["concierto", "dj", "jam", "club", "networking", "meetup", "afterwork", "social", "fiesta", "micro abierto", "teatro"]
    },
    {
      id: "learn",
      label: "Aprender algo",
      blurb: "Charlas, talleres, ideas y tecnologia.",
      short: "Ideas",
      accent: "#3b82f6",
      categories: ["cursos talleres", "conferencias coloquios", "literatura", "tecnologia", "programacion destacada agenda cultura", "ciencia"],
      keywords: ["taller", "charla", "conferencia", "coloquio", "masterclass", "workshop", "tecnologia", "data", "inteligencia artificial", "lectura"]
    },
    {
      id: "move",
      label: "Mover el cuerpo",
      blurb: "Deporte, baile, carreras y aire libre.",
      short: "Mover",
      accent: "#2f9d6f",
      categories: ["deportes", "baile", "bienestar"],
      keywords: ["running", "trail", "ciclismo", "triatlon", "duatlon", "cross", "senderismo", "dance", "salsa", "bachata", "yoga", "pilates", "fitness"]
    },
    {
      id: "family",
      label: "Con peques",
      blurb: "Infantil, cuentacuentos y planes familiares.",
      short: "Familia",
      accent: "#d6a13f",
      categories: ["familia", "cuentacuentos titeres marionetas", "infantil"],
      keywords: ["familia", "infantil", "ninos", "ninas", "titeres", "marionetas", "cuentacuentos", "peques", "bebes"]
    },
    {
      id: "calm",
      label: "Plan tranquilo",
      blurb: "Cine, visitas, paseos y cultura con menos ruido.",
      short: "Calma",
      accent: "#5470a8",
      categories: ["cine", "excursiones itinerarios visitas", "cultura", "bienestar"],
      keywords: ["cine", "visita", "paseo", "poesia", "biblioteca", "meditacion", "documental", "recorrido", "mesa redonda"]
    }
  ];

  const MOOD_BY_ID = Object.fromEntries(MOODS.map((mood) => [mood.id, mood]));

  const state = {
    allPlans: [],
    allNews: [],
    filteredPlans: [],
    activeMood: null,
    activeDay: null,
    activePulse: null,
    activeSource: null,
    activeCategory: null,
    activePrice: null,
    search: "",
    sortBy: "smart",
    view: "cards",
    page: 1,
    savedIds: loadSavedIds(),
    slotId: getCurrentSlotId(new Date()),
    map: null,
    markers: null,
    zoneLayer: null,
    zoneFocus: null
  };

  const elements = {
    body: document.body,
    searchInput: document.getElementById("search-input"),
    surpriseButton: document.getElementById("surprise-button"),
    clearAllFilters: document.getElementById("clear-all-filters"),
    moodGrid: document.getElementById("mood-grid"),
    shelves: document.getElementById("shelves"),
    resultsSummary: document.getElementById("results-summary"),
    activeFilters: document.getElementById("active-filters"),
    resultsGrid: document.getElementById("results-grid"),
    loadMore: document.getElementById("load-more"),
    emptyState: document.getElementById("empty-state"),
    sourceCloud: document.getElementById("source-cloud"),
    categoryCloud: document.getElementById("category-cloud"),
    priceCloud: document.getElementById("price-cloud"),
    quickFilters: document.getElementById("quick-filters"),
    sortSelect: document.getElementById("sort-select"),
    shareView: document.getElementById("share-view"),
    savedList: document.getElementById("saved-list"),
    copyShortlist: document.getElementById("copy-shortlist"),
    savedCountPill: document.getElementById("saved-count-pill"),
    newsList: document.getElementById("news-list"),
    newsCountPill: document.getElementById("news-count-pill"),
    viewSwitch: document.getElementById("view-switch"),
    mapShell: document.getElementById("map-shell"),
    mapCanvas: document.getElementById("map-canvas"),
    mapList: document.getElementById("map-list"),
    zonePulse: document.getElementById("zone-pulse"),
    modal: document.getElementById("plan-modal"),
    modalBody: document.getElementById("plan-modal-body"),
    scrollTop: document.getElementById("scroll-top"),
    jumpExplorer: document.getElementById("jump-explorer"),
    jumpMap: document.getElementById("jump-map"),
    jumpShortlist: document.getElementById("jump-shortlist"),
    heroSlotLabel: document.getElementById("hero-slot-label")
  };

  hydrateStateFromUrl();

  function loadSavedIds() {
    try {
      const parsed = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "[]");
      return new Set(Array.isArray(parsed) ? parsed : []);
    } catch {
      return new Set();
    }
  }

  function persistSavedIds() {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(state.savedIds)));
  }

  function sourceMeta(key) {
    const meta = SOURCE_META[key] || {};
    return {
      color: meta.color || "#153047",
      type: meta.type || (PRIMARY_SOURCES.has(key) ? "official" : "aggregator")
    };
  }

  function sourceLabel(key) {
    return SOURCE_LABELS[key] || key || "Fuente";
  }

  function escHtml(value) {
    const div = document.createElement("div");
    div.textContent = value || "";
    return div.innerHTML;
  }

  function normalizeText(value) {
    return String(value || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  }

  function hexToRgba(hex, alpha) {
    const value = hex.replace("#", "");
    const bigint = Number.parseInt(value, 16);
    const red = (bigint >> 16) & 255;
    const green = (bigint >> 8) & 255;
    const blue = bigint & 255;
    return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
  }

  function truncate(text, maxLength) {
    const clean = String(text || "").replace(/\s+/g, " ").trim();
    if (clean.length <= maxLength) {
      return clean;
    }
    return `${clean.slice(0, maxLength - 1)}...`;
  }

  function parseDateish(value, fallbackHour) {
    if (!value) {
      return null;
    }
    const text = String(value).trim();
    if (!text) {
      return null;
    }
    const withTime = text.length === 10 ? `${text}T${fallbackHour || "12:00:00"}` : text;
    const parsed = new Date(withTime);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function startOfDay(date) {
    const copy = new Date(date);
    copy.setHours(0, 0, 0, 0);
    return copy;
  }

  function endOfDay(date) {
    const copy = new Date(date);
    copy.setHours(23, 59, 59, 999);
    return copy;
  }

  function addDays(date, amount) {
    const copy = new Date(date);
    copy.setDate(copy.getDate() + amount);
    return copy;
  }

  function dayKey(date) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  }

  function formatDate(date) {
    return date ? date.toLocaleDateString("es-ES", { day: "numeric", month: "short" }) : "";
  }

  function formatLongDate(date) {
    return date ? date.toLocaleDateString("es-ES", { weekday: "short", day: "numeric", month: "short" }) : "";
  }

  function formatTime(value) {
    if (!value || !String(value).includes("T")) {
      return "";
    }
    const parsed = parseDateish(value);
    if (!parsed) {
      return "";
    }
    const hours = parsed.getHours();
    const minutes = parsed.getMinutes();
    if ((hours === 0 && minutes === 0) || (hours === 23 && minutes === 59)) {
      return "";
    }
    return parsed.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
  }

  function formatMoney(value, currency) {
    if (value == null || Number.isNaN(Number(value))) {
      return "Consultar";
    }
    return `${Number(value).toFixed(0)} ${currency || "EUR"}`;
  }

  function formatPrice(plan) {
    if (plan._isFree) {
      return "Gratis";
    }
    if (plan.precio != null && !Number.isNaN(Number(plan.precio))) {
      return formatMoney(plan.precio, plan.moneda);
    }
    return "Consultar";
  }

  function formatLinkPrice(link) {
    if (link.es_gratis === true || (link.precio != null && Number(link.precio) === 0)) {
      return "Gratis";
    }
    if (link.precio != null && !Number.isNaN(Number(link.precio))) {
      return formatMoney(link.precio, link.moneda);
    }
    return link.kind === "compra" ? "Entradas" : "Abrir";
  }

  function getCurrentSlotId(referenceDate) {
    const hour = referenceDate.getHours();
    if (hour >= 6 && hour < 13) {
      return "morning";
    }
    if (hour >= 13 && hour < 20) {
      return "afternoon";
    }
    return "night";
  }

  function applyTimeTheme() {
    const slot = SLOT_CONFIG[state.slotId] || SLOT_CONFIG.afternoon;
    elements.body.dataset.slot = state.slotId;
    if (elements.heroSlotLabel) {
      elements.heroSlotLabel.textContent = slot.eyebrow;
    }
  }

  function normalizeSourceLinks(plan) {
    const rawLinks = Array.isArray(plan.metadata && plan.metadata.source_links) ? plan.metadata.source_links : [];
    const links = [];
    const seen = new Set();

    rawLinks.forEach((link) => {
      if (!link || !link.url || !link.fuente) {
        return;
      }
      const key = `${String(link.fuente).toLowerCase()}::${String(link.url).toLowerCase()}`;
      if (seen.has(key)) {
        return;
      }
      seen.add(key);
      links.push({
        fuente: link.fuente,
        url: link.url,
        kind: link.kind || "detalle",
        precio: link.precio != null ? Number(link.precio) : null,
        moneda: link.moneda || null,
        es_gratis: link.es_gratis === true || (link.precio != null && Number(link.precio) === 0)
      });
    });

    if (!links.length) {
      const fallbackUrl = (plan.url_compra || plan.url || plan.url_articulo || "").trim();
      if (fallbackUrl) {
        links.push({
          fuente: plan.fuente,
          url: fallbackUrl,
          kind: plan.url_compra ? "compra" : "detalle",
          precio: plan.precio != null ? Number(plan.precio) : null,
          moneda: plan.moneda || null,
          es_gratis: plan.es_gratis === true || (plan.precio != null && Number(plan.precio) === 0)
        });
      }
    }

    return links.sort((left, right) => {
      const leftMeta = sourceMeta(left.fuente);
      const rightMeta = sourceMeta(right.fuente);
      const typeRank = { official: 0, public: 1, editorial: 2, aggregator: 3 };
      if (typeRank[leftMeta.type] !== typeRank[rightMeta.type]) {
        return typeRank[leftMeta.type] - typeRank[rightMeta.type];
      }
      if (left.kind !== right.kind) {
        return left.kind === "compra" ? -1 : 1;
      }
      if (left.es_gratis !== right.es_gratis) {
        return Number(right.es_gratis) - Number(left.es_gratis);
      }
      if (left.precio != null && right.precio != null && left.precio !== right.precio) {
        return left.precio - right.precio;
      }
      return sourceLabel(left.fuente).localeCompare(sourceLabel(right.fuente), "es");
    });
  }

  function primaryLink(plan) {
    return plan._sourceLinks[0] ? plan._sourceLinks[0].url : (plan.url_compra || plan.url || plan.url_articulo || "#");
  }

  function getMoodMatches(plan) {
    const matches = MOODS.filter((mood) => {
      const categoryMatch = mood.categories.some((token) => plan._text.includes(normalizeText(token)));
      const keywordMatch = mood.keywords.some((token) => plan._text.includes(normalizeText(token)));
      return categoryMatch || keywordMatch;
    }).map((mood) => mood.id);

    if (!matches.length) {
      if (plan._text.includes("cine") || plan._text.includes("visita") || plan._text.includes("biblioteca")) {
        matches.push("calm");
      } else if (plan._text.includes("charla") || plan._text.includes("conferencia")) {
        matches.push("learn");
      } else {
        matches.push("afterwork");
      }
    }

    return Array.from(new Set(matches));
  }

  function isWithinMadridBounds(lat, lon) {
    return lat >= MADRID_CITY_BOUNDS.latMin
      && lat <= MADRID_CITY_BOUNDS.latMax
      && lon >= MADRID_CITY_BOUNDS.lonMin
      && lon <= MADRID_CITY_BOUNDS.lonMax;
  }

  function distanceKm(leftLat, leftLon, rightLat, rightLon) {
    const toRad = (value) => value * Math.PI / 180;
    const dLat = toRad(rightLat - leftLat);
    const dLon = toRad(rightLon - leftLon);
    const a = Math.sin(dLat / 2) ** 2
      + Math.cos(toRad(leftLat)) * Math.cos(toRad(rightLat)) * Math.sin(dLon / 2) ** 2;
    return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function detectZone(plan) {
    if (plan._lat == null || plan._lon == null || !plan._mapEligible) {
      return null;
    }
    let bestZone = null;
    let bestDistance = Number.POSITIVE_INFINITY;
    BARRIO_ZONES.forEach((zone) => {
      const distance = distanceKm(zone.center[0], zone.center[1], plan._lat, plan._lon);
      if (distance <= zone.radiusKm && distance < bestDistance) {
        bestZone = zone;
        bestDistance = distance;
      }
    });
    return bestZone;
  }

  function inferOutdoorHint(plan) {
    const text = plan._text;
    return [
      "parque",
      "jardin",
      "terraza",
      "al aire libre",
      "outdoor",
      "trail",
      "running",
      "ruta",
      "senderismo",
      "recinto ferial",
      "plaza",
      "festival",
      "mercado"
    ].some((token) => text.includes(normalizeText(token)));
  }

  function buildCoverCode(plan) {
    if (plan.fuente === "rockthesport") return "RUN";
    if (plan.fuente === "meetup") return "MEET";
    if (plan._primaryMood === "visual") return "ART";
    if (plan._primaryMood === "move") return "MOVE";
    if (plan._primaryMood === "family") return "KIDS";
    if (plan._primaryMood === "learn") return "TALK";
    if (plan._primaryMood === "calm") return "CINE";
    return "LIVE";
  }

  function getTrustInfo(plan) {
    if (plan._officialSources.length) return { label: "Fuente oficial", tone: "official" };
    if (plan._publicSources.length) return { label: "Agenda publica", tone: "public" };
    if (plan._sourceLinks.length > 1) return { label: "Varias fuentes", tone: "mixed" };
    return { label: "Agregador", tone: "aggregator" };
  }

  function getGroupScore(plan) {
    let score = 0;
    if (plan._moods.includes("afterwork")) score += 3;
    if (plan._moods.includes("move")) score += 2;
    if (plan._moods.includes("family")) score += 1;
    if (plan._text.includes("networking") || plan._text.includes("social") || plan._text.includes("festival") || plan._text.includes("meetup")) score += 2;
    if (plan._isFree) score += 1;
    if (plan._hasLocation) score += 1;
    return score;
  }

  function matchesDayPreset(plan, preset) {
    if (!preset) return true;

    const today = startOfDay(new Date());
    let range;

    switch (preset) {
      case "today":
        range = { start: today, end: endOfDay(today) };
        break;
      case "tomorrow": {
        const tomorrow = addDays(today, 1);
        range = { start: startOfDay(tomorrow), end: endOfDay(tomorrow) };
        break;
      }
      case "week":
        range = { start: today, end: endOfDay(addDays(today, 7)) };
        break;
      case "weekend": {
        const day = today.getDay();
        if (day === 6) {
          range = { start: today, end: endOfDay(addDays(today, 1)) };
        } else if (day === 0) {
          range = { start: today, end: endOfDay(today) };
        } else {
          const saturday = addDays(today, 6 - day);
          range = { start: startOfDay(saturday), end: endOfDay(addDays(saturday, 1)) };
        }
        break;
      }
      case "tonight": {
        const nightStart = new Date(today);
        nightStart.setHours(19, 0, 0, 0);
        const nightEnd = addDays(today, 1);
        nightEnd.setHours(3, 59, 59, 999);
        const planStart = plan._rangeStart || plan._nextDate;
        const planEnd = plan._rangeEnd || planStart;
        if (!planStart) return false;
        if (plan._hasExplicitTime) return planEnd >= nightStart && planStart <= nightEnd;
        return dayKey(planStart) === dayKey(today) && plan._isNightFriendly;
      }
      default:
        return true;
    }

    const planStart = plan._rangeStart || plan._nextDate;
    const planEnd = plan._rangeEnd || planStart;
    if (!planStart) return false;
    return planEnd >= range.start && planStart <= range.end;
  }

  function matchesPulsePreset(plan, preset) {
    if (!preset) return true;
    if (preset === "mananeo") {
      return plan._startsBefore14 || (!plan._hasExplicitTime && ["visual", "family", "learn"].includes(plan._primaryMood));
    }
    if (preset === "fresquito") {
      const month = new Date().getMonth();
      const isSummer = month >= 5 && month <= 8;
      return plan._isOutdoorHint || (isSummer && plan._isNightFriendly) || (plan._isNightFriendly && plan._text.includes("terraza"));
    }
    return true;
  }

  function getAvailabilityLabel(plan) {
    if (!plan._nextDate) return "Sin fecha clara";
    const today = startOfDay(new Date());
    if (matchesDayPreset(plan, "tonight")) return "Esta noche";
    if (matchesDayPreset(plan, "today")) return plan._hoursUntil != null && plan._hoursUntil <= 4 ? "En breve" : "Hoy";
    if (matchesDayPreset(plan, "tomorrow")) return "Manana";
    if (matchesDayPreset(plan, "weekend")) return "Este finde";
    const days = Math.round((startOfDay(plan._nextDate) - today) / DAY_MS);
    if (days > 0 && days <= 7) return `En ${days} d`;
    return formatDate(plan._nextDate);
  }

  function compareLabel(plan) {
    if (plan._sourceLinks.length < 2) return null;
    const prices = Array.from(new Set(plan._sourceLinks.map((link) => formatLinkPrice(link))));
    if (prices.length > 1) return `Compara ${plan._sourceLinks.length} accesos`;
    return `${plan._sourceLinks.length} fuentes`;
  }

  function computeDiscoveryScore(plan) {
    const now = new Date();
    const nowStart = startOfDay(now);
    let score = 0;

    if (plan._officialSources.length) score += 24;
    else if (plan._publicSources.length) score += 16;
    else score += 8;

    if (plan._hasImage) score += 10;
    else score += 5;

    if (plan._mapEligible) score += 10;
    else if (plan._hasLocation) score += 4;

    if (plan._priceKnown) score += 5;
    if (plan._isFree) score += 7;
    if (plan._sourceLinks.length > 1) score += 5;

    if (plan._nextDate) {
      const hours = (plan._nextDate.getTime() - now.getTime()) / (60 * 60 * 1000);
      if (hours >= 0) score += Math.max(0, 36 - Math.min(hours, 36));
      const dayDistance = Math.floor((startOfDay(plan._nextDate) - nowStart) / DAY_MS);
      if (dayDistance === 0) score += 10;
    }

    if (state.slotId === "morning") {
      if (plan._moods.includes("visual") || plan._moods.includes("family") || plan._moods.includes("learn")) score += 8;
      if (plan._startsBefore14) score += 6;
    }
    if (state.slotId === "afternoon") {
      if (plan._moods.includes("move") || plan._isOutdoorHint) score += 9;
      if (matchesDayPreset(plan, "today")) score += 4;
    }
    if (state.slotId === "night") {
      if (plan._moods.includes("afterwork") || plan._isNightFriendly) score += 12;
      if (plan._text.includes("teatro") || plan._text.includes("concierto") || plan._text.includes("club") || plan._text.includes("dj")) score += 6;
    }

    return score;
  }

  function formatDateLabel(plan) {
    const start = plan._rangeStart || plan._nextDate;
    const end = plan._rangeEnd || start;
    const time = formatTime(plan.datetime_inicio);
    if (!start) return "Sin fecha clara";
    if (!end || dayKey(start) === dayKey(end)) return time ? `${formatLongDate(start)} · ${time}` : formatLongDate(start);
    return `${formatDate(start)} - ${formatDate(end)}`;
  }

  function enrichPlan(plan) {
    const nextDate = parseDateish(plan.proximo_datetime || plan.proxima_fecha || plan.sort_datetime || plan.datetime_inicio || plan.fecha_inicio, "09:00:00");
    const rangeStart = parseDateish(plan.fecha_inicio || plan.proxima_fecha || plan.sort_datetime || plan.datetime_inicio, "09:00:00") || nextDate;
    const rangeEnd = parseDateish(plan.fecha_fin || plan.proxima_fecha || plan.sort_datetime || plan.datetime_fin || plan.datetime_inicio, "18:00:00") || rangeStart;
    const lat = plan.latitud != null ? Number(plan.latitud) : null;
    const lon = plan.longitud != null ? Number(plan.longitud) : null;
    const relatedSources = Array.isArray(plan.fuentes_relacionadas) && plan.fuentes_relacionadas.length
      ? plan.fuentes_relacionadas.filter(Boolean)
      : [plan.fuente].filter(Boolean);

    const text = normalizeText([
      plan.titulo,
      plan.subtitulo,
      plan.resumen,
      plan.descripcion,
      plan.lugar,
      plan.direccion,
      ...(plan.categorias || []),
      ...(plan.etiquetas || []),
      ...relatedSources.map((source) => sourceLabel(source))
    ].join(" "));

    const sourceLinks = normalizeSourceLinks(plan);
    const officialSources = relatedSources.filter((source) => PRIMARY_SOURCES.has(source));
    const publicSources = relatedSources.filter((source) => PUBLIC_SOURCES.has(source));
    const primarySourceKey = officialSources[0] || relatedSources[0] || plan.fuente;
    const primarySourceTone = sourceMeta(primarySourceKey).color;

    const enriched = {
      ...plan,
      _nextDate: nextDate,
      _rangeStart: rangeStart,
      _rangeEnd: rangeEnd,
      _text: text,
      _sourceLabel: sourceLabel(primarySourceKey),
      _sourceTone: primarySourceTone,
      _sourceToneSoft: hexToRgba(primarySourceTone, 0.18),
      _hasImage: Boolean(plan.imagen),
      _hasLocation: Boolean(plan.lugar || plan.direccion || (lat != null && lon != null)),
      _priceKnown: plan.precio != null && !Number.isNaN(Number(plan.precio)),
      _isFree: plan.es_gratis === true || (plan.precio != null && Number(plan.precio) === 0),
      _lat: Number.isFinite(lat) ? lat : null,
      _lon: Number.isFinite(lon) ? lon : null,
      _relatedSources: relatedSources,
      _sourceLinks: sourceLinks,
      _officialSources: officialSources,
      _publicSources: publicSources
    };

    enriched._moods = getMoodMatches(enriched);
    enriched._primaryMood = enriched._moods[0];
    enriched._hasExplicitTime = Boolean(plan.datetime_inicio || plan.tiene_hora_inicio);
    enriched._startHour = enriched._hasExplicitTime && nextDate ? nextDate.getHours() : null;
    enriched._startsBefore14 = enriched._startHour != null && enriched._startHour < 14;
    enriched._isNightFriendly = (enriched._startHour != null && enriched._startHour >= 19) || enriched._moods.includes("afterwork") || enriched._text.includes("teatro") || enriched._text.includes("concierto") || enriched._text.includes("club");
    enriched._isOutdoorHint = inferOutdoorHint(enriched);
    enriched._citySafe = enriched._lat == null || enriched._lon == null || isWithinMadridBounds(enriched._lat, enriched._lon);
    enriched._mapEligible = enriched._lat != null && enriched._lon != null && isWithinMadridBounds(enriched._lat, enriched._lon);
    enriched._zone = detectZone(enriched);
    enriched._groupScore = getGroupScore(enriched);
    enriched._availabilityLabel = getAvailabilityLabel(enriched);
    enriched._compareLabel = compareLabel(enriched);
    enriched._coverCode = buildCoverCode(enriched);
    enriched._hoursUntil = nextDate ? (nextDate.getTime() - Date.now()) / (60 * 60 * 1000) : null;
    enriched._trust = getTrustInfo(enriched);
    enriched._score = computeDiscoveryScore(enriched);
    return enriched;
  }

  function flashButton(button, text) {
    if (!button) return;
    const previous = button.textContent;
    button.textContent = text;
    window.setTimeout(() => {
      button.textContent = previous;
    }, 1200);
  }

  function loadData() {
    return Promise.all([
      fetch(DATA_URL).then((response) => {
        if (!response.ok) throw new Error(response.statusText);
        return response.json();
      }),
      fetch(NEWS_URL).then((response) => {
        if (!response.ok) throw new Error(response.statusText);
        return response.json();
      })
    ]).then(([plans, news]) => {
      state.allPlans = plans.map(enrichPlan).filter((plan) => plan._citySafe);
      state.allNews = news;
      syncControlsFromState();
      applyTimeTheme();
      renderStaticViews();
      applyFilters({ syncUrl: false });
      syncUrlState();
    }).catch((error) => {
      elements.resultsGrid.innerHTML = `<div class="empty-state"><h3>No he podido cargar el feed</h3><p>${escHtml(error.message)}</p></div>`;
      elements.newsList.innerHTML = "";
    });
  }

  function renderStaticViews() {
    renderMoodButtons();
    renderRefineClouds();
    renderNews();
    renderShortlist();
  }

  function syncControlsFromState() {
    elements.searchInput.value = state.search;
    elements.sortSelect.value = state.sortBy;
    setView(state.view, { render: false, syncUrl: false });
  }

  function renderMoodButtons() {
    elements.moodGrid.innerHTML = MOODS.map((mood) => {
      const count = state.allPlans.filter((plan) => plan._moods.includes(mood.id)).length;
      const isActive = state.activeMood === mood.id;
      return `
        <button
          class="mood-button${isActive ? " is-active" : ""}"
          type="button"
          data-mood="${mood.id}"
          style="--tone:${mood.accent};--tone-soft:${hexToRgba(mood.accent, 0.14)}"
        >
          <em>${mood.short}</em>
          <strong>${mood.label}</strong>
          <small>${mood.blurb}</small>
          <span>${count} planes</span>
        </button>
      `;
    }).join("");
  }

  function renderRefineClouds() {
    const sourceCounts = countBy(state.allPlans, (plan) => plan.fuente);
    const categoryCounts = countMany(state.allPlans, (plan) => plan.categorias || []);
    const priceItems = [
      { id: "free", label: "Gratis total", count: state.allPlans.filter((plan) => plan._isFree).length },
      { id: "paid", label: "De pago", count: state.allPlans.filter((plan) => plan.precio != null && Number(plan.precio) > 0).length }
    ];

    elements.sourceCloud.innerHTML = Array.from(sourceCounts.entries())
      .sort((left, right) => right[1] - left[1])
      .slice(0, TOP_SOURCE_CHIPS)
      .map(([source, count]) => pillButtonHtml({ kind: "source", id: source, label: sourceLabel(source), count, active: state.activeSource === source }))
      .join("");

    elements.categoryCloud.innerHTML = Array.from(categoryCounts.entries())
      .sort((left, right) => right[1] - left[1])
      .slice(0, TOP_CATEGORY_CHIPS)
      .map(([category, count]) => pillButtonHtml({ kind: "category", id: category, label: category, count, active: state.activeCategory === category }))
      .join("");

    elements.priceCloud.innerHTML = priceItems.map((item) => pillButtonHtml({ kind: "price", id: item.id, label: item.label, count: item.count, active: state.activePrice === item.id })).join("");
  }

  function pillButtonHtml(config) {
    return `
      <button class="pill-button${config.active ? " is-active" : ""}" type="button" data-filter-kind="${escHtml(config.kind)}" data-filter-value="${escHtml(config.id)}">
        ${escHtml(config.label)}
        <span>${config.count}</span>
      </button>
    `;
  }

  function countBy(items, getter) {
    const counts = new Map();
    items.forEach((item) => {
      const key = getter(item);
      if (!key) return;
      counts.set(key, (counts.get(key) || 0) + 1);
    });
    return counts;
  }

  function countMany(items, getter) {
    const counts = new Map();
    items.forEach((item) => {
      getter(item).forEach((value) => {
        if (!value) return;
        counts.set(value, (counts.get(value) || 0) + 1);
      });
    });
    return counts;
  }

  function comparePlans(left, right, sortBy) {
    if (sortBy === "free" && left._isFree !== right._isFree) {
      return Number(right._isFree) - Number(left._isFree);
    }
    if (sortBy === "smart" && right._score !== left._score) {
      return right._score - left._score;
    }
    const leftTime = left._nextDate ? left._nextDate.getTime() : Number.POSITIVE_INFINITY;
    const rightTime = right._nextDate ? right._nextDate.getTime() : Number.POSITIVE_INFINITY;
    if (leftTime !== rightTime) return leftTime - rightTime;
    return String(left.titulo || "").localeCompare(String(right.titulo || ""), "es");
  }

  function hasActiveFilters() {
    return Boolean(state.search || state.activeMood || state.activeDay || state.activePulse || state.activeSource || state.activeCategory || state.activePrice);
  }

  function applyFilters(options) {
    const settings = { syncUrl: true, ...(options || {}) };
    const query = normalizeText(state.search);
    const filtered = state.allPlans.filter((plan) => {
      if (query && !plan._text.includes(query)) return false;
      if (state.activeMood && !plan._moods.includes(state.activeMood)) return false;
      if (state.activeDay && !matchesDayPreset(plan, state.activeDay)) return false;
      if (state.activePulse && !matchesPulsePreset(plan, state.activePulse)) return false;
      if (state.activeSource && !(plan._relatedSources || []).includes(state.activeSource)) return false;
      if (state.activeCategory && !(plan.categorias || []).includes(state.activeCategory)) return false;
      if (state.activePrice === "free" && !plan._isFree) return false;
      if (state.activePrice === "paid" && !(plan.precio != null && Number(plan.precio) > 0)) return false;
      return true;
    }).sort((left, right) => comparePlans(left, right, state.sortBy));

    state.filteredPlans = filtered;
    state.page = 1;
    refreshFilterStates();
    renderShelves();
    renderResults();
    renderShortlist();
    if (settings.syncUrl) syncUrlState();
  }

  function refreshFilterStates() {
    renderMoodButtons();
    renderRefineClouds();
    renderQuickFilters();
    renderActiveFilters();
  }

  function renderQuickFilters() {
    elements.quickFilters.querySelectorAll("[data-day], [data-price], [data-pulse]").forEach((button) => {
      const day = button.getAttribute("data-day");
      const price = button.getAttribute("data-price");
      const pulse = button.getAttribute("data-pulse");
      const isActive = (day && state.activeDay === day) || (price && state.activePrice === price) || (pulse && state.activePulse === pulse);
      button.classList.toggle("is-active", Boolean(isActive));
    });
  }

  function dayLabel(value) {
    return {
      today: "Hoy",
      tonight: "Esta noche",
      tomorrow: "Manana",
      week: "Esta semana",
      weekend: "Este finde"
    }[value] || value;
  }

  function pulseLabel(value) {
    return {
      mananeo: "De mananeo",
      fresquito: "Al fresquito"
    }[value] || value;
  }

  function renderActiveFilters() {
    const pills = [];
    if (state.activeMood) pills.push({ key: "mood", label: MOOD_BY_ID[state.activeMood].label });
    if (state.activeDay) pills.push({ key: "day", label: dayLabel(state.activeDay) });
    if (state.activePulse) pills.push({ key: "pulse", label: pulseLabel(state.activePulse) });
    if (state.activeSource) pills.push({ key: "source", label: sourceLabel(state.activeSource) });
    if (state.activeCategory) pills.push({ key: "category", label: state.activeCategory });
    if (state.activePrice) pills.push({ key: "price", label: state.activePrice === "free" ? "Gratis total" : "De pago" });
    if (state.search) pills.push({ key: "search", label: `Busqueda: ${state.search}` });

    elements.activeFilters.innerHTML = pills.map((pill) => `
      <button class="pill-button" type="button" data-clear="${pill.key}">
        ${escHtml(pill.label)}
      </button>
    `).join("");
  }

  function renderShelves() {
    const base = hasActiveFilters() ? state.filteredPlans : state.allPlans;
    const shelves = [
      {
        id: "now",
        title: state.slotId === "night" ? "Ahora mismo tira la noche" : "Ahora mismo",
        text: "Ordenado por cercania temporal, pulso del momento y fiabilidad de la fuente.",
        items: base.filter((plan) => matchesDayPreset(plan, "today")).sort((left, right) => comparePlans(left, right, "smart"))
      },
      {
        id: "tonight",
        title: "Esta noche",
        text: "Concierto, teatro, club o algo facil de proponer cuando cae el sol.",
        items: base.filter((plan) => matchesDayPreset(plan, "tonight")).sort((left, right) => comparePlans(left, right, "smart"))
      },
      {
        id: "mananeo",
        title: "De mananeo",
        text: "Museo, charla, familia o plan que arranca antes de las dos.",
        items: base.filter((plan) => matchesPulsePreset(plan, "mananeo")).sort((left, right) => comparePlans(left, right, "smart"))
      },
      {
        id: "free",
        title: "Gratis total",
        text: "Disparadores limpios para decidir rapido cuando el presupuesto manda.",
        items: base.filter((plan) => plan._isFree).sort((left, right) => comparePlans(left, right, "smart"))
      },
      {
        id: "group",
        title: "Faciles de cuadrar",
        text: "Planes amplios, sociales o sencillos de proponer cuando decides con mas gente.",
        items: base.filter((plan) => plan._groupScore >= 4).sort((left, right) => comparePlans(left, right, "smart"))
      }
    ];

    elements.shelves.innerHTML = shelves
      .map((shelf) => ({ ...shelf, items: shelf.items.slice(0, SHELF_SIZE) }))
      .filter((shelf) => shelf.items.length)
      .map((shelf) => `
        <section class="shelf">
          <div class="shelf-head">
            <div>
              <h3>${escHtml(shelf.title)}</h3>
              <p>${escHtml(shelf.text)}</p>
            </div>
            <span class="count-pill">${shelf.items.length}</span>
          </div>
          <div class="shelf-track" data-shelf="${escHtml(shelf.id)}">
            ${shelf.items.map((plan) => renderMiniCard(plan)).join("")}
          </div>
        </section>
      `).join("");
  }

  function renderMiniCard(plan) {
    const mood = MOOD_BY_ID[plan._primaryMood] || MOODS[0];
    return `
      <article class="mini-card" style="--tone:${mood.accent};--tone-soft:${hexToRgba(mood.accent, 0.14)};--source-tone:${plan._sourceTone};--source-tone-soft:${plan._sourceToneSoft}">
        ${renderVisual(plan, true)}
        <div class="trust-row">
          <span class="trust-pill is-${escHtml(plan._trust.tone)}">${escHtml(plan._trust.label)}</span>
          ${plan._compareLabel ? `<span class="compare-pill">${escHtml(plan._compareLabel)}</span>` : ""}
        </div>
        <h3>${escHtml(plan.titulo)}</h3>
        <p class="mini-copy">${escHtml(truncate(plan.resumen || plan.descripcion || "", 108))}</p>
        <div class="source-link-row is-compact">${renderSourceLinks(plan, 2)}</div>
        <div class="mini-actions">
          <button class="mini-action" type="button" data-action="open" data-id="${escHtml(plan.id)}">Resumen</button>
          <button class="mini-action" type="button" data-action="toggle-save" data-id="${escHtml(plan.id)}">${state.savedIds.has(plan.id) ? "Quitar" : "Guardar"}</button>
        </div>
      </article>
    `;
  }

  function renderResults() {
    const total = state.filteredPlans.length;
    const visible = state.filteredPlans.slice(0, state.page * PAGE_SIZE);
    const mapped = state.filteredPlans.filter((plan) => plan._mapEligible).length;
    elements.resultsSummary.innerHTML = `
      ${visible.length} de ${total} planes visibles
      <small>${hasActiveFilters() ? "Feed afinado por tus criterios actuales." : "Ordenados por pulso, cercania y confianza de fuente."}${mapped ? ` ${mapped} entran limpios en el mapa.` : ""}</small>
    `;

    elements.emptyState.classList.toggle("is-hidden", total !== 0);
    if (state.view === "cards") {
      elements.resultsGrid.style.display = total ? "grid" : "none";
      elements.resultsGrid.innerHTML = visible.map((plan) => renderPlanCard(plan)).join("");
      elements.mapShell.classList.add("is-hidden");
    } else {
      elements.resultsGrid.style.display = "none";
      elements.mapShell.classList.remove("is-hidden");
      renderMap();
    }

    elements.loadMore.classList.toggle("is-hidden", total <= visible.length || state.view !== "cards");
  }

  function renderPlanCard(plan) {
    const mood = MOOD_BY_ID[plan._primaryMood] || MOODS[0];
    const tagCandidates = [...(plan.categorias || []), ...(plan.etiquetas || [])].filter(Boolean).slice(0, 3);

    return `
      <article class="plan-card" style="--tone:${mood.accent};--tone-soft:${hexToRgba(mood.accent, 0.14)};--source-tone:${plan._sourceTone};--source-tone-soft:${plan._sourceToneSoft}">
        ${renderVisual(plan, false)}
        <div class="trust-row">
          <span class="trust-pill is-${escHtml(plan._trust.tone)}">${escHtml(plan._trust.label)}</span>
          ${plan._compareLabel ? `<span class="compare-pill">${escHtml(plan._compareLabel)}</span>` : ""}
        </div>
        <h3>${escHtml(plan.titulo)}</h3>
        <div class="plan-meta">
          <span class="meta-pill meta-pill-strong">${escHtml(plan._availabilityLabel)}</span>
          <span class="meta-pill">${escHtml(formatDateLabel(plan))}</span>
          <span class="meta-pill">${escHtml(plan.lugar || plan.direccion || "Madrid")}</span>
        </div>
        <p class="plan-copy">${escHtml(truncate(plan.resumen || plan.descripcion || "", 170))}</p>
        <div class="tag-row">${tagCandidates.map((tag) => `<span>${escHtml(tag)}</span>`).join("")}</div>
        <div class="source-link-row">${renderSourceLinks(plan, 3)}</div>
        <div class="card-actions">
          <button class="card-action" type="button" data-action="open" data-id="${escHtml(plan.id)}">Ver resumen</button>
          <a class="card-action card-action-primary" href="${escHtml(primaryLink(plan))}" target="_blank" rel="noopener">Abrir mejor acceso</a>
        </div>
      </article>
    `;
  }

  function renderGeneratedCover(plan) {
    return `
      <div class="generated-cover">
        <span class="generated-kicker">${escHtml(sourceLabel(plan._officialSources[0] || plan._relatedSources[0] || plan.fuente))}</span>
        <strong>${escHtml(plan._coverCode)}</strong>
        <small>${escHtml(plan.categoria_principal || plan._availabilityLabel)}</small>
      </div>
    `;
  }

  function renderVisual(plan, compact) {
    const mood = MOOD_BY_ID[plan._primaryMood] || MOODS[0];
    const className = compact ? "mini-visual" : "plan-visual";
    const imageStyle = plan.imagen ? `background-image:url('${escHtml(plan.imagen)}')` : "";
    const generatedClass = plan.imagen ? " has-image" : " is-generated";

    return `
      <div class="${className}${generatedClass}" style="--tone:${mood.accent};--tone-soft:${hexToRgba(mood.accent, 0.14)};--source-tone:${plan._sourceTone};--source-tone-soft:${plan._sourceToneSoft};${imageStyle}">
        ${plan.imagen ? "" : renderGeneratedCover(plan)}
        <div class="visual-top">
          <span class="mood-pill">${escHtml(mood.label)}</span>
          <button class="save-button${state.savedIds.has(plan.id) ? " is-saved" : ""}" type="button" data-action="toggle-save" data-id="${escHtml(plan.id)}">
            ${state.savedIds.has(plan.id) ? "Saved" : "+"}
          </button>
        </div>
        <div class="visual-bottom">
          <span class="source-pill">${escHtml(plan._sourceLabel)}</span>
          <span class="price-pill">${escHtml(formatPrice(plan))}</span>
        </div>
      </div>
    `;
  }

  function renderSourceLinks(plan, limit) {
    return plan._sourceLinks.slice(0, limit).map((link, index) => `
      <a class="source-link-chip${index === 0 ? " is-primary" : ""}" href="${escHtml(link.url)}" target="_blank" rel="noopener">
        <strong>${escHtml(sourceLabel(link.fuente))}</strong>
        <small>${escHtml(formatLinkPrice(link))}</small>
      </a>
    `).join("");
  }

  function renderShortlist() {
    const savedPlans = state.allPlans.filter((plan) => state.savedIds.has(plan.id)).sort((left, right) => comparePlans(left, right, "soon"));

    elements.savedCountPill.textContent = String(savedPlans.length);
    elements.copyShortlist.disabled = savedPlans.length === 0;

    if (!savedPlans.length) {
      elements.savedList.innerHTML = `
        <div class="saved-item">
          <h3>Sin shortlist todavia</h3>
          <p>Guarda dos o tres opciones y ya tendras una base real para decidir con menos ruido.</p>
        </div>
      `;
      return;
    }

    elements.savedList.innerHTML = savedPlans.slice(0, 8).map((plan) => `
      <article class="saved-item">
        <h3>${escHtml(plan.titulo)}</h3>
        <div class="saved-meta">
          <span>${escHtml(plan._availabilityLabel)}</span>
          <span>${escHtml(plan.lugar || plan.direccion || "Madrid")}</span>
        </div>
        <p>${escHtml(truncate(plan.resumen || plan.descripcion || "", 110))}</p>
        <div class="source-link-row is-compact">${renderSourceLinks(plan, 2)}</div>
        <div class="saved-actions">
          <button class="mini-action" type="button" data-action="open" data-id="${escHtml(plan.id)}">Ver</button>
          <button class="mini-action" type="button" data-action="toggle-save" data-id="${escHtml(plan.id)}">Quitar</button>
        </div>
      </article>
    `).join("");
  }

  function renderNews() {
    elements.newsCountPill.textContent = String(state.allNews.length);
    elements.newsList.innerHTML = state.allNews.slice(0, NEWS_ITEMS).map((news) => `
      <a class="news-card" href="${escHtml(news.url || "#")}" target="_blank" rel="noopener">
        <div class="news-thumb">${news.imagen ? `<img src="${escHtml(news.imagen)}" alt="">` : ""}</div>
        <div>
          <div class="news-meta">
            <span>${escHtml(sourceLabel(news.fuente))}</span>
            <span>${escHtml(news.publicado_en ? formatLongDate(parseDateish(news.publicado_en, "09:00:00")) : "Actualidad")}</span>
          </div>
          <h3>${escHtml(news.titulo)}</h3>
          <p>${escHtml(truncate(news.resumen || news.descripcion || "", 120))}</p>
        </div>
      </a>
    `).join("");
  }

  function zoneBounds(zone) {
    const latOffset = zone.radiusKm / 111;
    const lonOffset = zone.radiusKm / (111 * Math.cos(zone.center[0] * Math.PI / 180));
    return L.latLngBounds([zone.center[0] - latOffset, zone.center[1] - lonOffset], [zone.center[0] + latOffset, zone.center[1] + lonOffset]);
  }

  function computeZoneStats(plans) {
    const counts = new Map();
    plans.forEach((plan) => {
      if (!plan._zone) return;
      counts.set(plan._zone.id, (counts.get(plan._zone.id) || 0) + 1);
    });
    return BARRIO_ZONES
      .map((zone) => ({ ...zone, count: counts.get(zone.id) || 0 }))
      .filter((zone) => zone.count > 0)
      .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label, "es"));
  }

  function renderZonePulse(plans) {
    const todayPlans = state.activeDay ? plans : plans.filter((plan) => matchesDayPreset(plan, "today"));
    const pulseBase = todayPlans.length ? todayPlans : plans;
    const zones = computeZoneStats(pulseBase).slice(0, 6);

    if (!zones.length) {
      state.zoneFocus = null;
      elements.zonePulse.innerHTML = "";
      return [];
    }

    if (state.zoneFocus && !zones.some((zone) => zone.id === state.zoneFocus)) {
      state.zoneFocus = null;
    }

    elements.zonePulse.innerHTML = zones.map((zone) => `
      <button class="zone-card${state.zoneFocus === zone.id ? " is-active" : ""}" type="button" data-zone="${escHtml(zone.id)}" style="--tone:${zone.color}">
        <strong>${escHtml(zone.label)}</strong>
        <span>${zone.count} planes</span>
        <small>${escHtml(zone.copy)}</small>
      </button>
    `).join("");

    return zones;
  }

  function markerIcon(plan) {
    return L.divIcon({
      className: "pulse-marker-wrapper",
      html: `<span class="pulse-marker" style="--tone:${escHtml(plan._sourceTone)};--ring:${escHtml(hexToRgba(plan._sourceTone, 0.25))}"></span>`,
      iconSize: [18, 18],
      iconAnchor: [9, 9]
    });
  }

  function ensureMap() {
    if (state.map) return;

    state.map = L.map(elements.mapCanvas, { preferCanvas: true, zoomControl: true }).setView(MADRID_CENTER, 11);

    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://carto.com/">Carto</a>',
      maxZoom: 19
    }).addTo(state.map);

    state.markers = L.markerClusterGroup({
      showCoverageOnHover: false,
      spiderfyOnMaxZoom: true,
      maxClusterRadius: 52,
      iconCreateFunction(cluster) {
        return L.divIcon({
          html: `<span>${cluster.getChildCount()}</span>`,
          className: "pulse-cluster",
          iconSize: [46, 46]
        });
      }
    });

    state.zoneLayer = L.layerGroup();
    state.map.addLayer(state.markers);
    state.map.addLayer(state.zoneLayer);
  }

  function focusZone(zoneId) {
    const zone = BARRIO_ZONES.find((item) => item.id === zoneId);
    if (!zone || !state.map) return;
    state.zoneFocus = zoneId;
    state.map.fitBounds(zoneBounds(zone), { maxZoom: 14, padding: [20, 20] });
    renderMap();
  }

  function renderMap() {
    ensureMap();
    state.markers.clearLayers();
    state.zoneLayer.clearLayers();

    const geocoded = state.filteredPlans.filter((plan) => plan._mapEligible);
    const zones = renderZonePulse(geocoded);

    geocoded.forEach((plan) => {
      const marker = L.marker([plan._lat, plan._lon], { icon: markerIcon(plan) });
      marker.bindPopup(`
        <strong>${escHtml(plan.titulo)}</strong><br>
        ${escHtml(plan._availabilityLabel)} · ${escHtml(formatDateLabel(plan))}<br>
        ${escHtml(plan.lugar || plan.direccion || "Madrid")}<br>
        <a href="${escHtml(primaryLink(plan))}" target="_blank" rel="noopener">Abrir acceso</a>
      `);
      state.markers.addLayer(marker);
    });

    zones.forEach((zone) => {
      const circle = L.circle(zone.center, {
        radius: zone.radiusKm * 1000,
        color: zone.color,
        fillColor: zone.color,
        fillOpacity: state.zoneFocus === zone.id ? 0.16 : 0.07,
        weight: state.zoneFocus === zone.id ? 2.2 : 1.2,
        dashArray: "6 6"
      });
      circle.bindTooltip(`${zone.label} · ${zone.count} planes`, {
        direction: "center",
        permanent: false,
        opacity: 0.92
      });
      state.zoneLayer.addLayer(circle);
    });

    if (state.zoneFocus) {
      const zone = BARRIO_ZONES.find((item) => item.id === state.zoneFocus);
      if (zone) {
        state.map.fitBounds(zoneBounds(zone), { maxZoom: 14, padding: [20, 20] });
      }
    } else if (geocoded.length) {
      const bounds = L.latLngBounds(geocoded.map((plan) => [plan._lat, plan._lon]));
      state.map.fitBounds(bounds.pad(0.08), { maxZoom: 13 });
    } else {
      state.map.setView(MADRID_CENTER, 11);
    }

    if (!geocoded.length) {
      elements.mapList.innerHTML = `
        <article class="map-item">
          <h3>Sin puntos fiables para este filtro</h3>
          <p>Los planes siguen en tarjetas, pero este corte no deja marcadores limpios dentro de Madrid ciudad.</p>
        </article>
      `;
    } else {
      elements.mapList.innerHTML = geocoded.slice(0, 12).map((plan) => `
        <article class="map-item">
          <div class="map-meta">
            <span>${escHtml(plan._availabilityLabel)}</span>
            <span>${escHtml(plan._zone ? plan._zone.label : sourceLabel(plan.fuente))}</span>
          </div>
          <h3>${escHtml(plan.titulo)}</h3>
          <p>${escHtml(plan.lugar || plan.direccion || "Madrid")}</p>
          <div class="source-link-row is-compact">${renderSourceLinks(plan, 2)}</div>
          <div class="saved-actions">
            <button class="mini-action" type="button" data-action="open" data-id="${escHtml(plan.id)}">Ver resumen</button>
            <a class="mini-action" href="${escHtml(primaryLink(plan))}" target="_blank" rel="noopener">Abrir</a>
          </div>
        </article>
      `).join("");
    }

    window.setTimeout(() => state.map.invalidateSize(), 120);
  }

  function openModal(planId) {
    const plan = state.allPlans.find((item) => item.id === planId);
    if (!plan) return;
    const mood = MOOD_BY_ID[plan._primaryMood] || MOODS[0];
    const tagCandidates = [...(plan.categorias || []), ...(plan.etiquetas || [])].filter(Boolean).slice(0, 8);

    elements.modalBody.innerHTML = `
      <div class="close-row">
        <div>
          <p class="eyebrow">Resumen rapido</p>
          <h2>${escHtml(plan.titulo)}</h2>
        </div>
        <button class="close-button" type="button" data-action="close-modal">Cerrar</button>
      </div>
      <div class="modal-grid">
        <div class="modal-main">
          <div class="modal-visual${plan.imagen ? " has-image" : " is-generated"}" style="--tone:${mood.accent};--tone-soft:${hexToRgba(mood.accent, 0.14)};--source-tone:${plan._sourceTone};--source-tone-soft:${plan._sourceToneSoft};${plan.imagen ? `background-image:url('${escHtml(plan.imagen)}')` : ""}">
            ${plan.imagen ? "" : renderGeneratedCover(plan)}
            <div class="visual-top">
              <span class="mood-pill">${escHtml(mood.label)}</span>
              <button class="save-button${state.savedIds.has(plan.id) ? " is-saved" : ""}" type="button" data-action="toggle-save" data-id="${escHtml(plan.id)}">
                ${state.savedIds.has(plan.id) ? "Saved" : "+"}
              </button>
            </div>
            <div class="visual-bottom">
              <span class="source-pill">${escHtml(plan._sourceLabel)}</span>
              <span class="price-pill">${escHtml(formatPrice(plan))}</span>
            </div>
          </div>
          <div class="trust-row">
            <span class="trust-pill is-${escHtml(plan._trust.tone)}">${escHtml(plan._trust.label)}</span>
            ${plan._compareLabel ? `<span class="compare-pill">${escHtml(plan._compareLabel)}</span>` : ""}
          </div>
          <p>${escHtml(plan.descripcion || plan.resumen || plan.titulo)}</p>
          <div class="tag-row">${tagCandidates.map((tag) => `<span>${escHtml(tag)}</span>`).join("")}</div>
        </div>
        <aside class="modal-side">
          <div class="modal-card">
            <p class="eyebrow">Disponibilidad</p>
            <p>${escHtml(plan._availabilityLabel)} · ${escHtml(formatDateLabel(plan))}</p>
          </div>
          <div class="modal-card">
            <p class="eyebrow">Donde</p>
            <p>${escHtml(plan.lugar || plan.direccion || "Madrid")}</p>
          </div>
          <div class="modal-card">
            <p class="eyebrow">Accesos</p>
            <div class="source-link-row">${renderSourceLinks(plan, plan._sourceLinks.length || 1)}</div>
          </div>
          <div class="modal-actions">
            <a class="card-action card-action-primary" href="${escHtml(primaryLink(plan))}" target="_blank" rel="noopener">Abrir mejor acceso</a>
            <button class="card-action" type="button" data-action="toggle-save" data-id="${escHtml(plan.id)}">${state.savedIds.has(plan.id) ? "Quitar del radar" : "Guardar en radar"}</button>
          </div>
        </aside>
      </div>
    `;

    if (!elements.modal.open) elements.modal.showModal();
  }

  function closeModal() {
    if (elements.modal.open) elements.modal.close();
  }

  function toggleSave(planId) {
    if (state.savedIds.has(planId)) state.savedIds.delete(planId);
    else state.savedIds.add(planId);
    persistSavedIds();
    renderResults();
    renderShortlist();
    if (elements.modal.open) openModal(planId);
  }

  function clearFilters() {
    state.activeMood = null;
    state.activeDay = null;
    state.activePulse = null;
    state.activeSource = null;
    state.activeCategory = null;
    state.activePrice = null;
    state.search = "";
    state.zoneFocus = null;
    elements.searchInput.value = "";
    applyFilters();
  }

  function pickSurprise() {
    const pool = state.filteredPlans.length ? state.filteredPlans : state.allPlans;
    if (!pool.length) return;
    const choice = pool[Math.floor(Math.random() * pool.length)];
    openModal(choice.id);
  }

  function copyShortlist() {
    const savedPlans = state.allPlans.filter((plan) => state.savedIds.has(plan.id));
    if (!savedPlans.length) return;
    const text = savedPlans.map((plan) => `${plan.titulo} - ${plan._availabilityLabel} - ${primaryLink(plan)}`).join("\n");
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => flashButton(elements.copyShortlist, "Copiado")).catch(() => {
        window.prompt("Copia tu shortlist", text);
      });
      return;
    }
    window.prompt("Copia tu shortlist", text);
  }

  function shareCurrentView() {
    syncUrlState();
    const url = window.location.href;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(() => flashButton(elements.shareView, "Vista copiada")).catch(() => {
        window.prompt("Copia esta vista", url);
      });
      return;
    }
    window.prompt("Copia esta vista", url);
  }

  function setView(view, options) {
    const settings = { render: true, syncUrl: true, ...(options || {}) };
    state.view = view;
    elements.viewSwitch.querySelectorAll("[data-view]").forEach((button) => {
      button.classList.toggle("is-active", button.getAttribute("data-view") === view);
    });
    if (settings.render) renderResults();
    if (settings.syncUrl) syncUrlState();
  }

  function hydrateStateFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const mood = params.get("mood");
    const day = params.get("day");
    const pulse = params.get("pulse");
    const source = params.get("source");
    const category = params.get("category");
    const price = params.get("price");
    const sort = params.get("sort");
    const view = params.get("view");
    state.activeMood = mood || null;
    state.activeDay = day || null;
    state.activePulse = pulse || null;
    state.activeSource = source || null;
    state.activeCategory = category || null;
    state.activePrice = price || null;
    state.search = params.get("q") || "";
    state.sortBy = ["smart", "soon", "free"].includes(sort) ? sort : "smart";
    state.view = ["cards", "map"].includes(view) ? view : "cards";
  }

  function syncUrlState() {
    const params = new URLSearchParams();
    if (state.search) params.set("q", state.search);
    if (state.activeMood) params.set("mood", state.activeMood);
    if (state.activeDay) params.set("day", state.activeDay);
    if (state.activePulse) params.set("pulse", state.activePulse);
    if (state.activeSource) params.set("source", state.activeSource);
    if (state.activeCategory) params.set("category", state.activeCategory);
    if (state.activePrice) params.set("price", state.activePrice);
    if (state.sortBy && state.sortBy !== "smart") params.set("sort", state.sortBy);
    if (state.view && state.view !== "cards") params.set("view", state.view);

    const query = params.toString();
    const url = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash || ""}`;
    window.history.replaceState({}, "", url);
  }

  function bindEvents() {
    let searchTimer;
    elements.searchInput.addEventListener("input", () => {
      window.clearTimeout(searchTimer);
      searchTimer = window.setTimeout(() => {
        state.search = elements.searchInput.value;
        applyFilters();
      }, 140);
    });

    elements.surpriseButton.addEventListener("click", pickSurprise);
    elements.clearAllFilters.addEventListener("click", clearFilters);
    elements.sortSelect.addEventListener("change", () => {
      state.sortBy = elements.sortSelect.value;
      applyFilters();
    });
    elements.loadMore.addEventListener("click", () => {
      state.page += 1;
      renderResults();
    });
    elements.copyShortlist.addEventListener("click", copyShortlist);
    elements.shareView.addEventListener("click", shareCurrentView);

    elements.moodGrid.addEventListener("click", (event) => {
      const button = event.target.closest("[data-mood]");
      if (!button) return;
      const mood = button.getAttribute("data-mood");
      state.activeMood = state.activeMood === mood ? null : mood;
      applyFilters();
    });

    elements.quickFilters.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (!button) return;
      const day = button.getAttribute("data-day");
      const price = button.getAttribute("data-price");
      const pulse = button.getAttribute("data-pulse");
      if (day) state.activeDay = state.activeDay === day ? null : day;
      if (price) state.activePrice = state.activePrice === price ? null : price;
      if (pulse) state.activePulse = state.activePulse === pulse ? null : pulse;
      applyFilters();
    });

    [elements.sourceCloud, elements.categoryCloud, elements.priceCloud, elements.activeFilters].forEach((container) => {
      container.addEventListener("click", (event) => {
        const button = event.target.closest("button");
        if (!button) return;

        const clearKey = button.getAttribute("data-clear");
        if (clearKey) {
          if (clearKey === "mood") state.activeMood = null;
          if (clearKey === "day") state.activeDay = null;
          if (clearKey === "pulse") state.activePulse = null;
          if (clearKey === "source") state.activeSource = null;
          if (clearKey === "category") state.activeCategory = null;
          if (clearKey === "price") state.activePrice = null;
          if (clearKey === "search") {
            state.search = "";
            elements.searchInput.value = "";
          }
          applyFilters();
          return;
        }

        const kind = button.getAttribute("data-filter-kind");
        const value = button.getAttribute("data-filter-value");
        if (kind === "source") state.activeSource = state.activeSource === value ? null : value;
        if (kind === "category") state.activeCategory = state.activeCategory === value ? null : value;
        if (kind === "price") state.activePrice = state.activePrice === value ? null : value;
        applyFilters();
      });
    });

    [elements.resultsGrid, elements.shelves, elements.savedList, elements.mapList, elements.modalBody].forEach((container) => {
      container.addEventListener("click", (event) => {
        const actionTarget = event.target.closest("[data-action]");
        if (!actionTarget) return;
        const action = actionTarget.getAttribute("data-action");
        const planId = actionTarget.getAttribute("data-id");
        if (action === "open" && planId) openModal(planId);
        if (action === "toggle-save" && planId) toggleSave(planId);
        if (action === "close-modal") closeModal();
      });
    });

    elements.zonePulse.addEventListener("click", (event) => {
      const button = event.target.closest("[data-zone]");
      if (!button) return;
      const zoneId = button.getAttribute("data-zone");
      if (state.zoneFocus === zoneId) {
        state.zoneFocus = null;
        renderMap();
        return;
      }
      focusZone(zoneId);
    });

    elements.viewSwitch.addEventListener("click", (event) => {
      const button = event.target.closest("[data-view]");
      if (!button) return;
      setView(button.getAttribute("data-view"));
    });

    elements.jumpExplorer.addEventListener("click", () => document.getElementById("explorer").scrollIntoView({ behavior: "smooth", block: "start" }));
    elements.jumpMap.addEventListener("click", () => {
      setView("map");
      document.getElementById("explorer").scrollIntoView({ behavior: "smooth", block: "start" });
    });
    elements.jumpShortlist.addEventListener("click", () => document.getElementById("shortlist-panel").scrollIntoView({ behavior: "smooth", block: "start" }));

    window.addEventListener("scroll", () => {
      elements.scrollTop.classList.toggle("is-visible", window.scrollY > 700);
    });
    elements.scrollTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

    window.addEventListener("popstate", () => {
      hydrateStateFromUrl();
      syncControlsFromState();
      applyFilters({ syncUrl: false });
    });

    elements.modal.addEventListener("click", (event) => {
      if (event.target === elements.modal) closeModal();
    });
  }

  bindEvents();
  loadData();
})();