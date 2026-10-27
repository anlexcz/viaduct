# Viaduct heatmap

První MVP vizualizace jízd z GPX exportů Viaductu.

## Co umí

- vykreslit GPX trasy na mapě OpenStreetMap,
- zvýraznit častěji projeté trasy,
- zobrazit počet jízd a bodů v aktuálním datasetu,
- funguje jako jednoduchý statický web bez buildu.

## Struktura

- `index.html` – UI a Leaflet mapa
- `data/trips.js` – zpracované GPX body pro aktuální prototyp

## Omezení MVP

Aktuální verze je vizuální heatmapa založená na překryvu tras. Přesné počítání průjezdů po totožných železničních úsecích bude další krok: GPX je potřeba prostorově sesadit do společné sítě a agregovat po segmentech.

## Lokální spuštění

Stačí otevřít `index.html`, případně spustit jednoduchý HTTP server:

```bash
python -m http.server 8000
```

Pak otevřít `http://localhost:8000`.
