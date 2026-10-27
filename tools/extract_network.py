#!/usr/bin/env python3
"""Two streaming passes over regional Geofabrik PBFs; retain railways near GPX."""
import argparse,gzip,json,pathlib,xml.etree.ElementTree as ET
import osmium
import numpy as np
from scipy.spatial import cKDTree
from pyproj import Transformer
P=Transformer.from_crs(4326,3035,always_xy=True)
def extract(source,pbfs,output):
 xy=[]
 for f in pathlib.Path(source).rglob('*.gpx'):
  for p in ET.parse(f).getroot().findall('.//{*}trkpt'):xy.append(P.transform(float(p.attrib['lon']),float(p.attrib['lat'])))
 tree=cKDTree(np.array(xy));ways={};snapshots=[]
 for pbf in sorted(pathlib.Path(pbfs).glob('*.osm.pbf')):
  print('Reading ways',pbf.name,flush=True);local={};ids=set()
  for w in osmium.FileProcessor(str(pbf),osmium.osm.WAY).with_filter(osmium.filter.TagFilter(('railway','rail'),('railway','narrow_gauge'))):
   tags=dict(w.tags)
   if tags.get('area')=='yes' or tags.get('disused')=='yes' or tags.get('abandoned')=='yes':continue
   ns=[n.ref for n in w.nodes];local[w.id]={'id':w.id,'nodes':ns,'tags':tags};ids.update(ns)
  nc={}
  for n in osmium.FileProcessor(str(pbf),osmium.osm.NODE).with_filter(osmium.filter.IdFilter(list(ids))):nc[n.id]=(n.location.lon,n.location.lat)
  for wid,w in local.items():
   if not all(n in nc for n in w['nodes']):continue
   geo=[nc[n] for n in w['nodes']];x,y=P.transform([p[0] for p in geo],[p[1] for p in geo])
   if tree.query(np.column_stack((x,y)))[0].min()>1000:continue
   w['geometry']=geo;ways[wid]=w
  reader=osmium.io.Reader(str(pbf));header=reader.header();reader.close();snapshots.append({'file':pbf.name,'replicationTimestamp':header.get('osmosis_replication_timestamp'),'bytes':pbf.stat().st_size})
 data={'source':'OpenStreetMap / Geofabrik','license':'ODbL 1.0','snapshots':snapshots,'corridorMeters':1000,'ways':[ways[i] for i in sorted(ways)]};pathlib.Path(output).parent.mkdir(parents=True,exist_ok=True)
 with open(output,'wb') as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as g:g.write(json.dumps(data,separators=(',',':'),ensure_ascii=False).encode())
 print(len(ways),'railway ways retained')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('gpx');a.add_argument('pbf_dir');a.add_argument('output');o=a.parse_args();extract(o.gpx,o.pbf_dir,o.output)
