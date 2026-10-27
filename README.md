# Po kolejích · ANLEX 2026

**[Otevřít veřejnou mapu](https://anlexcz.github.io/viaduct/)**

Vlastní železniční deník z GPX exportů Viaductu. Skutečná data, žádný ukázkový fallback. Statická aplikace pro GitHub Pages, Leaflet 1.9.4 je součástí repozitáře.

## Dataset a výsledky

Build z exportu `VIADUCT-20261027T163344Z-1-001.zip`:

| Metrika | Výsledek |
| --- | ---: |
| GPX / validní jízdy | 185 / 185 |
| Období | 5. 1. – 4. 10. 2026 |
| Samostatné trkseg | 1 758 |
| Zdrojové body | 286 741 |
| Podezřelé spojnice nad 1,5 km | 42 odmítnutých |
| Délka GPX bez mezer a skoků | 13 130,5 km |
| Přijatá délka GPX, přibližně | 99,84 % |
| Nepřiřazené části GPX | 21,25 km |
| Napárované / nepřiřazené přechody | 266 382 / 697 |
| Normalizované projeté mikroúseky | 113 358 |
| Nejvyšší počet jízd úsekem | 25× |
| 95. percentil vzdálenosti přijatých bodů od OSM | 4,7 m |

Přijatý podíl **není ověřená přesnost** map-matchingu. Délka GPX je součet geometrie v metrické projekci EPSG:3035; nezahrnuje vynechané části a není tarifní vzdáleností. Počet mikroúseků závisí na členění OSM, nevyjadřuje počet tratí. `uniqueRepresentativeKm` v technických datech je pouze odhad délky reprezentantů, proto jej web neprezentuje jako přesné unikátní traťové kilometry.

GPX byly porovnány s hranicemi států: **Česko, Polsko, Slovensko a Německo**. Německem procházejí také cesty Liberec–Varnsdorf a Varnsdorf–Jedlová. Síť není omezena na ČR.

## Reprodukce

Python 3.11+:

```bash
python -m pip install -r requirements.txt
# ZIP rozbal do libovolné složky, sám není součástí veřejného repozitáře.
python tools/build_heatmap.py /cesta/k/rozbalenym/GPX --network data/network.json.gz --out data
python -m unittest discover -s tools -p 'test_*.py' -v
python -m http.server 8000
```

Otevři `http://localhost:8000`. Build pracuje offline s připnutým výřezem OSM. V `qa.json` jsou SHA-256 každého GPX a v `stats.json` hash síťového snapshotu. Prázdný vstup způsobí chybu, nevytvoří testovací data. Každý soubor je jedna jízda; pipeline záměrně neslučuje stejné geometrie z různých GPX. Před přidáním exportu je potřeba odstranit skutečné duplicitní exporty téže jízdy.

### Rozšíření síťového výřezu

Pokud nové GPX leží mimo uložený koridor, nejprve rozšiř síť. Stáhni potřebné regiony z [Geofabriku](https://download.geofabrik.de/europe.html): Czech Republic, Poland, Slovakia a Germany/Sachsen. Přípony `.osm.pbf`; všechny ulož do jedné složky. Pro další země přidej odpovídající region. Není potřeba stahovat celou Evropu.

```bash
python tools/extract_network.py /cesta/k/GPX /cesta/k/PBF data/network.json.gz
python tools/build_heatmap.py /cesta/k/GPX --network data/network.json.gz --out data
```

Extraktor načte železniční ways a jejich uzly ve dvou průchodech bez ukládání všech bodů celé země do paměti. Zachová celé OSM linie, které mají alespoň jeden bod do 1 km od GPX. Jde o prostorový výřez pro matching, **nikoliv jmenovatel pokrytí sítě**. Dlouhá OSM linie protínající koridor bez blízkého uzlu může být výjimečně vynechána; projeví se v unmatched. Při rozšíření do nových zemí aktualizuj i metadata `countries` a text webu: tento release je explicitně vyhodnocený dataset 2026 pro CZ/PL/SK/DE.

Připnutý snapshot: OSM/Geofabrik 26. 10. 2026, Sasko 25. 10. 2026; podrobné timestampy jsou ve statistikách. Aktualizace OSM může měnit identifikátory segmentů i výsledek. Pro srovnatelné buildy používej stejný snapshot.

## Map-matching

1. XML validace souřadnic. Každý `<trkseg>` se zpracovává zvlášť. Zdrojové spojnice nad 1 500 m se odmítnou **před** převzorkováním. Přes mezery se nikdy nedokresluje spojnice.
2. Kanonická fyzická síť obsahuje OSM `railway=rail` a `railway=narrow_gauge`. Vyřazují se `disused=yes`, `abandoned=yes`, `area=yes` a při routování `service=yard|spur|crossover`. `service=siding` zůstává s mírnou penalizací. Nerozlišujeme univerzálně osobní a nákladní tratě; to pro mapování vlastních GPX není potřeba.
3. Graf spojuje pouze skutečné společné OSM uzly. Křížení bez uzlu se nepropojuje. Hrany se dělí maximálně na 80 m; nové mezilehlé uzly jsou interní pro konkrétní way. GPX se vzorkuje přibližně po 20–100 m, bez propojení oddělených bloků.
4. Pro každý vzorek se najdou nejvýše čtyři kandidátní hrany do 65 m. Cena polohy je `(vzdálenost/18)^2`; přidává se směrová penalizace. Směr koleje je neorientovaný, opačné směry se počítají společně.
5. Dynamické programování v omezeném paprsku (beam search) hledá návaznou sekvenci. Přechody mezi projekcemi bodů se routují Dijkstrovým algoritmem po fyzickém OSM grafu. Odchylka délky přechodu nesmí překročit `max(90 m, 0,6 × vzdálenost vzorků)`; prohledávání má omezený dosah. Chybějící kandidát nebo nenavazující graf zahájí nový blok a vytvoří záznam unmatched. Nejde o silniční router ani volné přichytávání čar k nejbližší trati.
6. Teprve pak následuje normalizace souběžných kolejí. Deterministický reprezentant pochází ze skutečné OSM geometrie. Přednost má hlavní kolej před `siding`, pak menší OSM way ID. Slučují se místní souběžné hrany s odchylkou do 12°, kompatibilními `gauge`, `layer`, `bridge`, `tunnel` a nepřekrývajícími se různými `ref` se naopak neslučují. Tolerance je do 25 m při společném `ref`, jinak do 10 m; kontrolují se i konce hran a překryv projekce. Slučování není tranzitivní, nemůže postupně pohltit vzdálenou trať.
7. V jedné GPX jízdě je každý reprezentant v množině, tedy se započte nejvýše jednou. Frekvence je počet GPX jízd, které reprezentanta navštívily, nikoli počet směrových průjezdů nebo jednotlivých kolejí.

Koncept kombinace vzdálenosti a délky průchodu grafem vychází z [Newson & Krumm, Hidden Markov Map Matching](https://www.microsoft.com/en-us/research/publication/hidden-markov-map-matching-through-noise-and-sparseness/); zde jde o vlastní deterministické nákladové beam řešení, bez pravděpodobnostní kalibrace HMM. Význam OSM atributů: [OpenRailwayMap tagging](https://wiki.openstreetmap.org/wiki/OpenRailwayMap/Tagging).

## Přesnost a kontrola

- Toleranční matching může ve složitém souběhu zvolit nesprávnou větev, která je geometricky i topologicky věrohodná. Malý reziduál sám o sobě správnou větev nedokazuje. Řešení nemá ručně ověřený ground truth pro každou jízdu.
- Slučování kolejí je konzervativní lokální aproximace. Různě členěné ways nebo neúplné ref/bridge/gauge tagy mohou zachovat více reprezentantů téže trati. Nelze z něj odvodit přesné procento projetých tratí.
- Tunel se přijme jen tam, kde je doložený průběh GPX i routovatelná OSM geometrie. Přerušené GPX se přes tunel nedopočítává.
- Delší skutečná zdrojová spojnice může být odmítnuta jako podezřelá; těchto 42 míst je záměrně zachováno pro kontrolu.
- Nejméně jisté části jsou v `unmatched.geojson`, odmítnuté skoky v `rejected.geojson` jako dvojice bodů. Web je umí zobrazit oranžově. `qa.json` obsahuje per-ride zdrojovou délku, routovanou délku, mezery a reziduály.

Automatické regrese ověřují oddělení trkseg, odmítání skoků, oba směry jízdy, nespojování nesouvislého grafu, slučování paralelních kolejí a zachování různých tratí/tunelů. Kontrola datasetu a namátkové kontroly jsou v `data/validation.json`.

## Web a výkon

Jedna canvas vrstva, šest trvale dostupných kategorií 1 / 2–3 / 4–9 / 10–24 / 25–49 / 50+ jízd. Filtry, tooltip i klikací detail fungují také pro kategorii 1×. Pro výběr se používá prostorový index v obrazovkových buňkách, nevytváří se 100 tisíc DOM prvků či Leaflet vrstev. Překreslují se jen viditelné úseky.

`heatmap.json.gz` má přibližně 1,3 MB. Prohlížeč jej dekomprimuje pomocí `DecompressionStream` (aktuální Firefox, Chrome, Edge, Safari); nevyžaduje backend. Struktura: `segments = [lon1,lat1,lon2,lat2,count,osmWayId]`, metadata linií jsou v `ways`. Kompletní síťový snapshot se při prohlížení webu nestahuje.

## Pokrytí sítě: zatím bez procenta

Možný budoucí jmenovatel: délka všech provozovaných osobních železničních **koridorů** v přesně vyjmenovaných zemích, `railway=rail|narrow_gauge`, bez staveb, zrušených tratí a manipulačních kolejí; souběžné koleje sjednocené stejnou metodou v čitateli i jmenovateli. Je nutné vyřešit neúplné značení osobní dopravy i traťových koridorů pro **celé země**. Uložený 1km koridor podél GPX není vhodný jmenovatel. Dokud taková síť není připravená, web žádné procento pokrytí nepublikuje.

## Licence a nasazení

Železniční síť a odvozené geometrie: © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Výřezy poskytuje Geofabrik. GPX jízd: export uživatele Anlex. Leaflet: BSD-2-Clause, licence ve `vendor/leaflet-LICENSE`. Podkladové dlaždice: OpenStreetMap; tmavý vzhled vytváří CSS filtr pouze nad podkladovou vrstvou. Web zachovává atribuci.

GitHub Pages publikuje kořen větve `main`. Soubor `.nojekyll` zachovává statické soubory. Bez falešného datasetu: při chybě načtení web zobrazí chybu místo náhradních jízd. Staré `trips.js`, `segments.js` a builder ručně vytvořených trips byly odstraněny.
