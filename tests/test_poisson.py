import numpy as np
import pytest

from numpy.testing import (assert_allclose,
                           assert_equal,
                           assert_raises)

from pyuoi.linear_model import Poisson, UoI_Poisson
from pyuoi.linear_model.poisson import _poisson_loss_and_grad

from sklearn.exceptions import NotFittedError

# poisson GLM model by hand

# design matrix
X = np.array([
    [0.35, 0.84, 0.95, 0.77, 0.88],
    [0.43, 0.76, 0.47, 0.09, 0.34],
    [0.41, 0.40, 0.08, 0.82, 0.49],
    [0.73, 0.93, 0.39, 0.77, 0.72],
    [0.69, 0.88, 0.32, 0.54, 0.26],
    [0.34, 0.10, 0.55, 0.20, 0.20],
    [0.20, 0.15, 0.23, 0.16, 0.74],
    [0.94, 0.08, 0.97, 0.03, 0.48],
    [0.61, 0.55, 0.72, 0.21, 0.27],
    [0.54, 0.21, 0.98, 0.26, 0.01]])

# true parameters
beta = np.array([3., 1., 0., -2., 0.])

# response variable
y = np.array([2, 6, 0, 4, 6, 3, 0, 16, 8, 7])


def test_soft_threshold():
    """Tests the soft threshold function against equivalent output from a
    MATLAB implementation."""

    true_threshold = np.array([
        [0, 0.34, 0.45, 0.27, 0.38],
        [0, 0.26, 0, 0, 0],
        [0, 0, 0, 0.32, 0],
        [0.23, 0.43, 0, 0.27, 0.22],
        [0.19, 0.38, 0, 0.04, 0],
        [0, 0, 0.05, 0, 0],
        [0, 0, 0.0, 0, 0.24],
        [0.44, 0, 0.47, 0, 0],
        [0.11, 0.05, 0.22, 0, 0],
        [0.04, 0, 0.48, 0, 0]])

    assert_allclose(true_threshold,
                    Poisson.soft_threshold(X, 0.5))


def test_adjusted_response():
    """Tests the adjusted response function against equivalent output from a
    MATLAB implementation."""

    w, z = Poisson.adjusted_response(X, y, beta)

    w_true = np.array([
        1.419067548593257, 6.488296399286710, 0.990049833749168,
        4.854955811237434, 6.488296399286709, 2.054433210643888,
        1.537257523548281, 17.115765537145876, 7.099327065156633,
        3.706173712210199])

    z_true = np.array([
        0.759376179437427, 1.794741970890788, -1.01,
        1.403900392819534, 1.794741970890788, 1.180256767879915,
        -0.57, 2.774810655432013, 2.086867367368360,
        2.198740394692808])

    assert_allclose(w_true, w)
    assert_allclose(z_true, z)


def test_cd_sweep():
    """Test one pass through the coordinate sweep function."""

    poisson = Poisson(fit_intercept=False)

    w, z = Poisson.adjusted_response(X, y, beta)
    active_idx = np.argwhere(beta != 0).ravel()
    beta_new, intercept_new = poisson._cd_sweep(beta, X, w, z, active_idx)

    beta_new_true = np.array([
        2.922553187460584, 0.909849302128083, 0, -1.850644198436912, 0])

    assert_allclose(beta_new_true, beta_new)
    assert intercept_new == 0


@pytest.mark.skip
def test_fit():
    """Test the entire fitting procedure for the Poisson GLM."""

    # compare after 50 iterations
    poisson = Poisson(max_iter=50, fit_intercept=False)
    poisson.fit(X, y, init=0.5 * np.ones(beta.size))
    beta_new_true = np.array([
        -3.865910169523823, 6.243915946623266, -0.728804736275411,
        -0.463706073765083, -3.622620769371424])

    assert_allclose(beta_new_true, poisson.coef_)


def test_predict():
    """Test the predict function in the Poisson class"""
    # design matrix
    X = np.array([[np.log(2.5), -1, -3],
                  [np.log(3.5), -2, -4],
                  [np.log(4.5), -3, -5],
                  [np.log(5.5), -4, -6]])

    poisson = Poisson()

    # test for NotFittedError
    assert_raises(NotFittedError, poisson.predict, X)

    # create "fit"
    poisson.coef_ = np.array([1, 0, 0])
    poisson.intercept_ = 0
    y_pred = poisson.predict(X)
    y_mode = np.array([2, 3, 4, 5])

    # test for predict
    assert_allclose(y_pred, y_mode)


def test_predict_mean():
    """Test the predict function in the Poisson class"""
    # design matrix
    X = np.array([[np.log(2.5), -1, -3],
                  [np.log(3.5), -2, -4],
                  [np.log(4.5), -3, -5],
                  [np.log(5.5), -4, -6]])

    poisson = Poisson()

    # test for NotFittedError
    assert_raises(NotFittedError, poisson.predict_mean, X)

    # create "fit"
    poisson.coef_ = np.array([1, 0, 0])
    poisson.intercept_ = 0
    y_pred = poisson.predict_mean(X)
    y_mean = np.array([2.5, 3.5, 4.5, 5.5])

    # test for predict
    assert_allclose(y_pred, y_mean)


def test_score_predictions():
    """Test the score predictions function in UoI Poisson."""
    X = np.array([[np.log(2), -1, -3],
                  [np.log(3), -2, -4],
                  [np.log(4), -3, -5],
                  [np.log(5), -4, -6]])
    y = 1. / np.log([2., 3., 4., 5.])
    support = np.array([True, False, False])

    # create fitter by hand
    fitter = Poisson()
    fitter.coef_ = np.array([1])
    fitter.intercept_ = 0

    uoi_fitter = UoI_Poisson()

    # test log-likelihood
    ll = uoi_fitter._score_predictions(
        metric='log',
        fitter=fitter,
        X=X, y=y, support=support)
    assert_allclose(ll, -2.5)

    # test information criteria
    aic = uoi_fitter._score_predictions(
        metric='AIC',
        fitter=fitter,
        X=X, y=y, support=support)
    assert_allclose(aic, 2 * ll - 2)

    aicc = uoi_fitter._score_predictions(
        metric='AICc',
        fitter=fitter,
        X=X, y=y, support=support)
    assert_allclose(aicc, aic - 2)

    bic = uoi_fitter._score_predictions(
        metric='BIC',
        fitter=fitter,
        X=X, y=y, support=support)
    assert_allclose(bic, 2 * ll - np.log(y.size))

    # test invalid metric
    assert_raises(ValueError,
                  uoi_fitter._score_predictions,
                  'fake',
                  fitter,
                  X, y, support)


def test_poisson_loss_and_grad():
    """Tests the poisson loss and gradient function."""
    n_features = 5
    n_samples = 100

    # test with empty coefficients
    X = np.random.normal(loc=0, scale=1., size=(n_samples, n_features))
    y = np.random.normal(loc=0, scale=1, size=(n_samples))

    loss, grad = _poisson_loss_and_grad(np.zeros(n_features), X, y, 0.)

    assert_equal(loss, 1.)
    assert_allclose(grad, -np.dot(X.T, y - 1) / n_samples)

    # test with non-empty coefficients
    X = np.ones((n_samples, n_features))
    y = np.zeros(n_samples)

    loss, grad = _poisson_loss_and_grad(np.ones(n_features), X, y, 0)
    assert_equal(loss, np.exp(n_features).mean())
    assert_allclose(grad, np.mean(X * np.exp(n_features), axis=0))


def test_poisson_lbfgs():
    """Tests the Poisson fitter using orthant-wise LBFGS."""
    n_features = 3
    n_samples = 10000

    # create data
    X = np.random.normal(loc=0, scale=1. / 8, size=(n_samples, n_features))
    beta = np.array([0.5, 1.0, 1.5])
    eta = np.dot(X, beta)
    y = np.random.poisson(np.exp(eta))

    poisson = Poisson(alpha=0., l1_ratio=1., fit_intercept=False)
    poisson.fit(X, y)

    assert_allclose(poisson.coef_, beta, rtol=0.5)
