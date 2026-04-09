import requests
import json
import time
from bs4 import BeautifulSoup

def extraer_madrid_por_categorias():
    # Mapeo de tus categorías a los slugs reales de la URL de Eventbrite
    categorias = {
        "Negocios": "business",
        "Gastronomía": "food-and-drink",
        "Salud": "health",
        "Música": "music",
        "Motores": "auto-boat-and-air",
        "Solidaridad": "charity-and-causes",
        "Comunidad": "community",
        "Familia": "family-and-education",
        "Moda": "fashion",
        "Cine": "film-and-media",
        "Aficiones": "hobbies",
        "Hogar": "home-and-lifestyle",
        "Artes": "arts",
        "Gobierno": "government",
        "Espiritualidad": "spirituality",
        "Escolares": "school-activities",
        "Ciencia": "science-and-tech",
        "Vacaciones": "holiday",
        "Deportes": "sports-and-fitness",
        "Viajes": "travel-and-outdoor",
        "Otro": "other"
    }

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    biblioteca_eventos = {}

    for nombre, slug in categorias.items():
        # Usamos sort_by=date para asegurar que barremos el calendario a futuro
        url = f"https://www.eventbrite.es/d/spain--madrid/{slug}--events/?sort_by=date"
        
        try:
            # Scrapeamos las 3 primeras páginas de cada categoría para no saturar
            for page in range(1, 4):
                paginated_url = f"{url}&page={page}"
                res = requests.get(paginated_url, headers=headers, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                scripts = soup.find_all('script', type='application/ld+json')

                for s in scripts:
                    data = json.loads(s.string)
                    items = data.get('itemListElement', []) if isinstance(data, dict) else []
                    for entry in items:
                        info = entry.get('item', {})
                        link = info.get("url")
                        if link and link not in biblioteca_eventos:
                            loc = info.get("location", {})
                            geo = loc.get("geo", {})
                            biblioteca_eventos[link] = {
                                "nombre": info.get("name"),
                                "fecha": info.get("startDate"),
                                "ciudad": "Madrid",
                                "lat": geo.get("latitude"),
                                "lon": geo.get("longitude"),
                                "url_compra": link,
                                "categoria": nombre,
                                "descripcion": info.get("description")
                            }
                time.sleep(1) # Respiro para el servidor
        except:
            pass

    # Guardar resultados
    if biblioteca_eventos:
        with open('eventos_madrid_completo.json', 'w', encoding='utf-8') as f:
            json.dump(list(biblioteca_eventos.values()), f, ensure_ascii=False, indent=4)
        return list(biblioteca_eventos.values())
    return []

if __name__ == "__main__":
    extraer_madrid_por_categorias()