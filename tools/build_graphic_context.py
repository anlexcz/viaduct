#!/usr/bin/env python3
"""Small vector backdrop for tile-free, CORS-free PNG export."""
import gzip,json,pathlib,argparse,urllib.request
from shapely.geometry import LineString,shape,mapping,box
from pyproj import Transformer

def build(network,output,borders=None):
 data=json.loads(gzip.decompress(pathlib.Path(network).read_bytes()));p=Transformer.from_crs(4326,3035,always_xy=True);u=Transformer.from_crs(3035,4326,always_xy=True);lines=[]
 for w in data['ways']:
  if w['tags'].get('service') in ('yard','spur','crossover'):continue
  pts=w['geometry']
  if len(pts)<2:continue
  line=LineString([p.transform(*a) for a in pts]).simplify(22)
  lines.append([[round(a,5),round(b,5)] for a,b in (u.transform(*x) for x in line.coords)])
 countries=[]
 if borders:
  js=json.loads(pathlib.Path(borders).read_text());extent=box(9,46,25,56)
  for f in js['features']:
   g=shape(f['geometry'])
   if g.intersects(extent):countries.append(mapping(g.intersection(extent).simplify(.012,preserve_topology=True)))
 out={'schemaVersion':1,'railways':lines,'countries':countries,'attribution':'Railways © OpenStreetMap contributors / ODbL; borders Natural Earth / geo-countries'}
 with open(output,'wb') as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as z:z.write(json.dumps(out,separators=(',',':')).encode())
 print(len(lines),'railway ways;',len(countries),'country polygons;',pathlib.Path(output).stat().st_size,'bytes')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--network',default='data/network.json.gz');a.add_argument('--out',default='data/graphic-context.json.gz');a.add_argument('--borders');o=a.parse_args();build(o.network,o.out,o.borders)
