# Viaduct heatmap

Heatmapa železničních jízd z GPX exportů Viaductu.

## Aktuální pipeline

1. GPX trasy jsou převedeny do `data/trips.js`.
2. Opakované shodné geometrie mohou mít `weight` > 1.
3. `tools/build_from_trips.py` sesadí geometrii do cca 120m buněk a sčítá průjezdy po společných hranách.
4. Spojení delší než 1,5 km se odmítnou, aby poškozená nebo špatně spojená GPX geometrie nevytvářela čáry přes půl republiky.
5. Výsledkem je `data/segments.js`, který web vykreslí jako segmentovou heatmapu.

Web má navíc fallback: pokud `segments.js` ještě není vygenerovaný, vykreslí přímo `trips.js`, ale i v tomto režimu zahazuje spojnice delší než 1,5 km.

## Soubory

- `index.html` – UI a Leaflet mapa
- `data/trips.js` – GPX-derived geometrie
- `data/segments.js` – agregované segmenty
- `tools/build_from_trips.py` – builder pro současný agregovaný dataset
- `tools/build_heatmap.py` – builder přímo ze složky GPX

## Vygenerování segmentů

```bash
python tools/build_from_trips.py
```

Potom stačí otevřít `index.html`, případně:

```bash
python -m http.server 8000
```

## Důležité omezení

Současná agregace je prostorová aproximace nad GPX geometrií. Pro statisticky přesné tvrzení typu „tento konkrétní železniční úsek jsem projel 17×“ bude další verze map-matchovat GPX na kanonickou železniční síť (např. OSM/SŽ). Tím se sjednotí drobně odlišné geometrie téže koleje a správně se ošetří souběžné tratě a uzly.
