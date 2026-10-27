#!/usr/bin/env python3
"""Build data/segments.js directly from Viaduct GPX exports.

Usage:
    python tools/build_heatmap.py path/to/gpx-folder [output]

The builder keeps GPX <trkseg> blocks separate, resamples dense geometry,
normalises samples to a 120 m metric grid and counts every grid edge at most
once per GPX ride. Implausible links are rejected rather than drawn.

This is a GPX geometry heatmap. It is intentionally not presented as exact
railway-network coverage; canonical OSM/SŽ map matching is a separate step.
"""
from pathlib import Path
from collections import Counter
import json, math, sys, xml.etree.ElementTree as ET

STEP_M = 120
CELL_M = 120.0
MAX_EDGE_M = 1500
REF_LAT = 50.0


def distance(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2-lat1, lon2-lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371000 * 2 * math.asin(min(1, math.sqrt(h)))


def read_gpx(path):
    root = ET.parse(path).getroot()
    result = []
    for seg in root.iter():
        if not seg.tag.endswith('trkseg'):
            continue
        pts = [(float(p.attrib['lat']), float(p.attrib['lon']))
               for p in list(seg) if p.tag.endswith('trkpt')]
        if len(pts) >= 2:
            result.append(pts)
    return result


def resample(points):
    out = [points[0]]
    acc = 0.0
    last = points[0]
    for p in points[1:]:
        d = distance(last, p)
        if d > 5000:
            last, acc = p, 0.0
            out.append(p)
            continue
        acc += d
        if acc >= STEP_M:
            out.append(p)
            acc = 0.0
        last = p
    if distance(out[-1], points[-1]) > 20:
        out.append(points[-1])
    return out


def project(p):
    lat, lon = p
    return lon * 111320.0 * math.cos(math.radians(REF_LAT)), lat * 111320.0


def cell(p):
    x, y = project(p)
    return round(x / CELL_M), round(y / CELL_M)


def unproject(c):
    x, y = c
    return [round(y * CELL_M / 111320.0, 6),
            round(x * CELL_M / (111320.0 * math.cos(math.radians(REF_LAT))), 6)]


def main():
    source = Path(sys.argv[1] if len(sys.argv) > 1 else 'gpx')
    output = Path(sys.argv[2] if len(sys.argv) > 2 else 'data/segments.js')
    files = sorted(source.rglob('*.gpx'))
    counts = Counter()
    valid = rejected = trksegs = points = 0
    minlat = minlon = float('inf')
    maxlat = maxlon = float('-inf')

    for path in files:
        try:
            track_segments = read_gpx(path)
        except Exception as exc:
            print(f'WARN {path}: {exc}', file=sys.stderr)
            continue
        if not track_segments:
            continue
        valid += 1
        trksegs += len(track_segments)
        trip_edges = set()
        for raw in track_segments:
            points += len(raw)
            for lat, lon in raw:
                minlat, maxlat = min(minlat, lat), max(maxlat, lat)
                minlon, maxlon = min(minlon, lon), max(maxlon, lon)
            pts = resample(raw)
            prev, prev_cell = pts[0], cell(pts[0])
            for p in pts[1:]:
                if distance(prev, p) > MAX_EDGE_M:
                    rejected += 1
                    prev, prev_cell = p, cell(p)
                    continue
                c = cell(p)
                if c != prev_cell:
                    trip_edges.add(tuple(sorted((prev_cell, c))))
                prev, prev_cell = p, c
        counts.update(trip_edges)

    # Compact representation: [lat1, lon1, lat2, lon2, traversal_count].
    segments = [[*unproject(a), *unproject(b), n] for (a, b), n in counts.items()]
    segments.sort(key=lambda x: (x[4], x[0], x[1], x[2], x[3]))
    histogram = Counter(s[4] for s in segments)
    data = {
        'year': 2026,
        'tripCount': valid,
        'trackSegmentCount': trksegs,
        'pointCount': points,
        'segmentCount': len(segments),
        'maxCount': max(counts.values(), default=0),
        'rejectedLinks': rejected,
        'cellMeters': CELL_M,
        'bounds': [[round(minlat, 5), round(minlon, 5)],
                   [round(maxlat, 5), round(maxlon, 5)]],
        'frequencyHistogram': dict(sorted(histogram.items())),
        'format': '[lat1,lon1,lat2,lon2,count]',
        'segments': segments,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('window.VIADUCT_DATA=' + json.dumps(data, separators=(',', ':')) + ';\n', encoding='utf-8')
    print(f'{valid} rides / {trksegs} trkseg / {points} points -> {len(segments)} segments; max {data["maxCount"]}x; rejected {rejected}')


if __name__ == '__main__':
    main()
