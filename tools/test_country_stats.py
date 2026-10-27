import unittest
import shapely
from shapely.geometry import box
from build_country_stats import split_lengths
class CountryStatsTests(unittest.TestCase):
 def test_cross_border_edges_keep_repeated_traversals(self):
  lines=shapely.linestrings([[[-5,0],[5,0]],[[-5,0],[5,0]]]);parts,unknown,total=split_lengths(lines,[('CZ',box(0,-1,10,1)),('DE',box(-10,-1,0,1))]);self.assertAlmostEqual(parts['CZ'],10);self.assertAlmostEqual(parts['DE'],10);self.assertAlmostEqual(total,20);self.assertAlmostEqual(unknown,0)
 def test_shared_border_counted_only_once(self):
  lines=shapely.linestrings([[[0,-5],[0,5]]]);parts,unknown,total=split_lengths(lines,[('CZ',box(0,-10,10,10)),('DE',box(-10,-10,0,10))]);self.assertAlmostEqual(sum(parts.values()),10);self.assertAlmostEqual(parts['CZ'],10);self.assertAlmostEqual(parts['DE'],0)
 def test_missing_country_is_reported(self):
  lines=shapely.linestrings([[[-5,0],[5,0]]]);parts,unknown,total=split_lengths(lines,[('CZ',box(0,-1,10,1))]);self.assertAlmostEqual(parts['CZ'],5);self.assertAlmostEqual(unknown,5)
if __name__=='__main__':unittest.main()
