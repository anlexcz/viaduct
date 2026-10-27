#!/usr/bin/env python3
"""Build data/segments.js from GPX files.

Usage: python tools/build_heatmap.py path/to/gpx-folder

The builder resamples tracks, snaps nearby samples to ~100 m nodes and counts
undirected edges once per trip. This makes opposite directions and repeated GPX
exports contribute to the same heatmap segment while guarding against GPX jumps.
"""
from pathlib import Path
from collections import Counter
import json, math, sys, xml.etree.ElementTree as ET

STEP_M = 120
SNAP_DECIMALS = 3
MAX_EDGE_M = 2000

def distance(a,b):
    lat1,lon1=map(math.radians,a); lat2,lon2=map(math.radians,b)
    dlat=lat2-lat1; dlon=lon2-lon1
    h=math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371000*2*math.asin(math.sqrt(h))

def read_gpx(path):
    root=ET.parse(path).getroot()
    return [(float(p.attrib['lat']),float(p.attrib['lon'])) for p in root.iter() if p.tag.endswith('trkpt')]

def resample(points):
    if len(points)<2: return points
    out=[points[0]]; acc=0; last=points[0]
    for p in points[1:]:
        d=distance(last,p)
        if d>5000:
            if distance(out[-1],last)>STEP_M/2: out.append(last)
            out.append(p); last=p; acc=0; continue
        acc+=d
        if acc>=STEP_M: out.append(p); acc=0
        last=p
    if distance(out[-1],points[-1])>20: out.append(points[-1])
    return out

def snap(p): return (round(p[0],SNAP_DECIMALS),round(p[1],SNAP_DECIMALS))

def main():
    source=Path(sys.argv[1] if len(sys.argv)>1 else 'gpx')
    files=sorted(source.glob('*.gpx'))
    counts=Counter(); valid=0
    for path in files:
        pts=resample(read_gpx(path))
        if len(pts)<2: continue
        valid+=1; trip_edges=set()
        for a,b in zip(pts,pts[1:]):
            if distance(a,b)>MAX_EDGE_M: continue
            a,b=snap(a),snap(b)
            if a!=b: trip_edges.add(tuple(sorted((a,b))))
        counts.update(trip_edges)
    segments=[{'a':a,'b':b,'count':count} for (a,b),count in counts.items()]
    segments.sort(key=lambda x:(x['count'],x['a']))
    data={'tripCount':valid,'segmentCount':len(segments),'maxCount':max(counts.values(),default=0),'segments':segments}
    out=Path('data/segments.js'); out.parent.mkdir(exist_ok=True)
    out.write_text('window.VIADUCT_DATA='+json.dumps(data,separators=(',',':'))+';\n',encoding='utf-8')
    print(f'{valid} trips -> {len(segments)} segments -> {out}')

if __name__=='__main__': main()
