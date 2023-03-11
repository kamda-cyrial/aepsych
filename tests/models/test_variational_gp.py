#!/usr/bin/env python3
# Copyright (c) Facebook, Inc. and its affiliates.
# All rights reserved.

# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import unittest

import numpy as np
import numpy.testing as npt
import torch
from botorch.fit import fit_gpytorch_mll
from gpytorch.likelihoods import BernoulliLikelihood
from aepsych.likelihoods.ordinal import OrdinalLikelihood
from gpytorch.mlls import VariationalELBO
from sklearn.datasets import make_classification

from aepsych.models import BinaryClassificationGP
from aepsych.models.variational_gp import OrdinalGP


class BinaryClassificationGPTestCase(unittest.TestCase):
    """
    Super basic smoke test to make sure we know if we broke the underlying model
    for single-probit  ("1AFC") model
    """

    def setUp(self):
        np.random.seed(1)
        torch.manual_seed(1)
        X, y = make_classification(
            n_samples=10,
            n_features=1,
            n_redundant=0,
            n_informative=1,
            random_state=1,
            n_clusters_per_class=1,
        )
        self.X, self.y = torch.Tensor(X), torch.Tensor(y).reshape(-1, 1)

    def test_1d_classification(self):
        """
        Just see if we memorize the training set
        """
        X, y = self.X, self.y
        model = BinaryClassificationGP(
            train_X=X, train_Y=y, likelihood=BernoulliLikelihood(), inducing_points=10
        )
        mll = VariationalELBO(model.likelihood, model.model, len(y))
        fit_gpytorch_mll(mll)

        # pspace
        pm, pv = model.predict(X, probability_space=True)
        pred = (pm > 0.5).numpy()
        npt.assert_allclose(pred.reshape(-1, 1), y)
        npt.assert_array_less(pv, 1)

        # fspace
        pm, pv = model.predict(X, probability_space=False)
        pred = (pm > 0).numpy()
        npt.assert_allclose(pred.reshape(-1, 1), y)
        npt.assert_array_less(1, pv)


class AxOrdinalGPTestCase(unittest.TestCase):
    @classmethod
    def setUp(cls):
        np.random.seed(1)
        torch.manual_seed(1)
        cls.n_levels = 5
        X, y = make_classification(
            n_samples=20,
            n_features=5,
            n_classes=cls.n_levels,
            n_informative=3,
            n_clusters_per_class=1,
        )
        cls.X, cls.y = torch.Tensor(X), torch.Tensor(y).reshape(-1, 1)

    def test_ordinal_classification(self):

        model = OrdinalGP(
            train_X=self.X,
            train_Y=self.y,
            likelihood=OrdinalLikelihood(n_levels=self.n_levels),
            inducing_points=2000,
        )
        probs = model.predict(self.X, probability_space=True)
        pred = np.argmax(probs.detach().numpy(), axis=1).reshape(-1, 1)
        print(
            "predicted: ",
            pred.reshape(-1),
            "expected: ",
            self.y.detach().numpy().reshape(-1),
        )
        mll = VariationalELBO(model.likelihood, model.model, len(self.y))
        fit_gpytorch_mll(mll)

        # pspace
        probs = model.predict(self.X, probability_space=True)
        pred = np.argmax(probs.detach().numpy(), axis=1).reshape(-1, 1)
        print(
            "predicted: ",
            pred.reshape(-1),
            "expected: ",
            self.y.detach().numpy().reshape(-1),
        )
        clipped_pred = np.clip(pred, 0, self.n_levels)
        npt.assert_allclose(clipped_pred, pred, atol=1, rtol=1)
        npt.assert_allclose(pred, self.y, atol=1, rtol=1)

        # fspace
        pm, pv = model.predict(self.X, probability_space=False)
        pred = np.floor(self.n_levels * pm).reshape(-1, 1)
        pred_var = (self.n_levels * pv).reshape(-1, 1)
        print(
            "predicted: ",
            pred.detach().numpy().reshape(-1),
            "expected: ",
            self.y.detach().numpy().reshape(-1),
            sep=" ",
        )
        clipped_pred = np.clip(pred, 0, self.n_levels)
        npt.assert_allclose(clipped_pred, pred, atol=3, rtol=self.n_levels)
        npt.assert_allclose(pred, self.y, atol=3, rtol=self.n_levels)
        npt.assert_allclose(
            pred_var, np.ones_like(pred_var), atol=self.n_levels, rtol=self.n_levels
        )


if __name__ == "__main__":
    unittest.main()
