#!/usr/bin/env python3
"""Build data/segments.js from data/trips.js.

This is intended for the current Viaduct prototype where GPX-derived routes have
already been collected in window.VIADUCT_TRIPS. Each route can carry `weight`,
which represents how many rides that geometry stands for.

Important: this is a geometry heatmap, not railway-network map matching. It
rejects implausible jumps and aggregates nearby route samples into shared cells.
"""
from pathlib import Path
from collections import Counter
import json, math, re

SOURCE = Path('data/trips.js')
OUTPUT = Path('data/segments.js')
CELL_M = 120.0
MAX_LINK_M = 1500.0


def haversine(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2-lat1, lon2-lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371000 * 2 * math.asin(min(1, math.sqrt(h)))


def load_trips():
    text = SOURCE.read_text(encoding='utf-8')
    m = re.search(r'window\.VIADUCT_TRIPS\s*=\s*(\[.*\])\s*;?\s*$', text, re.S)
    if not m:
        raise SystemExit('Could not parse window.VIADUCT_TRIPS')
    return json.loads(m.group(1))


def project(p, ref_lat=50.0):
    lat, lon = p
    y = lat * 111_320.0
    x = lon * 111_320.0 * math.cos(math.radians(ref_lat))
    return x, y


def unproject(cell, ref_lat=50.0):
    x, y = cell
    return [round(y * CELL_M / 111_320.0, 6),
            round(x * CELL_M / (111_320.0 * math.cos(math.radians(ref_lat))), 6)]


def cell(p):
    x, y = project(p)
    return (round(x / CELL_M), round(y / CELL_M))


def main():
    trips = load_trips()
    counts = Counter()
    rejected = 0
    weighted_trip_count = 0
    valid_geometries = 0

    for trip in trips:
        points = trip.get('points') or []
        weight = max(1, int(trip.get('weight', 1)))
        if len(points) < 2:
            continue
        valid_geometries += 1
        weighted_trip_count += weight
        seen = set()
        prev = points[0]
        prev_cell = cell(prev)
        for p in points[1:]:
            # Protect the map from malformed/truncated route geometry.
            if haversine(prev, p) > MAX_LINK_M:
                rejected += 1
                prev, prev_cell = p, cell(p)
                continue
            c = cell(p)
            if c != prev_cell:
                edge = tuple(sorted((prev_cell, c)))
                seen.add(edge)
            prev, prev_cell = p, c
        for edge in seen:
            counts[edge] += weight

    segments = [
        {'a': unproject(a), 'b': unproject(b), 'count': n}
        for (a, b), n in counts.items()
    ]
    segments.sort(key=lambda s: (s['count'], s['a'], s['b']))
    data = {
        'tripCount': weighted_trip_count,
        'geometryCount': valid_geometries,
        'segmentCount': len(segments),
        'maxCount': max(counts.values(), default=0),
        'rejectedLinks': rejected,
        'cellMeters': CELL_M,
        'segments': segments,
    }
    OUTPUT.write_text('window.VIADUCT_DATA=' + json.dumps(data, separators=(',', ':')) + ';\n', encoding='utf-8')
    print(f"{weighted_trip_count} rides / {valid_geometries} geometries -> {len(segments)} segments; rejected {rejected} jumps")


if __name__ == '__main__':
    main()
