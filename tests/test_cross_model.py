import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import torch
from cross_model import SoilingCrossUNet
class CrossTest(unittest.TestCase):
 def test_shape_and_soiling_monotonicity(self):
  torch.manual_seed(42);m=SoilingCrossUNet();m.eval();h=torch.rand(2,96,8);f=torch.rand(2,96,6);f[:,:,0]=.6;f[:,:,1]=.6;f[:,:,5]=.08
  p,l,clean=m(h,f);self.assertEqual(p.shape,(2,96));self.assertEqual(l.shape,(2,96));self.assertTrue(torch.isfinite(p).all());self.assertTrue((p<=clean+1e-6).all())
  dust=f.clone();dust[:,:,5]=.2;p2,_,_=m(h,dust);self.assertTrue((p2<=p+1e-6).all())
if __name__=='__main__':unittest.main()
