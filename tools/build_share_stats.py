#!/usr/bin/env python3
"""Aggregate a Viaduct JSON export; never publish raw notes, prices or access keys."""
import argparse,collections,hashlib,json,pathlib

def build(source,qa_path,stats_path,output):
 raw=pathlib.Path(source).read_bytes();payload=json.loads(raw);items=payload['items'] if isinstance(payload,dict) else payload
 stats=json.loads(pathlib.Path(stats_path).read_text());year=stats['year'];trips=[t for t in items if str(t.get('departure','')).startswith(str(year)) and t.get('mode')==1 and t.get('status',0)==0]
 if len({t['id'] for t in trips})!=len(trips):raise ValueError('Duplicate trip IDs')
 q=json.loads(pathlib.Path(qa_path).read_text())['trips']
 if collections.Counter(t['departure'][:16] for t in trips)!=collections.Counter(t['date'][:16] for t in q):raise ValueError('JSON rides and mapped GPX departures differ; rebuild GPX dataset first')
 if any(t.get('distance') is None or t.get('duration') is None for t in trips):raise ValueError('Missing distances or durations')
 pairs=collections.Counter(tuple(sorted((t['from_station'],t['to_station']))) for t in trips);pair,count=sorted(pairs.items(),key=lambda x:(-x[1],x[0]))[0];longest=max(trips,key=lambda t:t['distance']);months=collections.Counter(t['departure'][:7] for t in trips);month,month_n=sorted(months.items(),key=lambda x:(-x[1],x[0]))[0]
 result={'schemaVersion':1,'year':year,'tripCount':len(trips),'recordedKm':round(sum(t['distance'] for t in trips),2),'durationMinutes':sum(t['duration'] for t in trips),'travelDays':len(set(t['departure'][:10] for t in trips)),'countryCodes':stats['countries'],'dateFrom':min(t['departure'][:10] for t in trips),'dateTo':max(t['departure'][:10] for t in trips),'favoriteConnection':{'from':pair[0],'to':pair[1],'count':count},'longestTrip':{'from':longest['from_station'],'to':longest['to_station'],'km':longest['distance'],'durationMinutes':longest['duration']},'averageKm':round(sum(t['distance'] for t in trips)/len(trips),2),'busiestMonth':{'month':month,'count':month_n},'source':{'kind':'Viaduct JSON export','sha256':hashlib.sha256(raw).hexdigest(),'totalExportItems':len(items),'matchedGpxDepartures':len(q),'distanceNote':'Recorded distance in Viaduct, including parts missing from GPX.','durationNote':'Recorded duration, not a measurement of actual time including delays.','countriesNote':'Countries intersected by mapped GPX; includes German transit not present in trip endpoint country lists.'}}
 pathlib.Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('source');a.add_argument('--qa',default='data/qa.json');a.add_argument('--stats',default='data/stats.json');a.add_argument('--out',default='data/share-stats.json');o=a.parse_args();build(o.source,o.qa,o.stats,o.out)
