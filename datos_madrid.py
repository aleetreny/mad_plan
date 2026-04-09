import requests
import json

def extraer_datos_madrid():
    api_url = "https://datos.madrid.es/api/3/action/package_show?id=206974-0-agenda-eventos-culturales-100"
    res = requests.get(api_url).json()

    data_url = res['result']['resources'][0]['url']
    data = requests.get(data_url).json()

    eventos = []
    for item in data.get('@graph', []):
        loc = item.get('location', {})
        eventos.append({
            "fecha": item.get("dtstart"),
            "ciudad": "Madrid",
            "lat": loc.get("latitude"),
            "lon": loc.get("longitude"),
            "tipo": item.get("tipo"),
            "url_compra": item.get("url-actividad"),
            "nombre": item.get("title"),
            "descripcion": item.get("description")
        })
        
    if eventos:
        with open('eventos_datos_madrid.json', 'w', encoding='utf-8') as f:
            json.dump(eventos, f, ensure_ascii=False, indent=4)
            
    return eventos
    
if __name__ == "__main__":
    extraer_datos_madrid()