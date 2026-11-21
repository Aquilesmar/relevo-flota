import unittest
try:
    import numpy as np
    from ml.train import threshold_from_validation
except ImportError:
    np = None


@unittest.skipIf(np is None, "Instalar requirements-ml.txt para las pruebas de entrenamiento")
class ThresholdTests(unittest.TestCase):
    def test_tied_scores_match_brute_force(self):
        y = np.array([1, 0, 1, 0, 0], dtype=bool)
        scores = np.array([.7, .7, .4, .4, .2])
        def cost(t):
            pred = scores >= t
            return 10*(pred & ~y).sum() + 500*(~pred & y).sum()
        actual = threshold_from_validation(scores, y)
        self.assertEqual(cost(actual), min(cost(t) for t in [1, *scores]))
    def test_no_positives(self):
        scores = np.array([.1, .2])
        self.assertGreater(threshold_from_validation(scores, np.zeros(2, dtype=bool)), .2)

