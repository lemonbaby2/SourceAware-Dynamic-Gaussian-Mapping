import unittest
from protocol import split_ids, select_frames, family_log_pool
import numpy as np

class ProtocolTests(unittest.TestCase):
    def test_no_test_view_in_training(self):
        train, test = split_ids(12)
        self.assertEqual(test, [2,5,8,11])
        self.assertFalse(set(train) & set(test))
        self.assertEqual(sorted(train+test), list(range(12)))
    def test_select_evaluation_subset(self):
        self.assertEqual(select_frames(list(range(12)), [2,5]), [2,5])
    def test_duplicate_family_invariance(self):
        p=np.array([[.2,.8],[.6,.4]])
        a=family_log_pool(p, [0,1])
        b=family_log_pool(np.column_stack([p[:,0],p[:,0],p[:,1]]), [0,0,1])
        np.testing.assert_allclose(a,b,atol=1e-12)
    def test_invalid_probability_rejected(self):
        with self.assertRaises(ValueError): family_log_pool(np.array([[1.1,.5]]),[0,1])

if __name__=='__main__': unittest.main()
