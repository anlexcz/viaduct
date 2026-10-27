import pathlib,tempfile,unittest
from build_heatmap import Network,read_trips,P

def way(i,nodes,coords,ref='A',**tags):return {'id':i,'nodes':nodes,'geometry':coords,'tags':{'railway':'rail','ref':ref,**tags}}
class PipelineTests(unittest.TestCase):
 def test_trkseg_and_jump_separation(self):
  with tempfile.TemporaryDirectory() as d:
   pathlib.Path(d,'a.gpx').write_text('<gpx><trk><trkseg><trkpt lat="50" lon="14"/><trkpt lat="50" lon="14.001"/><trkpt lat="51" lon="15"/><trkpt lat="51" lon="15.001"/></trkseg><trkseg><trkpt lat="49" lon="16"/><trkpt lat="49" lon="16.001"/></trkseg></trk></gpx>')
   t,s,r=read_trips(d);self.assertEqual((s['trackSegmentCount'],s['rejectedLinks'],len(t[0]['blocks'])),(2,1,3));self.assertEqual(r[0]['geometry']['type'],'MultiPoint')
 def test_opposite_direction_same_edges(self):
  n=Network({'ways':[way(1,[1,2,3],[(14,50),(14.001,50),(14.002,50)])]});p=[P.transform(14,50),P.transform(14.001,50),P.transform(14.002,50)];a=n.match(p);b=n.match(p[::-1]);self.assertEqual({e for r in a[0] for e in r},{e for r in b[0] for e in r});self.assertFalse(a[1]);self.assertFalse(b[1])
 def test_no_routing_across_disconnected_edges(self):
  n=Network({'ways':[way(1,[1,2],[(14,50),(14.001,50)]),way(2,[3,4],[(14.0015,50),(14.0025,50)],ref='B')]});self.assertIsNone(n.transition((0,0,1,n.edges[0]['b'],0),(0,1,0,n.edges[1]['a'],0),40))
 def test_parallel_normalization_preserves_different_ref(self):
  n=Network({'ways':[way(1,[1,2],[(14,50),(14.001,50)]),way(2,[3,4],[(14,50.00004),(14.001,50.00004)]),way(3,[5,6],[(14,50.00008),(14.001,50.00008)],ref='B')]});self.assertEqual(n.canonical[0],n.canonical[1]);self.assertNotEqual(n.canonical[0],n.canonical[2])
 def test_tunnel_and_surface_remain_separate(self):
  n=Network({'ways':[way(1,[1,2],[(14,50),(14.001,50)]),way(2,[3,4],[(14,50.00004),(14.001,50.00004)],tunnel='yes')]});self.assertNotEqual(n.canonical[0],n.canonical[1])
if __name__=='__main__':unittest.main()
