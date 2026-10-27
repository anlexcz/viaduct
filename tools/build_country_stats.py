#!/usr/bin/env python3
"""Split every valid GPX edge by country polygons, preserving repeat traversal.
Distances describe available GPX only: no extrapolation of missing geometry.
"""
import argparse,gzip,hashlib,json,pathlib
import numpy as np
import shapely
from shapely.geometry import shape,mapping
from shapely.ops import transform
from pyproj import Transformer
from build_heatmap import read_trips

CODES={'Czechia':'CZ','Poland':'PL','Slovakia':'SK','Germany':'DE'}
def prepare_boundaries(source,output):
 raw=pathlib.Path(source).read_bytes();js=json.loads(raw);p=Transformer.from_crs(4326,3035,always_xy=True);features=[]
 for f in js['features']:
  code=CODES.get(f['properties']['name'])
  if code:
   g=transform(p.transform,shape(f['geometry'])).simplify(2,preserve_topology=True)
   features.append({'code':code,'geometry':mapping(g)})
 data={'crs':'EPSG:3035','source':'Natural Earth / datasets/geo-countries','sourceSha256':hashlib.sha256(raw).hexdigest(),'simplificationMeters':2,'features':features}
 with open(output,'wb') as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as z:z.write(json.dumps(data,separators=(',',':')).encode())

def split_lengths(lines,countries):
 """Each edge retains multiplicity; boundary overlaps assigned only once."""
 lengths=shapely.length(lines);remaining=np.ones(len(lines),dtype=bool);result={code:0.0 for code,_ in countries}
 for code,polygon in countries:
  covered=remaining & shapely.covers(polygon,lines)
  result[code]+=float(lengths[covered].sum());remaining[covered]=False
 # Only boundary-crossing / unmapped edges need expensive polygon clipping.
 unknown=0.0
 for line in lines[remaining]:
  residue=line
  for code,polygon in countries:
   part=shapely.intersection(residue,polygon);result[code]+=float(shapely.length(part));residue=shapely.difference(residue,polygon)
  unknown+=float(shapely.length(residue))
 return result,unknown,float(lengths.sum())

def build(source,borders,output):
 trips,qa,_=read_trips(source);b=json.loads(gzip.decompress(pathlib.Path(borders).read_bytes()));features={f['code']:shape(f['geometry']) for f in b['features']};countries=[(c,features[c]) for c in ['CZ','PL','SK','DE'] if c in features]
 for _,g in countries:shapely.prepare(g)
 totals={c:0.0 for c,_ in countries};source_m=unknown_m=0.0;per_trip=[]
 for t in trips:
  edges=np.array([[a,b] for _,block in t['blocks'] for a,b in zip(block,block[1:])]);lines=shapely.linestrings(edges);parts,unknown,L=split_lengths(lines,countries)
  for c,d in parts.items():totals[c]+=d
  unknown_m+=unknown;source_m+=L;per_trip.append({'file':t['file'],'sha256':t['sha256'],'kmByCountry':{c:round(d/1000,4) for c,d in parts.items()},'unknownKm':round(unknown/1000,4)})
 if unknown_m>100:raise ValueError(f'{unknown_m/1000:.2f} km outside known country polygons; extend the boundaries first')
 assert abs(sum(totals.values())+unknown_m-source_m)<.05,'Country length conservation failed'
 result={'schemaVersion':1,'gpxCount':len(trips),'pointCount':qa['pointCount'],'rejectedLinks':qa['rejectedLinks'],'sourceKm':round(source_m/1000,4),'kmByCountry':{c:round(d/1000,4) for c,d in totals.items()},'foreignKm':round(sum(d for c,d in totals.items() if c!='CZ')/1000,4),'unknownKm':round(unknown_m/1000,4),'method':'EPSG:3035 edge clipping against country polygons; every occurrence counted; GPX gaps and >1500m jumps excluded','borderSource':b['source'],'borderSourceSha256':b['sourceSha256'],'boundarySimplificationMeters':b['simplificationMeters'],'notice':'Approximate distance in available GPX, not the full Viaduct recorded distance; missing GPX parts are not imputed.','trips':per_trip}
 pathlib.Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='trips'},ensure_ascii=False,indent=2));return result
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('gpx');a.add_argument('--borders',default='data/country-boundaries.json.gz');a.add_argument('--source-borders');a.add_argument('--out',default='data/country-stats.json');o=a.parse_args()
 if o.source_borders:prepare_boundaries(o.source_borders,o.borders)
 build(o.gpx,o.borders,o.out)
