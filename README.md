# Moje železnice 2026

Vlastní heatmapa železničních jízd postavená nad GPX exporty z Viaductu.

## Dataset 2026

Kontrolní build z exportu 27. 10. 2026 obsahuje:

- 185 validních GPX jízd
- 1 758 samostatných `<trkseg>` bloků
- 286 741 zdrojových GPX bodů
- 22 867 normalizovaných prostorových úseků při 120m mřížce
- nejvyšší zachycenou intenzitu 25×
- 42 odmítnutých spojnic delších než 1,5 km
- geografický rozsah přibližně 48.72–52.40° N / 13.20–21.00° E

## Pipeline

1. Zdroj pravdy jsou jednotlivé GPX exporty z Viaductu.
2. Každý GPX `<trkseg>` zůstává samostatný; mezi dvěma segmenty se nikdy nevytváří umělá spojnice.
3. Hustá GPX geometrie se resampluje přibližně po 120 metrech.
4. Body se normalizují do metrické 120m mřížky.
5. Každá hrana se v rámci jedné GPX jízdy započítá nejvýše jednou.
6. Spojení delší než 1,5 km se odmítají jako podezřelé skoky.
7. Výstup `data/segments.js` používá kompaktní pole `[lat1,lon1,lat2,lon2,count]`.

## Build

```bash
python tools/build_heatmap.py /cesta/k/VIADUCT/2026 data/segments.js
```

Lokální náhled:

```bash
python -m http.server 8000
```

## Co statistika znamená

Aktuální mapa je **heatmapa GPX geometrie**, nikoli ještě přesný výpočet unikátních kilometrů české železniční sítě. Normalizace do 120m mřížky dovoluje rozumně spojit mírně odlišné GPX průjezdy a zobrazit frekvenci, ale nemá být používána pro tvrzení typu „projeto přesně X % české železnice“.

Pro přesné coverage statistiky je další krok map-matching GPX na kanonickou železniční síť (OSM/SŽ). Teprve nad ní má smysl počítat unikátní kilometry, podíl sítě, elektrizaci a další infrastrukturní atributy.

## Soubory

- `index.html` – výsledná interaktivní heatmapa
- `data/segments.js` – vygenerovaný dataset pro web
- `tools/build_heatmap.py` – builder přímo ze složky GPX
- `tools/build_from_trips.py` – starší builder pro agregovaný `trips.js`; ponechán jen pro reprodukci prototypu
