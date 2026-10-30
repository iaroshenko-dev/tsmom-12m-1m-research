import unittest
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
class TestArchived(unittest.TestCase):
    def setUp(self):
        self.s=pd.read_csv(ROOT/'results/strategy_summary.csv')
    def pick(self,strategy,period,cost='net_1x'):
        x=self.s[(self.s.strategy==strategy)&(self.s.period==period)&(self.s.cost_case==cost)]
        self.assertEqual(len(x),1)
        return x.iloc[0]
    def test_primary_2010_net(self):
        x=self.pick('TSMOM_scaled','POST_2009')
        self.assertAlmostEqual(float(x.ann_arith_mean),.05869676721219526,places=10)
        self.assertAlmostEqual(float(x.sharpe),.47893069428686535,places=10)
    def test_controls(self):
        t=self.pick('TSMOM_scaled','POST_2009');a=self.pick('AlwaysLong_scaled','POST_2009');h=self.pick('HistoricalMean_scaled','POST_2009')
        self.assertGreater(a.ann_arith_mean,t.ann_arith_mean)
        self.assertGreater(h.ann_arith_mean,t.ann_arith_mean)
    def test_archive_is_not_truncated(self):
        b=pd.read_csv(ROOT/'results/paired_control_bootstrap.csv')
        self.assertEqual(len(b),24)
if __name__=='__main__': unittest.main()
