import json,pathlib,tempfile,unittest
from build_share_stats import build
class ShareStatsTests(unittest.TestCase):
 def setup_files(self,d):
  p=pathlib.Path(d);rows=[{'id':1,'departure':'2026-01-02T10:00:00','from_station':'A','to_station':'B','distance':100,'duration':60,'mode':1,'status':0,'notes':'PRIVATE_MARKER','price':999},{'id':2,'departure':'2026-01-03T11:00:00','from_station':'B','to_station':'A','distance':120,'duration':85,'mode':1,'status':0},{'id':3,'departure':'2025-01-02T10:00:00','from_station':'A','to_station':'C','distance':900,'duration':600,'mode':1,'status':0}]
  (p/'trips.json').write_text(json.dumps({'items':rows}));(p/'qa.json').write_text(json.dumps({'trips':[{'date':r['departure']+'Z'} for r in rows[:2]]}));(p/'stats.json').write_text(json.dumps({'year':2026,'countries':['CZ','DE']}));return p
 def test_year_filter_bidirectional_connection_and_no_private_fields(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.setup_files(d);r=build(p/'trips.json',p/'qa.json',p/'stats.json',p/'out.json');self.assertEqual((r['tripCount'],r['recordedKm'],r['durationMinutes'],r['favoriteConnection']['count']),(2,220,145,2));self.assertEqual(r['travelDays'],2);self.assertNotIn('PRIVATE_MARKER',(p/'out.json').read_text());self.assertNotIn('price',r)
 def test_mismatched_map_and_trip_export_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.setup_files(d);(p/'qa.json').write_text('{"trips":[]}')
   with self.assertRaises(ValueError):build(p/'trips.json',p/'qa.json',p/'stats.json',p/'out.json')
if __name__=='__main__':unittest.main()
