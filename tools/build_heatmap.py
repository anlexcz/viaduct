#!/usr/bin/env python3
"""Offline topology-constrained beam matching of Viaduct GPX to OSM railways."""
import argparse,collections,functools,gzip,hashlib,heapq,json,math,pathlib,xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial import cKDTree
from pyproj import Transformer
P=Transformer.from_crs(4326,3035,always_xy=True);U=Transformer.from_crs(3035,4326,always_xy=True)
MAX_JUMP=1500;RADIUS=65;STEP=100;BEAM=4

def dist(a,b):return math.hypot(a[0]-b[0],a[1]-b[1])
def ll(p):return [round(v,6) for v in U.transform(*p)]
def project(p,a,b):
 dx,dy=b[0]-a[0],b[1]-a[1];l2=dx*dx+dy*dy;t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/l2));q=(a[0]+t*dx,a[1]+t*dy)
 return dist(p,q),t,q

def read_trips(source):
 trips=[];invalid=[];point_count=seg_count=jumps=0;rejected=[]
 for f in sorted(pathlib.Path(source).rglob('*')):
  if f.suffix.lower()!='.gpx':continue
  try:
   r=ET.parse(f).getroot();blocks=[];npoints=nsegs=nj=0
   for si,s in enumerate(r.findall('.//{*}trkseg')):
    nsegs+=1;block=[]
    for p in s.findall('{*}trkpt'):
     lat,lon=float(p.attrib['lat']),float(p.attrib['lon']);npoints+=1
     if not(-90<=lat<=90 and -180<=lon<=180):raise ValueError('invalid coordinates')
     xy=P.transform(lon,lat)
     if block and dist(block[-1],xy)>MAX_JUMP:
      rejected.append({'type':'Feature','properties':{'trip':f.name,'trkseg':si,'reason':'jump_over_1500m'},'geometry':{'type':'MultiPoint','coordinates':[ll(block[-1]),ll(xy)]}})
      if len(block)>1:blocks.append((si,block))
      block=[];nj+=1
     block.append(xy)
    if len(block)>1:blocks.append((si,block))
   if not blocks:raise ValueError('no valid track segments')
   trips.append({'file':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'name':r.findtext('.//{*}metadata/{*}name',f.stem),'date':r.findtext('.//{*}metadata/{*}time',''),'blocks':blocks,'points':npoints,'trkseg':nsegs,'rejected':nj})
   point_count+=npoints;seg_count+=nsegs;jumps+=nj
  except (ET.ParseError,ValueError,KeyError) as e:invalid.append({'file':f.name,'error':str(e)})
 if not trips:raise ValueError('No valid GPX input; refusing empty output')
 return trips,{'gpxCount':len(trips)+len(invalid),'validGpxCount':len(trips),'invalidGpx':invalid,'pointCount':point_count,'trackSegmentCount':seg_count,'rejectedLinks':jumps},rejected

class Network:
 def __init__(self,data):
  self.edges=[];self.adj=collections.defaultdict(list);samples=[];sample_edges=[]
  for w in data['ways']:
   tags=w['tags']
   if tags.get('service') in ('yard','spur','crossover'):continue
   geo=[P.transform(*p) for p in w['geometry']]
   for i,(a,b) in enumerate(zip(geo,geo[1:])):
    length=dist(a,b)
    if length<.05:continue
    n=max(1,math.ceil(length/80))
    for k in range(n):
     aa=tuple(a[j]+(b[j]-a[j])*k/n for j in (0,1));bb=tuple(a[j]+(b[j]-a[j])*(k+1)/n for j in (0,1))
     u=('n',w['nodes'][i]) if k==0 else ('s',w['id'],i,k);v=('n',w['nodes'][i+1]) if k==n-1 else ('s',w['id'],i,k+1)
     eid=len(self.edges);L=length/n;e={'a':aa,'b':bb,'u':u,'v':v,'length':L,'way':w['id'],'id':f"w{w['id']}:{i}:{k}",'tags':tags}
     self.edges.append(e);self.adj[u].append((v,L,eid));self.adj[v].append((u,L,eid))
     for t in np.linspace(0,1,max(2,math.ceil(L/25)+1)):
      samples.append([aa[j]+(bb[j]-aa[j])*t for j in (0,1)]);sample_edges.append(eid)
  if not self.edges:raise ValueError('Empty OSM graph')
  self.tree=cKDTree(samples);self.sample_edges=sample_edges
  print('Graph:',len(self.edges),'physical edges',flush=True);self.canonical=self.normalize()
 def normalize(self):
  # Representatives cannot transitively pull in progressively distant tracks.
  buckets=collections.defaultdict(list);reps=[];mapping={}
  order=sorted(range(len(self.edges)),key=lambda i:(self.edges[i]['tags'].get('service')=='siding',self.edges[i]['way'],self.edges[i]['id']))
  for i in order:
   e=self.edges[i];a,b=e['a'],e['b'];mid=((a[0]+b[0])/2,(a[1]+b[1])/2);cell=(int(mid[0]//100),int(mid[1]//100));best=None;vx,vy=b[0]-a[0],b[1]-a[1]
   for dx in (-1,0,1):
    for dy in (-1,0,1):
     for j in buckets[(cell[0]+dx,cell[1]+dy)]:
      c=self.edges[j];ta,tb=e['tags'],c['tags']
      if e['way']==c['way']:continue
      if any(ta.get(k,'')!=tb.get(k,'') for k in ('layer','bridge','tunnel','gauge')):continue
      ra=set(ta.get('ref','').split(';'))-{''};rb=set(tb.get('ref','').split(';'))-{''}
      if ra and rb and not ra.intersection(rb):continue
      limit=25 if ra.intersection(rb) else 10;d,t,q=project(mid,c['a'],c['b'])
      if d>limit or t<=.02 or t>=.98:continue
      dot=abs(vx*(c['b'][0]-c['a'][0])+vy*(c['b'][1]-c['a'][1]))/(e['length']*c['length'])
      if dot<math.cos(math.radians(12)):continue
      if max(project(p,c['a'],c['b'])[0] for p in (a,b))>limit+min(20,e['length']*.5):continue
      score=d+abs(.5-t)*2
      if best is None or score<best[0]:best=(score,j)
   if best:mapping[i]=best[1]
   else:mapping[i]=i;reps.append(i);buckets[cell].append(i)
  print('Canonical:',len(reps),'representatives;',len(self.edges)-len(reps),'parallel edges grouped',flush=True)
  return mapping
 def candidates(self,p,heading):
  ids=set(self.sample_edges[int(i)] for i in self.tree.query_ball_point(p,RADIUS+25));out=[]
  for i in ids:
   e=self.edges[i];d,t,q=project(p,e['a'],e['b'])
   if d>RADIUS:continue
   dot=abs(heading[0]*(e['b'][0]-e['a'][0])+heading[1]*(e['b'][1]-e['a'][1]))/e['length']
   if dot<.65:continue
   score=(d/18)**2+4*(1-dot)+(1 if e['tags'].get('service')=='siding' else 0);out.append((score,i,t,q,d))
  out.sort(key=lambda c:(c[0],c[1]));return out[:BEAM]
 @functools.lru_cache(maxsize=200000)
 def route_nodes(self,u,v,limit):
  if u==v:return 0,()
  heap=[(0,0,u)];seen={u:0};prev={};serial=0
  while heap:
   d,_,n=heapq.heappop(heap)
   if d!=seen[n]:continue
   if n==v:
    edges=[]
    while n!=u:n,eid=prev[n];edges.append(eid)
    return d,tuple(reversed(edges))
   for node,L,eid in self.adj[n]:
    nd=d+L
    if nd<=limit and nd<seen.get(node,float('inf')):
     seen[node]=nd;prev[node]=(n,eid);serial+=1;heapq.heappush(heap,(nd,serial,node))
  return None
 def transition(self,p,c,gps):
  ep,ec=self.edges[p[1]],self.edges[c[1]];limit=math.ceil((gps*1.7+80)/100)*100
  if p[1]==c[1]:return abs(p[2]-c[2])*ep['length'],(p[1],)
  best=None
  for u,du in ((ep['u'],p[2]*ep['length']),(ep['v'],(1-p[2])*ep['length'])):
   for v,dv in ((ec['u'],c[2]*ec['length']),(ec['v'],(1-c[2])*ec['length'])):
    route=self.route_nodes(u,v,limit)
    if route is None:continue
    length=du+route[0]+dv
    if abs(length-gps)>max(90,gps*.6):continue
    if best is None or length<best[0]:best=(length,((p[1],) if du>.1 else ())+route[1]+((c[1],) if dv>.1 else ()))
  return best
 def match(self,raw):
  samples=[raw[0]]
  for a,b in zip(raw,raw[1:]):
   L=dist(a,b)
   if L<.1:continue
   n=max(1,math.ceil(L/STEP))
   for k in range(1,n+1):
    q=tuple(a[j]+(b[j]-a[j])*k/n for j in (0,1))
    if dist(samples[-1],q)>=20 or k==n and b==raw[-1]:samples.append(q)
  states=[];runs=[];unmatched=[];matched_lengths=[];residuals=[];resets=0
  def flush():
   if not states:return
   last=min(states[-1],key=lambda s:s['cost']);seq=[]
   while last is not None:seq.append(last);last=last['parent']
   for s in reversed(seq):
    residuals.append(s['c'][4])
    if s['route'] is not None:runs.append(s['route'][1]);matched_lengths.append(s['route'][0])
   states.clear()
  for i,p in enumerate(samples):
   a=samples[max(0,i-1)];b=samples[min(len(samples)-1,i+1)];L=dist(a,b);heading=((b[0]-a[0])/L,(b[1]-a[1])/L) if L else (1,0);candidates=self.candidates(p,heading)
   if not candidates:
    flush()
    if i:unmatched.append((samples[i-1],p,'no_candidate'))
    continue
   if not states:
    states.append([{'c':c,'cost':c[0],'parent':None,'route':None} for c in candidates])
    if i:unmatched.append((samples[i-1],p,'restart'))
    continue
   gps=dist(samples[i-1],p);nxt=[]
   for c in candidates:
    choices=[]
    for prev in states[-1]:
     route=self.transition(prev['c'],c,gps)
     if route is not None:choices.append((prev['cost']+c[0]+abs(route[0]-gps)/20,prev,route))
    if choices:
     cost,parent,route=min(choices,key=lambda x:x[0]);nxt.append({'c':c,'cost':cost,'parent':parent,'route':route})
   if not nxt:
    flush();resets+=1;unmatched.append((samples[i-1],p,'topology_break'));states.append([{'c':c,'cost':c[0],'parent':None,'route':None} for c in candidates])
   else:
    floor=min(s['cost'] for s in nxt)
    for s in nxt:s['cost']-=floor
    states.append(nxt)
  flush();return runs,unmatched,matched_lengths,residuals,resets

def write_json(path,obj):path.write_text(json.dumps(obj,separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('source');ap.add_argument('--network',default='data/network.json.gz');ap.add_argument('--out',default='data');o=ap.parse_args();out=pathlib.Path(o.out);out.mkdir(parents=True,exist_ok=True)
 trips,stats,rejected=read_trips(o.source);data=json.loads(gzip.decompress(pathlib.Path(o.network).read_bytes()));net=Network(data);counts=collections.Counter();qa=[];features=[];residuals=[];source_len=matched_len=unmatched_len=0;resets=matched_parts=unmatched_parts=0
 for ti,trip in enumerate(trips):
  seen=set();tl=ml=ul=0;tu=tm=tr=0;res=[]
  for si,raw in trip['blocks']:
   tl+=sum(dist(a,b) for a,b in zip(raw,raw[1:]));runs,unknown,lens,rs,r=net.match(raw)
   for run in runs:seen.update(net.canonical[e] for e in run)
   for a,b,reason in unknown:features.append({'type':'Feature','properties':{'trip':ti,'trkseg':si,'reason':reason},'geometry':{'type':'LineString','coordinates':[ll(a),ll(b)]}})
   ml+=sum(lens);ul+=sum(dist(a,b) for a,b,_ in unknown);tu+=len(unknown);tm+=len(runs);tr+=r;res.extend(rs)
  counts.update(seen);source_len+=tl;matched_len+=ml;unmatched_len+=ul;residuals.extend(res);resets+=tr;matched_parts+=tm;unmatched_parts+=tu
  qa.append({k:v for k,v in trip.items() if k!='blocks'}|{'id':ti,'sourceKm':round(tl/1000,3),'matchedRouteKm':round(ml/1000,3),'unmatchedKm':round(ul/1000,3),'matchedTransitions':tm,'unmatchedTransitions':tu,'topologyBreaks':tr,'canonicalSegments':len(seen),'p95ResidualMeters':round(float(np.percentile(res,95)),1) if res else None})
  print(f"{ti+1}/{len(trips)} {trip['name']}: {ml/1000:.1f} km matched, {ul/1000:.2f} km unmatched",flush=True)
 rows=[];ways={}
 for i,n in sorted(counts.items(),key=lambda x:(x[1],x[0])):
  e=net.edges[i];rows.append([*ll(e['a']),*ll(e['b']),n,e['way']]);ways[str(e['way'])]=[e['tags'].get('ref',''),e['tags'].get('name','')]
 bounds=np.array([ll(p) for t in trips for _,raw in t['blocks'] for p in raw]);dates=sorted(t['date'] for t in trips if t['date'])
 stats.update({'schemaVersion':2,'year':2026,'method':'OSM topology-constrained beam matching; conservative parallel-track representatives','countries':['CZ','PL','SK','DE'],'dateFrom':dates[0][:10],'dateTo':dates[-1][:10],'tripCount':len(trips),'segmentCount':len(counts),'physicalNetworkEdges':len(net.edges),'canonicalNetworkEdges':len(set(net.canonical.values())),'maxCount':max(counts.values()),'sourceKm':round(source_len/1000,1),'matchedRouteKm':round(matched_len/1000,1),'unmatchedKm':round(unmatched_len/1000,2),'matchedTransitions':matched_parts,'unmatchedTransitions':unmatched_parts,'topologyBreaks':resets,'matchedSourcePercent':round(100*(source_len-unmatched_len)/source_len,2),'matchedSourceKm':round((source_len-unmatched_len)/1000,2),'matchedTransitionPercent':round(100*matched_parts/(matched_parts+unmatched_parts),2),'p95ResidualMeters':round(float(np.percentile(residuals,95)),1),'uniqueRepresentativeKm':round(sum(net.edges[i]['length'] for i in counts)/1000,1),'frequencyHistogram':dict(sorted(collections.Counter(counts.values()).items())),'bounds':[[float(bounds[:,1].min()),float(bounds[:,0].min())],[float(bounds[:,1].max()),float(bounds[:,0].max())]],'osmSnapshots':data['snapshots'],'networkSha256':hashlib.sha256(pathlib.Path(o.network).read_bytes()).hexdigest(),'parameters':{'candidateRadiusMeters':RADIUS,'maxSourceLinkMeters':MAX_JUMP,'sampleMaxMeters':STEP,'sampleMinMeters':20,'beam':BEAM,'parallelMetersSharedRef':25,'parallelMetersNoRef':10,'parallelMaxAngleDegrees':12}})
 with open(out/'heatmap.json.gz','wb') as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as g:g.write(json.dumps({'schemaVersion':2,'ways':ways,'segments':rows},separators=(',',':'),ensure_ascii=False).encode())
 write_json(out/'unmatched.geojson',{'type':'FeatureCollection','features':features});write_json(out/'rejected.geojson',{'type':'FeatureCollection','features':rejected});write_json(out/'stats.json',stats);write_json(out/'qa.json',{'trips':qa,'notes':['Each trkseg is matched separately.','GPX length excludes gaps and rejected links.','Representative length is an estimate, not official route-km.']})
 print(json.dumps(stats,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
